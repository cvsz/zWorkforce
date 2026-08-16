import unittest

from tests.common import stack
from zworkforce.db import Database, SCHEMA_VERSION


class WorkspaceRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp, self.settings, self.db, self.provider, self.engine, self.auth = stack()

    def tearDown(self):
        self.engine.shutdown()
        self.temp.cleanup()

    def test_workspace_v5_entities_restart_persistence(self):
        self.assertGreaterEqual(SCHEMA_VERSION, 5)
        project = self.db.create_workspace_project("default", "Zeta", "test")
        conversation = self.db.create_workspace_conversation(
            "default", "test", project_id=project["id"], title="Persistent conversation"
        )
        message = self.db.append_workspace_message(
            "default", conversation["id"], "user", "test", content="persist me"
        )

        reopened = Database(self.settings.database_path, "default")
        self.assertEqual(reopened.get_workspace_project("default", project["id"])["name"], "Zeta")
        self.assertEqual(
            reopened.get_workspace_conversation("default", conversation["id"])["title"],
            "Persistent conversation",
        )
        messages = reopened.list_workspace_messages("default", conversation["id"])
        self.assertEqual([item["id"] for item in messages], [message["id"]])

    def test_tenant_isolation_and_cross_tenant_project_attachment(self):
        self.db.ensure_tenant("acme", "Acme")
        default_project = self.db.create_workspace_project("default", "Default Project", "owner")
        acme_project = self.db.create_workspace_project("acme", "Acme Project", "owner")

        self.assertIsNone(self.db.get_workspace_project("acme", default_project["id"]))
        self.assertEqual(
            [item["id"] for item in self.db.list_workspace_projects("default")],
            [default_project["id"]],
        )
        self.assertEqual(
            [item["id"] for item in self.db.list_workspace_projects("acme")],
            [acme_project["id"]],
        )
        with self.assertRaisesRegex(ValueError, "project not found"):
            self.db.create_workspace_conversation(
                "acme", "owner", project_id=default_project["id"], title="cross tenant"
            )

    def test_messages_have_deterministic_ordinals_and_search(self):
        project = self.db.create_workspace_project("default", "Search", "test")
        conversation = self.db.create_workspace_conversation(
            "default", "test", project_id=project["id"], title="Workspace search"
        )
        first = self.db.append_workspace_message(
            "default",
            conversation["id"],
            "user",
            "test",
            content="alpha message",
            artifact_ids=["artifact-1", "artifact-1", "artifact-2"],
        )
        second = self.db.append_workspace_message(
            "default", conversation["id"], "assistant", "agent", content="needle in response"
        )

        self.assertEqual(first["ordinal"], 1)
        self.assertEqual(second["ordinal"], 2)
        self.assertEqual(first["artifact_ids"], ["artifact-1", "artifact-2"])
        items = self.db.list_workspace_messages("default", conversation["id"])
        self.assertEqual([item["ordinal"] for item in items], [1, 2])
        search = self.db.list_workspace_conversations("default", query="needle")
        self.assertEqual([item["id"] for item in search], [conversation["id"]])

    def test_archived_conversation_is_readable_but_not_appendable(self):
        conversation = self.db.create_workspace_conversation("default", "test", title="Archive me")
        self.db.append_workspace_message("default", conversation["id"], "user", "test", content="before")
        archived = self.db.update_workspace_conversation(
            "default", conversation["id"], status="archived"
        )
        self.assertEqual(archived["status"], "archived")
        self.assertEqual(len(self.db.list_workspace_messages("default", conversation["id"])), 1)
        with self.assertRaisesRegex(ValueError, "archived conversation"):
            self.db.append_workspace_message(
                "default", conversation["id"], "user", "test", content="after"
            )

    def test_compliance_hold_blocks_delete_and_standard_delete_cascades(self):
        held = self.db.create_workspace_conversation(
            "default", "test", title="Held", retention_policy="compliance_hold"
        )
        with self.assertRaisesRegex(ValueError, "compliance hold"):
            self.db.delete_workspace_conversation("default", held["id"])

        standard = self.db.create_workspace_conversation("default", "test", title="Delete me")
        message = self.db.append_workspace_message(
            "default", standard["id"], "user", "test", content="gone"
        )
        self.assertTrue(self.db.delete_workspace_conversation("default", standard["id"]))
        self.assertIsNone(self.db.get_workspace_conversation("default", standard["id"]))
        self.assertIsNone(self.db.get_workspace_message("default", message["id"]))

    def test_parent_message_must_belong_to_same_conversation(self):
        first_conversation = self.db.create_workspace_conversation("default", "test", title="One")
        second_conversation = self.db.create_workspace_conversation("default", "test", title="Two")
        parent = self.db.append_workspace_message(
            "default", first_conversation["id"], "user", "test", content="parent"
        )
        with self.assertRaisesRegex(ValueError, "parent message not found"):
            self.db.append_workspace_message(
                "default",
                second_conversation["id"],
                "user",
                "test",
                content="child",
                parent_message_id=parent["id"],
            )

    def test_literal_search_does_not_treat_wildcards_as_query_operators(self):
        project = self.db.create_workspace_project("default", "100% Ready", "test")
        self.db.create_workspace_project("default", "1000 Ready", "test")
        matches = self.db.list_workspace_projects("default", query="100%")
        self.assertEqual([item["id"] for item in matches], [project["id"]])


if __name__ == "__main__":
    unittest.main()
