import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from tests.common import stack
from zworkforce.workspace_command_api import WorkspaceCommandApp
from zworkforce.workspace_commands import parse_workspace_command


class WorkspaceCommandParserTests(unittest.TestCase):
    def test_parser_normalizes_name_and_preserves_argument(self):
        command, argument = parse_workspace_command("  /CoMpAcT   summarize messages 1-20  ")
        self.assertEqual(command.name, "compact")
        self.assertEqual(command.scope, "workspace:compact")
        self.assertEqual(argument, "summarize messages 1-20")

    def test_unknown_and_non_slash_commands_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "must start with /"):
            parse_workspace_command("status")
        with self.assertRaisesRegex(ValueError, "unknown workspace command"):
            parse_workspace_command("/does-not-exist anything")


class WorkspaceCommandApiTests(unittest.TestCase):
    def setUp(self):
        self.temp, self.settings, self.db, self.provider, self.engine, self.auth = stack()
        self.app = WorkspaceCommandApp(self.settings, self.db, self.engine, self.auth, self.provider)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self.app.handler())
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.engine.shutdown()
        self.temp.cleanup()

    def req(self, path, method="GET", body=None, token="test-admin-secret", timeout=10):
        headers = {"Authorization": f"Bearer {token}"}
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read())

    def error(self, path, method="GET", body=None, token="test-admin-secret"):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.req(path, method, body, token)
        return ctx.exception.code, json.loads(ctx.exception.read())

    def test_discovery_reports_server_authorized_availability(self):
        _, viewer = self.auth.create_key("default", "command-viewer", "viewer", ["workspace:read"])
        status, payload = self.req("/api/v1/workspaces/commands", token=viewer)
        self.assertEqual(status, 200)
        commands = {item["name"]: item for item in payload["items"]}
        self.assertEqual(set(commands), {
            "plan", "review", "compact", "goal", "status", "artifacts", "cost", "skill", "workflow", "feedback"
        })
        self.assertFalse(commands["compact"]["available"])
        self.assertFalse(commands["skill"]["available"])

    def test_resolve_enforces_command_specific_scope_without_execution(self):
        _, conversation = self.req(
            "/api/v1/workspaces/conversations", "POST", {"title": "Command resolution"}
        )
        _, denied = self.auth.create_key(
            "default", "command-writer", "operator", ["workspace:read", "workspace:write"]
        )
        status, payload = self.error(
            "/api/v1/workspaces/commands/resolve",
            "POST",
            {"text": "/compact summarize the conversation"},
            token=denied,
        )
        self.assertEqual(status, 403)
        self.assertEqual(payload["error"]["code"], "workspace_command_not_authorized")

        _, allowed = self.auth.create_key(
            "default", "command-compactor", "operator", ["workspace:read", "workspace:compact"]
        )
        status, payload = self.req(
            "/api/v1/workspaces/commands/resolve",
            "POST",
            {"text": "/compact summarize the conversation"},
            token=allowed,
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["resolved"])
        self.assertEqual(payload["target"], "workspace.compact")
        self.assertEqual(payload["argument"], "summarize the conversation")
        self.assertTrue(payload["mutating"])
        self.assertEqual(self.db.list_workspace_context_snapshots("default", conversation["id"]), [])

    def test_resolve_does_not_let_workspace_scope_impersonate_admin_skill_scope(self):
        _, operator = self.auth.create_key(
            "default", "command-operator", "operator", ["workspace:read", "workspace:write", "workspace:compact"]
        )
        status, payload = self.error(
            "/api/v1/workspaces/commands/resolve",
            "POST",
            {"text": "/skill install something"},
            token=operator,
        )
        self.assertEqual(status, 403)
        self.assertEqual(payload["error"]["code"], "workspace_command_not_authorized")

    def test_invalid_command_returns_bounded_client_error(self):
        status, payload = self.error(
            "/api/v1/workspaces/commands/resolve",
            "POST",
            {"text": "status"},
        )
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"]["code"], "invalid_request")


if __name__ == "__main__":
    unittest.main()
