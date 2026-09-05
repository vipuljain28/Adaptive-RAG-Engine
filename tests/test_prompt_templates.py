"""
Unit tests for app/utils/prompt_templates.py
"""

import unittest
from app.utils.prompt_templates import build_rag_prompt

class TestPromptTemplates(unittest.TestCase):

    def test_build_rag_prompt_sections(self):
        chunks = [{"content": "Sample content", "source": "s3://bucket/test.pdf", "score": 0.9}]
        prompt = build_rag_prompt("What is AWS?", chunks)
        self.assertIn("ROLE", prompt)
        self.assertIn("CONTEXT", prompt)
        self.assertIn("TASK", prompt)
        self.assertIn("FORMAT", prompt)
        self.assertIn("CONSTRAINTS", prompt)
        self.assertIn("Sample content", prompt)
        self.assertIn("What is AWS?", prompt)

if __name__ == "__main__":
    unittest.main()
