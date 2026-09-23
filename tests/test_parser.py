import unittest
from parser import DocumentParser

class TestDocumentParser(unittest.TestCase):
    
    def test_extract_text_from_txt(self):
        text_bytes = b"Hello world! This is a contract."
        result = DocumentParser.extract_text_from_txt(text_bytes)
        self.assertEqual(result, "Hello world! This is a contract.")
        
    def test_extract_text_empty_txt(self):
        with self.assertRaises(ValueError):
            DocumentParser.extract_text_from_txt(b"   ")

    def test_parse_document_to_clauses(self):
        sample_doc = "Section 1. Definitions\nThis is the definition clause.\n\nSection 2. Term\nThe term is one year."
        clauses = DocumentParser.parse_document_to_clauses(sample_doc)
        
        self.assertEqual(len(clauses), 2)
        self.assertEqual(clauses[0]["title"], "Definitions")
        self.assertTrue("This is the definition" in clauses[0]["originalText"])
        self.assertEqual(clauses[1]["title"], "Term")

if __name__ == "__main__":
    unittest.main()
