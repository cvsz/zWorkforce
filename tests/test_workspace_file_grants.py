from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import unittest

from tests.common import stack
from zworkforce.policy import PolicyEngine
from zworkforce.tools import tool_schemas


class WorkspaceFileGrantEnforcementTests(unittest.TestCase):
    def setUp(self):
        self.temp, self.settings, self.db, self.provider, self.dev_engine, self.auth = stack()
        self.project = self.settings.workspace_root / "project-a"
        self.project.mkdir(parents=True)
        (self.project / "readme.txt").write_text("grant-scoped-content", encoding="utf-8")

    def tearDown(self):
        self.dev_engine.shutdown()
        engine = getattr(self, "prod_engine", None)
        if engine is not None:
            engine.shutdown()
        self.temp.cleanup()

    @staticmethod
    def future():
        return (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(timespec="seconds")

    def make_engine(self, **settings_overrides):
        settings = replace(self.settings, env="production", embedded_workers=0, **settings_overrides)
        self.prod_engine = PolicyEngine(settings, self.db, self.provider)
        return self.prod_engine

    def grant(self, tenant_id="default", *, read=True, write=False, root_rel="project-a"):
        return self.db.upsert_workspace_grant(
            tenant_id,
            {
                "name": "File grant",
                "root_rel": root_rel,
                "read": read,
                "write": write,
                "commands": [],
                "network_policy": "deny",
                "enabled": True,
                "expires_at": self.future(),
            },
            "test",
        )

    def test_workspace_id_is_exposed_in_file_tool_schemas(self):
        schemas = {item["function"]["name"]: item for item in tool_schemas({"workspace_list", "workspace_read", "workspace_write"})}
        self.assertEqual(set(schemas), {"workspace_list", "workspace_read", "workspace_write"})
        for schema in schemas.values():
            properties = schema["function"]["parameters"]["properties"]
            self.assertIn("workspace_id", properties)
            self.assertEqual(properties["workspace_id"]["type"], "string")

    def test_production_file_tools_require_workspace_grant(self):
        engine = self.make_engine()
        for name, args in (
            ("workspace_list", {"path": "."}),
            ("workspace_read", {"path": "project-a/readme.txt"}),
            ("workspace_write", {"path": "project-a/new.txt", "content": "nope"}),
        ):
            with self.subTest(name=name):
                with self.assertRaisesRegex(Exception, "workspace_id grant is required"):
                    engine.tools.execute(name, args, tenant_id="default", agent_id="software-engineer", actor="test")

    def test_read_only_grant_scopes_paths_and_denies_write(self):
        engine = self.make_engine()
        grant = self.grant(read=True, write=False)
        workspace_id = grant["id"]

        listing = engine.tools.execute(
            "workspace_list", {"workspace_id": workspace_id, "path": "."},
            tenant_id="default", agent_id="software-engineer", actor="test",
        )
        self.assertEqual([item["name"] for item in listing], ["readme.txt"])
        content = engine.tools.execute(
            "workspace_read", {"workspace_id": workspace_id, "path": "readme.txt"},
            tenant_id="default", agent_id="software-engineer", actor="test",
        )
        self.assertEqual(content, "grant-scoped-content")

        with self.assertRaisesRegex(Exception, "does not allow writes"):
            engine.tools.execute(
                "workspace_write", {"workspace_id": workspace_id, "path": "new.txt", "content": "blocked"},
                tenant_id="default", agent_id="software-engineer", actor="test",
            )
        with self.assertRaisesRegex(Exception, "escapes workspace grant root"):
            engine.tools.execute(
                "workspace_read", {"workspace_id": workspace_id, "path": "../outside.txt"},
                tenant_id="default", agent_id="software-engineer", actor="test",
            )

    def test_cross_tenant_grant_and_host_kill_switch_fail_closed(self):
        engine = self.make_engine()
        grant = self.grant("default", read=True, write=True)
        self.db.ensure_tenant("acme", "Acme")
        with self.assertRaisesRegex(Exception, "not found or disabled"):
            engine.tools.execute(
                "workspace_read", {"workspace_id": grant["id"], "path": "readme.txt"},
                tenant_id="acme", agent_id="software-engineer", actor="test",
            )

        engine.shutdown()
        self.prod_engine = None
        read_disabled = self.make_engine(workspace_read_enabled=False)
        with self.assertRaisesRegex(Exception, "disabled by host policy"):
            read_disabled.tools.execute(
                "workspace_read", {"workspace_id": grant["id"], "path": "readme.txt"},
                tenant_id="default", agent_id="software-engineer", actor="test",
            )

        read_disabled.shutdown()
        self.prod_engine = None
        write_disabled = self.make_engine(workspace_write_enabled=False)
        with self.assertRaisesRegex(Exception, "disabled by host policy"):
            write_disabled.tools.execute(
                "workspace_write", {"workspace_id": grant["id"], "path": "new.txt", "content": "blocked"},
                tenant_id="default", agent_id="software-engineer", actor="test",
            )

    def test_workspace_write_tool_event_never_persists_raw_content(self):
        engine = self.make_engine()
        grant = self.grant(read=True, write=True)
        task, _ = engine.submit(
            "default",
            "software-engineer",
            "write one grant-scoped test file",
            actor="test",
            mutating=True,
        )
        sentinel = "WRITE-CONTENT-SECRET-SENTINEL"
        result = engine._execute_tool(
            task,
            "workspace_write",
            {
                "workspace_id": grant["id"],
                "path": "written.txt",
                "content": sentinel,
                "create_parents": False,
            },
        )
        self.assertTrue(result.get("written"), result)
        self.assertEqual((self.project / "written.txt").read_text(encoding="utf-8"), sentinel)

        events = self.db.list_tool_events("default", task["id"], 20)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["tool_name"], "workspace_write")
        self.assertEqual(events[0]["args"]["workspace_id"], grant["id"])
        self.assertEqual(events[0]["args"]["content_bytes"], len(sentinel.encode("utf-8")))
        self.assertNotIn("content", events[0]["args"])
        self.assertNotIn(sentinel, json.dumps(events[0], ensure_ascii=False))

    def test_development_keeps_legacy_host_root_compatibility(self):
        content = self.dev_engine.tools.execute(
            "workspace_read",
            {"path": "project-a/readme.txt"},
            tenant_id="default",
            agent_id="software-engineer",
            actor="test",
        )
        self.assertEqual(content, "grant-scoped-content")


if __name__ == "__main__":
    unittest.main()
