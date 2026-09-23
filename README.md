# ClauseLens AI

ClauseLens AI is a dynamic legal document intelligence and validation engine. It empowers users to analyze legal contracts factually by uncovering potential blind spots, isolating key obligations, and translating dense legal language into plain English. 

ClauseLens AI is **not** an AI lawyer. It does not provide legal advice, invent assumptions, or fill in the blanks. It strictly adheres to the facts stated in the uploaded documents and identifies where essential clauses are missing.

## Key Features
- **Dynamic Document Analysis**: Upload PDFs, text files, or paste contract text directly for real-time analysis.
- **Clause Breakdown**: Extracts individual clauses, summarizes their intent in plain English, highlights why they matter, and formulates neutral clarification questions for vague terms.
- **Blind-Spot Detection**: Identifies standard clauses that are unexpectedly missing from the provided document (e.g., missing termination clauses or jurisdiction).
- **Key Obligations & Dates**: Isolates the primary responsibilities and crucial timelines explicitly mentioned in the text.
- **AI Legal Assistant (Q&A)**: Ask specific questions about your document. The assistant responds exclusively using the provided text, citing the exact sections.

## Architecture & Technology Stack
- **Frontend**: Vanilla HTML/JS/CSS focusing on dynamic DOM manipulation, responsive UI, and resilient state management (zero leakage between analysis sessions).
- **Backend**: Python 3.12 + FastAPI. Handles robust PDF parsing (using `PyPDF2`) and API orchestration.
- **AI Engine Pipeline**:
  - Primary Provider: **Google Gemini 2.5 Flash** 
  - Fallback Provider: **Groq (GPT-OSS-120b)**
- **Resilience**: The system uses Native API JSON generation modes (`response_mime_type="application/json"` and `response_format={"type": "json_object"}`) paired with sophisticated HTTP failover loops to guarantee structured, hallucination-free output.

## Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone <repository_url>
   cd ClauseLens
   ```

2. **Create a Python Virtual Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration:**
   Create a `.env` file in the root directory (refer to `.env.example`).
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   GROQ_API_KEY=your_groq_api_key_here
   ```
   *Note: Never expose these keys in your frontend or commit them to version control.*

5. **Run the Application:**
   ```bash
   python -m uvicorn main:app --port 8000
   ```
   Open `http://localhost:8000/static/index.html` in your browser.

## Limitations
- **Scanned PDFs**: If a PDF is a scanned image rather than a text-based document, the current implementation (using `PyPDF2`) cannot extract the text. OCR capabilities are not included.
- **Length**: Extremely long documents may be truncated before being sent to the AI depending on the specific model's context window.

## Legal Disclaimer
ClauseLens AI is an experimental tool designed for informational purposes only. It is **not** a substitute for professional legal counsel. Always consult a qualified attorney before signing any legal agreements.
