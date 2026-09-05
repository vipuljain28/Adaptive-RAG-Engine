"""
Unit tests for app/utils/rag_engine.py
"""

import json
import unittest
from io import BytesIO
from unittest.mock import patch, MagicMock
from app.utils.rag_engine import run_rag_query

class TestRagEngine(unittest.TestCase):

    @patch("app.utils.rag_engine.get_bedrock_agent_runtime")
    @patch("app.utils.rag_engine.get_bedrock_runtime")
    def test_run_rag_query_basic(self, mock_get_runtime, mock_get_agent_runtime):
        mock_kb = MagicMock()
        mock_kb.retrieve.return_value = {
            "retrievalResults": [
                {
                    "content": {"text": "Bedrock is a managed service."},
                    "location": {"type": "S3", "s3Location": {"uri": "s3://bucket/doc.txt"}},
                    "score": 0.95
                }
            ]
        }
        mock_get_agent_runtime.return_value = mock_kb
        
        mock_bedrock = MagicMock()
        mock_response_body = json.dumps({
            "content": [{"text": "Bedrock provides access to foundation models."}],
            "usage": {"input_tokens": 100, "output_tokens": 50}
        }).encode("utf-8")
        
        mock_bedrock.invoke_model.return_value = {
            "body": BytesIO(mock_response_body)
        }
        mock_get_runtime.return_value = mock_bedrock
        
        result = run_rag_query("What is Bedrock?", model_choice="Quality (Claude Sonnet)")
        self.assertIn("answer", result)
        self.assertIn("cost_usd", result)
        self.assertEqual(result["answer"], "Bedrock provides access to foundation models.")

if __name__ == "__main__":
    unittest.main()
