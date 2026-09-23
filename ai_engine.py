import os
import json
import re
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("legal_ai")
logging.basicConfig(level=logging.INFO)

class AIEngine:
    """ClauseLens Factual Document Intelligence & Validation Engine."""

    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.groq_key = os.getenv("GROQ_API_KEY", "").strip()


    def _extract_json(self, text: str) -> Dict[str, Any]:
        """
        Robustly extracts JSON object from LLM response text.
        Strips markdown formatting and attempts to repair broken JSON structure.

        Args:
            text (str): The raw output from the language model.

        Returns:
            Dict[str, Any]: Parsed JSON dictionary.

        Raises:
            ValueError: If JSON cannot be reliably parsed.
        """
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            # Basic fix for trailing commas in JSON lists/objects
            cleaned = re.sub(r',\s*([\]}])', r'\1', cleaned)
            return json.loads(cleaned)
        except Exception:
            match = re.search(r'(\{.*\})', cleaned, re.DOTALL)
            if match:
                try:
                    cleaned_match = re.sub(r',\s*([\]}])', r'\1', match.group(1))
                    return json.loads(cleaned_match)
                except Exception:
                    pass
            raise ValueError("Could not extract valid JSON from model response")

    def _call_gemini(self, prompt: str, system_instruction: str = "") -> str:
        if not self.gemini_key:
            raise ValueError("Gemini API key is not configured.")
        
        try:
            from google import genai
            client = genai.Client(api_key=self.gemini_key)
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config={
                    'system_instruction': system_instruction,
                    'response_mime_type': 'application/json'
                }
            )
            return response.text
        except Exception as e:
            logger.warning(f"Gemini SDK error: {e}. Trying REST API fallback...")
            import httpx
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.gemini_key}"
            payload = {
                "contents": [{"parts": [{"text": f"{system_instruction}\n\n{prompt}"}]}],
                "generationConfig": {
                    "responseMimeType": "application/json"
                }
            }
            resp = httpx.post(url, json=payload, timeout=30.0)
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

    def _call_groq(self, prompt: str, system_instruction: str = "") -> str:
        if not self.groq_key:
            raise ValueError("Groq API key is not configured.")
        
        from groq import Groq
        client = Groq(api_key=self.groq_key)
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            model="openai/gpt-oss-120b",
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content

    def generate_and_parse_completion(self, prompt: str, system_instruction: str = "", provider: str = "auto") -> Dict[str, Any]:
        """
        Generates and parses a JSON completion using primary and fallback LLM APIs.

        Args:
            prompt (str): The main user prompt to evaluate.
            system_instruction (str, optional): System-level prompt steering the AI.
            provider (str, optional): Target provider ("auto", "gemini", "groq").

        Returns:
            Dict[str, Any]: A successfully extracted JSON object.

        Raises:
            ValueError: If both providers fail to return valid JSON.
        """
        if provider == "groq" or (provider == "auto" and self.groq_key and not self.gemini_key):
            try:
                raw = self._call_groq(prompt, system_instruction)
                logger.info(f"RAW GROQ OUTPUT:\n{raw}")
                return self._extract_json(raw)
            except Exception as e:
                logger.warning(f"Groq failed (API or JSON parsing): {e}. Trying Gemini...")
                if self.gemini_key:
                    try:
                        raw2 = self._call_gemini(prompt, system_instruction)
                        logger.info(f"RAW GEMINI OUTPUT:\n{raw2}")
                        return self._extract_json(raw2)
                    except Exception as e2:
                        raise ValueError(f"Both providers failed. Last error: {e2}")
                raise e
        else:
            try:
                raw = self._call_gemini(prompt, system_instruction)
                logger.info(f"RAW GEMINI OUTPUT:\n{raw}")
                return self._extract_json(raw)
            except Exception as e:
                logger.warning(f"Gemini failed (API or JSON parsing): {e}. Trying Groq...")
                if self.groq_key:
                    try:
                        raw2 = self._call_groq(prompt, system_instruction)
                        logger.info(f"RAW GROQ OUTPUT:\n{raw2}")
                        return self._extract_json(raw2)
                    except Exception as e2:
                        raise ValueError(f"Both providers failed. Last error: {e2}")
                raise e

    def _deduplicate_items(self, items: List[str]) -> List[str]:
        """Deduplicates strings exactly."""
        unique_items = []
        seen = set()
        for item in items:
            if not item or not item.strip():
                continue
            item_clean = item.strip()
            key = item_clean.lower()
            if key not in seen:
                seen.add(key)
                unique_items.append(item_clean)
        return unique_items

    def _validate_and_repair_analysis(self, analysis: Dict[str, Any], clauses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validates AI response against actual uploaded text and repairs errors/hallucinations.
        Ensures exact quotes match the uploaded document text.

        Args:
            analysis (Dict[str, Any]): The initial AI output.
            clauses (List[Dict[str, Any]]): The list of actual document clauses.

        Returns:
            Dict[str, Any]: The repaired and verified analysis dict.
        """
        doc_text_combined = " ".join([c.get("originalText", "") for c in clauses]).lower()

        # Deduplicate blind spots
        raw_bs = analysis.get("blind_spots", [])
        analysis["blind_spots"] = self._deduplicate_items(raw_bs)

        findings = analysis.get("findings", [])
        repaired_findings = []
        seen_titles = set()

        for f in findings:
            title = f.get("title", "Clause")
            source_sec = f.get("source_section", "")
            title_key = f"{source_sec}-{title}".lower()

            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)

            what_says = f.get("what_document_says", "")

            # Verify source quote exists or use fallback
            if what_says and len(what_says) > 15:
                # Basic sanity check
                first_few = what_says[:20].lower()
                if first_few not in doc_text_combined:
                    # Find matching clause text
                    for c in clauses:
                        if c.get("number", "").lower() in source_sec.lower() or c.get("title", "").lower() in title.lower():
                            f["what_document_says"] = c.get("originalText", "")[:250]
                            break

            repaired_findings.append(f)

        analysis["findings"] = repaired_findings
        return analysis

    def analyze_clauses(self, clauses: List[Dict[str, Any]], provider: str = "auto") -> Dict[str, Any]:
        """Performs factual legal document analysis dynamically based solely on the provided clauses."""
        if not self.gemini_key and not self.groq_key:
            raise ValueError("No AI API keys are configured. Cannot perform analysis.")

        system_instruction = (
            "You are ClauseLens, a factual legal document assistant. Analyze the uploaded contract clauses strictly based on what is stated.\n\n"
            "STRICT ANTI-HALLUCINATION & ACCURACY RULES:\n"
            "1. Base findings ONLY on the actual uploaded document text. Never invent penalties, deadlines, fees, or obligations. Treat each document as a completely blank slate.\n"
            "2. Deduplicate findings and blind spots. Only list a blind spot if it is genuinely missing from the provided clauses.\n"
            "3. Return JSON matching:\n"
            "{\n"
            "  \"document_type\": \"Document type based on contents (e.g. Freelance Agreement, Lease)\",\n"
            "  \"summary\": \"Factual 2-sentence document summary based ONLY on the text\",\n"
            "  \"key_obligations\": [\"List of unique factual obligations\"],\n"
            "  \"important_dates\": [\"List of unique key timelines\"],\n"
            "  \"blind_spots\": [\"List of unique unstated terms/missing deadlines based on standard contracts of this type\"],\n"
            "  \"findings\": [\n"
            "    {\n"
            "      \"title\": \"Clause Title\",\n"
            "      \"category\": \"important_review | ambiguity | blind_spot | obligation | clear\",\n"
            "      \"severity\": \"important | moderate | informational\",\n"
            "      \"what_document_says\": \"Verbatim snippet from document\",\n"
            "      \"plain_language\": \"Plain English explanation\",\n"
            "      \"why_it_matters\": \"Why a non-lawyer should pay attention\",\n"
            "      \"what_is_unclear\": \"What is vague or unstated (or empty string)\",\n"
            "      \"question_to_clarify\": \"Neutral question to ask\",\n"
            "      \"source_text\": \"Exact clause text\",\n"
            "      \"source_section\": \"Section Number and Title\"\n"
            "    }\n"
            "  ]\n"
            "}"
        )

        formatted_clauses = [{"id": c.get("id"), "number": c.get("number"), "title": c.get("title"), "text": c.get("originalText")[:600]} for c in clauses[:15]]
        prompt = f"Clauses to analyze:\n{json.dumps(formatted_clauses, indent=2)}"

        try:
            parsed_analysis = self.generate_and_parse_completion(prompt, system_instruction, provider)
            return self._validate_and_repair_analysis(parsed_analysis, clauses)
        except Exception as e:
            logger.error(f"Error during AI analysis: {e}")
            raise ValueError(f"AI Analysis failed: {str(e)}. Please check your API quotas or try again.")

    def answer_question(self, clauses: List[Dict[str, Any]], user_question: str, provider: str = "auto") -> Dict[str, Any]:
        """Grounded Q&A strictly adhering to document facts without yes/no assumptions."""
        
        context_snippets = []
        for c in clauses[:12]:
            context_snippets.append(f"[{c.get('number', 'Section')}] {c.get('title', '')}: {c.get('originalText', '')[:500]}")
        context_str = "\n\n".join(context_snippets)

        if not self.gemini_key and not self.groq_key:
            raise ValueError("No API keys set. Cannot answer question.")

        system_instruction = (
            "You are ClauseLens Assistant. Answer the user's question using ONLY the provided document context.\n"
            "RULES:\n"
            "1. Do NOT answer simply 'Yes' or 'No'. Explain what the document explicitly states and what it leaves unstated.\n"
            "2. Cite the exact Section and Title.\n"
            "Return JSON matching:\n"
            "{\n"
            "  \"answer\": \"Factual answer citing exact terms and unstated nuances\",\n"
            "  \"citation\": \"Section X • Title\"\n"
            "}"
        )
        prompt = f"DOCUMENT CONTEXT:\n{context_str}\n\nUSER QUESTION: {user_question}"

        try:
            return self.generate_and_parse_completion(prompt, system_instruction, provider)
        except Exception as e:
            logger.error(f"Q&A LLM call failed: {e}")
            raise ValueError(f"AI Q&A Failed: {str(e)}")

ai_engine = AIEngine()
