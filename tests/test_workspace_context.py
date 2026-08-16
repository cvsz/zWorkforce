import hashlib
import unittest

from tests.common import stack


class WorkspaceContextTests(unittest.TestCase):
    def setUp(self):
        self.temp, self.settings, self.db, self.provider, self.engine, self.auth = stack()

    def tearDown(self):
        self.engine.shutdown()
        self.temp.cleanup()

    def _conversation_with_messages(self):
        conversation = self.db.create_workspace_conversation("default", "test", title="Context")
        first = self.db.append_workspace_message(
            "default", conversation["id"], "user", "test", content="alpha"
        )
        second = self.db.append_workspace_message(
            "default", conversation["id"], "assistant", "agent", content="beta response"
        )
        return conversation, first, second

    def test_snapshot_membership_is_deterministic_and_tenant_scoped(self):
        conversation, first, second = self._conversation_with_messages()
        snapshot = self.db.create_workspace_context_snapshot(
            "default",
            conversation["id"],
            "test",
            model_id="test-model",
            context_ceiling_tokens=8192,
            compaction_threshold_tokens=6144,
            message_ids=[second["id"], first["id"], second["id"]],
        )

        self.assertEqual([item["message_id"] for item in snapshot["members"]], [first["id"], second["id"]])
        self.assertGreater(snapshot["estimated_tokens"], 0)
        self.assertEqual(snapshot["summary_sha256"], "")

        self.db.ensure_tenant("other", "Other")
        self.assertIsNone(self.db.get_workspace_context_snapshot("other", snapshot["id"]))
        with self.assertRaisesRegex(ValueError, "conversation not found"):
            self.db.create_workspace_context_snapshot(
                "other",
                conversation["id"],
                "test",
                model_id="test-model",
                context_ceiling_tokens=8192,
                compaction_threshold_tokens=6144,
            )

    def test_compaction_preserves_history_and_hashes_summary(self):
        conversation, first, second = self._conversation_with_messages()
        summary = "User asked alpha; assistant returned beta response."
        compacted = self.db.compact_workspace_conversation(
            "default",
            conversation["id"],
            "test",
            model_id="test-model",
            context_ceiling_tokens=4096,
            compaction_threshold_tokens=3000,
            summary=summary,
        )

        self.assertEqual(compacted["summary"], summary)
        self.assertEqual(compacted["summary_sha256"], hashlib.sha256(summary.encode("utf-8")).hexdigest())
        messages = self.db.list_workspace_messages("default", conversation["id"])
        self.assertEqual([item["id"] for item in messages], [first["id"], second["id"]])

        historical = self.db.get_workspace_context_snapshot("default", compacted["id"])
        self.assertEqual(historical["summary"], summary)
        self.assertEqual(len(historical["members"]), 2)

    def test_snapshot_rejects_foreign_message_and_invalid_budget(self):
        conversation, first, _ = self._conversation_with_messages()
        other = self.db.create_workspace_conversation("default", "test", title="Other")
        foreign = self.db.append_workspace_message(
            "default", other["id"], "user", "test", content="foreign"
        )

        with self.assertRaisesRegex(ValueError, "message not found in conversation"):
            self.db.create_workspace_context_snapshot(
                "default",
                conversation["id"],
                "test",
                model_id="test-model",
                context_ceiling_tokens=4096,
                compaction_threshold_tokens=3000,
                message_ids=[first["id"], foreign["id"]],
            )
        with self.assertRaisesRegex(ValueError, "cannot exceed"):
            self.db.create_workspace_context_snapshot(
                "default",
                conversation["id"],
                "test",
                model_id="test-model",
                context_ceiling_tokens=2048,
                compaction_threshold_tokens=4096,
            )
        with self.assertRaisesRegex(ValueError, "summary is required"):
            self.db.compact_workspace_conversation(
                "default",
                conversation["id"],
                "test",
                model_id="test-model",
                context_ceiling_tokens=4096,
                compaction_threshold_tokens=3000,
                summary="",
            )


if __name__ == "__main__":
    unittest.main()
