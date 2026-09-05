"""
Unit tests for app/utils/conversation_store.py
"""

import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from app.utils.conversation_store import (
    init_db,
    create_conversation,
    save_message,
    get_all_conversations,
    get_conversation_messages,
    delete_conversation,
    get_all_stats,
)

class TestConversationStore(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp_dir.name, "test_conversations.db")

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_full_lifecycle(self):
        with patch("app.utils.conversation_store.DB_PATH", self.db_path):
            init_db()
            
            conv_id = create_conversation("Test Conversation")
            self.assertTrue(len(conv_id) > 0)
            
            save_message(conv_id, "user", "Hello world")
            save_message(conv_id, "assistant", "Hello user", model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0", model_name="Claude 3.5 Sonnet", input_tokens=10, output_tokens=5, cost_usd=0.0001)
            
            convs = get_all_conversations()
            self.assertTrue(any(c["id"] == conv_id for c in convs))
            
            msgs = get_conversation_messages(conv_id)
            self.assertEqual(len(msgs), 2)
            self.assertEqual(msgs[0]["content"], "Hello world")
            
            stats = get_all_stats()
            self.assertGreaterEqual(stats["total_messages"], 2)
            
            delete_conversation(conv_id)
            convs_after = get_all_conversations()
            self.assertFalse(any(c["id"] == conv_id for c in convs_after))

if __name__ == "__main__":
    unittest.main()
