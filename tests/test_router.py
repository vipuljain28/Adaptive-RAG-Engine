"""
Unit tests for gateway/router.py
"""

import unittest
from gateway.router import route
from gateway.llm_registry import MODELS

class TestRouter(unittest.TestCase):

    def test_registry_contains_models(self):
        self.assertIn("sonnet", MODELS)
        self.assertIn("haiku", MODELS)
        self.assertIn("vision", MODELS)
        self.assertIn("tinyllama", MODELS)

    def test_route_override_sonnet(self):
        decision = route("Explain architecture", user_selection="Quality (Claude Sonnet)")
        self.assertEqual(decision["model_id"], MODELS["sonnet"].model_id)

    def test_route_override_haiku(self):
        decision = route("Hi", user_selection="Fast (Claude Haiku)")
        self.assertEqual(decision["model_id"], MODELS["haiku"].model_id)

    def test_route_has_image(self):
        decision = route("Describe this image", has_image=True)
        self.assertEqual(decision["model_id"], MODELS["vision"].model_id)

if __name__ == "__main__":
    unittest.main()
