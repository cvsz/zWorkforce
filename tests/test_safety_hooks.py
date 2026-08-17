import unittest

from zworkforce.safety_hooks import SafetyLifecycleHooks, SafetyHookError
from zworkforce.tools import ToolExecutor, ToolError
from common import stack


class SafetyHooksTests(unittest.TestCase):
    def setUp(self):
        self.temp, self.settings, self.db, self.provider, self.engine, self.auth = stack()
        self.executor = ToolExecutor(self.settings, self.db)

    def tearDown(self):
        self.engine.shutdown()
        self.temp.cleanup()

    def test_is_read_only_tools(self):
        self.assertTrue(SafetyLifecycleHooks.is_read_only("workspace_read"))
        self.assertTrue(SafetyLifecycleHooks.is_read_only("workspace_list"))
        self.assertTrue(SafetyLifecycleHooks.is_read_only("calculator"))
        self.assertTrue(SafetyLifecycleHooks.is_read_only("memory_search"))
        self.assertFalse(SafetyLifecycleHooks.is_read_only("workspace_write"))
        self.assertFalse(SafetyLifecycleHooks.is_read_only("shell_exec"))

    def test_branch_guard_blocks_protected_branches_on_mutation(self):
        with self.assertRaises(SafetyHookError):
            SafetyLifecycleHooks.branch_guard("main", mutating=True)
        with self.assertRaises(SafetyHookError):
            SafetyLifecycleHooks.branch_guard("release/v3.0.3", mutating=True)
        with self.assertRaises(SafetyHookError):
            SafetyLifecycleHooks.branch_guard("master", mutating=True)
        # Feature branches should not be blocked
        SafetyLifecycleHooks.branch_guard("feature/safe-upgrade", mutating=True)

    def test_secret_guard_blocks_credentials(self):
        with self.assertRaises(SafetyHookError):
            SafetyLifecycleHooks.secret_guard("api_key = 'sk_live_12345678901234567890'")
        with self.assertRaises(SafetyHookError):
            SafetyLifecycleHooks.secret_guard("bearer ghp_12345678901234567890")

    def test_destructive_guard_blocks_destructive_commands(self):
        with self.assertRaises(SafetyHookError):
            SafetyLifecycleHooks.destructive_guard("rm -rf /")
        with self.assertRaises(SafetyHookError):
            SafetyLifecycleHooks.destructive_guard("mkfs.ext4 /dev/sda1")

    def test_tool_executor_enforces_safety_guard(self):
        with self.assertRaises(ToolError) as ctx:
            self.executor.execute(
                "workspace_write",
                {"path": "foo.txt", "content": "sk_test1234567890123456"},
                tenant_id="default",
                agent_id="test",
                actor="test",
            )
        self.assertIn("secret-guard", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
