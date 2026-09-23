import unittest
from ai_engine import ai_engine

class TestAIEngine(unittest.TestCase):
    
    def test_extract_json_valid(self):
        raw = "```json\n{\"test\": \"value\"}\n```"
        res = ai_engine._extract_json(raw)
        self.assertEqual(res["test"], "value")

    def test_extract_json_trailing_comma(self):
        raw = '{"findings": [{"title": "t1"},]}'
        res = ai_engine._extract_json(raw)
        self.assertEqual(len(res["findings"]), 1)

    def test_deduplicate_items(self):
        items = ["Term 1", " term 1 ", "term 2", "TERM 2", ""]
        res = ai_engine._deduplicate_items(items)
        self.assertEqual(res, ["Term 1", "term 2"])

if __name__ == "__main__":
    unittest.main()
