"""
Integration tests for Knowledge Assistant components using mock/stubs.
"""

import json
import unittest
from io import BytesIO
from unittest.mock import patch, MagicMock
from app.utils.rag_engine import run_rag_query

class TestIntegrationStubs(unittest.TestCase):

    @patch("app.utils.rag_engine.get_bedrock_agent_runtime")
    @patch("app.utils.rag_engine.get_bedrock_runtime")
    def test_full_rag_pipeline_end_to_end_stub(self, mock_get_runtime, mock_get_agent_runtime):
        mock_kb = MagicMock()
        mock_kb.retrieve.return_value = {
            "retrievalResults": [
                {
                    "content": {"text": "Architecture uses S3, Bedrock KB, OpenSearch, and Claude 3.5."},
                    "location": {"type": "S3", "s3Location": {"uri": "s3://knowledge-assistant-docs/arch.pdf"}},
                    "score": 0.92
                }
            ]
        }
        mock_get_agent_runtime.return_value = mock_kb
        
        mock_bedrock = MagicMock()
        mock_response_body = json.dumps({
            "content": [{"text": "The architecture leverages Bedrock Knowledge Base and Claude 3.5."}],
            "usage": {"input_tokens": 150, "output_tokens": 80}
        }).encode("utf-8")
        mock_bedrock.invoke_model.return_value = {
            "body": BytesIO(mock_response_body)
        }
        mock_get_runtime.return_value = mock_bedrock
        
        res = run_rag_query("What is the system architecture?", model_choice="Quality (Claude Sonnet)")
        self.assertIn("answer", res)
        self.assertIn("sources", res)
        self.assertEqual(len(res["sources"]), 1)
        self.assertGreater(res["cost_usd"], 0)

if __name__ == "__main__":
    unittest.main()
