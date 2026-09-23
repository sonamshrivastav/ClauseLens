import unittest
from fastapi.testclient import TestClient
from main import app

class TestMainAPI(unittest.TestCase):
    
    def setUp(self):
        self.client = TestClient(app)

    def test_analyze_empty_text(self):
        response = self.client.post(
            "/api/analyze-text",
            json={"text": "   ", "provider": "auto"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("empty", response.json()["detail"])

    def test_static_files_served(self):
        response = self.client.get("/static/index.html")
        self.assertEqual(response.status_code, 200)

if __name__ == "__main__":
    unittest.main()
