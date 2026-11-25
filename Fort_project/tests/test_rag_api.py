import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from Fort_project.app.api import main


class FakeRAGService:
    def __init__(self):
        self.questions = []

    def answer(self, question):
        self.questions.append(question)
        return {
            "answer": "Tanaji led the attack. [S1]",
            "sources": [
                {
                    "citation": "[S1]",
                    "source": "Battle of Sinhagad - Wikipedia.pdf",
                    "page": 1,
                    "chunk_id": 0,
                    "distance": 0.25,
                }
            ],
        }


class RAGAPITests(unittest.TestCase):
    def test_chat_returns_answer_and_sources_and_rejects_blank_question(self):
        rag_service = FakeRAGService()
        with (
            patch.object(main, "YOLO", return_value=object()),
            patch.object(main, "RAGService", return_value=rag_service),
            TestClient(main.app) as client,
        ):
            response = client.post(
                "/api/chat",
                json={"question": "Who led the Sinhagad attack?"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["answer"], "Tanaji led the attack. [S1]")
            self.assertEqual(
                response.json()["sources"][0]["source"],
                "Battle of Sinhagad - Wikipedia.pdf",
            )
            self.assertEqual(rag_service.questions, ["Who led the Sinhagad attack?"])

            blank_response = client.post("/api/chat", json={"question": "   "})
            self.assertEqual(blank_response.status_code, 422)
            self.assertEqual(rag_service.questions, ["Who led the Sinhagad attack?"])


if __name__ == "__main__":
    unittest.main()
