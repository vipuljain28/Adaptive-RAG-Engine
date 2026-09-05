"""
Unit tests for guardrails/guardrail_config.py
"""

import unittest
from guardrails.guardrail_config import (
    GUARDRAIL_NAME,
    DENIED_TOPICS,
    PII_ENTITIES,
    CONTENT_FILTERS,
)

class TestGuardrailConfig(unittest.TestCase):

    def test_guardrail_config_constants(self):
        self.assertTrue(len(GUARDRAIL_NAME) > 0)
        self.assertTrue(len(DENIED_TOPICS) > 0)
        self.assertTrue(len(PII_ENTITIES) > 0)
        self.assertTrue(len(CONTENT_FILTERS) > 0)

if __name__ == "__main__":
    unittest.main()
