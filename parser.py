import io
import re
from typing import List, Dict, Any
from pypdf import PdfReader

class DocumentParser:
    """Extracts raw text from PDF/TXT files and splits contract into structured clauses."""

    @staticmethod
    def extract_text_from_pdf(file_bytes: bytes) -> str:
        """
        Extract raw text from a PDF file.

        Args:
            file_bytes (bytes): The binary contents of the PDF file.

        Returns:
            str: The extracted text from all pages joined by double newlines.

        Raises:
            ValueError: If no text can be extracted from the PDF.
        """
        pdf_file = io.BytesIO(file_bytes)
        reader = PdfReader(pdf_file)
        full_text = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                full_text.append(text.strip())
        result = "\n\n".join(full_text).strip()
        if not result:
            raise ValueError("No readable text found in PDF. The file may be empty or a scanned image.")
        return result

    @staticmethod
    def extract_text_from_txt(file_bytes: bytes) -> str:
        """
        Decode and extract text from a plain text file.

        Args:
            file_bytes (bytes): The binary contents of the TXT file.

        Returns:
            str: The decoded utf-8 string.

        Raises:
            ValueError: If the file is completely empty.
        """
        text = file_bytes.decode('utf-8', errors='ignore').strip()
        if not text:
            raise ValueError("The uploaded text file is empty.")
        return text

    @classmethod
    def parse_document_to_clauses(cls, full_text: str) -> List[Dict[str, Any]]:
        """
        Parse raw document text into structured clauses based on common legal numbering.

        Args:
            full_text (str): The entire raw text of the document.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries representing individual clauses.
                Each dictionary contains 'id', 'number', 'title', and 'originalText'.
        """
        lines = full_text.split('\n')
        clauses = []
        current_title = "Preamble & General Terms"
        current_num = "Section 1"
        current_buffer = []
        clause_counter = 1

        header_pattern = re.compile(
            r'^(Section|Clause|Article|\d+[\.\)])\s*(\d+[\.\d\w]*)?\s*[-:]?\s*(.*)', 
            re.IGNORECASE
        )

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            match = header_pattern.match(line_str)
            if match and len(line_str) < 120 and (len(current_buffer) > 0 or clause_counter == 1):
                if current_buffer:
                    clauses.append({
                        "id": f"cl-{clause_counter}",
                        "number": current_num,
                        "title": current_title if current_title else f"Clause {clause_counter}",
                        "originalText": "\n".join(current_buffer).strip()
                    })
                    clause_counter += 1
                    current_buffer = []

                current_num = f"{match.group(1)} {match.group(2)}".strip() if match.group(2) else f"Clause {clause_counter}"
                current_title = match.group(3).strip() if match.group(3) else line_str
                if not current_title:
                    current_title = f"Terms Section {clause_counter}"
            else:
                current_buffer.append(line_str)

        if current_buffer:
            clauses.append({
                "id": f"cl-{clause_counter}",
                "number": current_num,
                "title": current_title if current_title else f"Clause {clause_counter}",
                "originalText": "\n".join(current_buffer).strip()
            })

        if len(clauses) <= 1:
            # First try splitting by double newline
            paragraphs = [p.strip() for p in full_text.split("\n\n") if len(p.strip()) > 30]
            
            # If still empty (e.g., pypdf extracted everything without newlines), just chunk it
            if not paragraphs:
                import textwrap
                paragraphs = textwrap.wrap(full_text, width=800)
                
            clauses = []
            for idx, para in enumerate(paragraphs, 1):
                words = para.split()
                first_words = " ".join(words[:5]) if len(words) >= 5 else "Clause"
                clauses.append({
                    "id": f"cl-{idx}",
                    "number": f"Section {idx}",
                    "title": f"{first_words}...",
                    "originalText": para
                })

        return clauses
