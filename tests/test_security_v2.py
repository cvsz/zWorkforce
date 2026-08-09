import os
import unittest

from common import stack
from zworkforce.config import BootstrapKey
from zworkforce.security import AuthManager
from zworkforce.security import RateLimiter, redact, resolve_tenant
from zworkforce.tools import ToolExecutor, ToolError

class SecurityV2Tests(unittest.TestCase):
    def setUp(self): self.temp,self.settings,self.db,self.provider,self.engine,self.auth=stack()
    def tearDown(self): self.engine.shutdown(); self.temp.cleanup()
    def test_bootstrap_key_auth_and_superadmin_tenant_switch(self):
        p=self.auth.authenticate("Bearer test-admin-secret",None); self.assertEqual(p.role,"superadmin"); self.assertEqual(resolve_tenant(p,"acme"),"acme")
    def test_bootstrap_key_rotation_revokes_old_secret(self):
        AuthManager(self.db, (BootstrapKey("rotated-secret", "superadmin", "default", "test-admin"),)); self.assertIsNone(self.auth.authenticate(None, "test-admin-secret"))
        fresh = AuthManager(self.db).authenticate(None, "rotated-secret"); self.assertIsNotNone(fresh)
        enabled = [x for x in self.db.list_api_keys("default") if not x["disabled"] and x["name"] == "test-admin"]; self.assertEqual(len(enabled), 1)
    def test_dynamic_key_roundtrip_and_revoke(self):
        key_id,secret=self.auth.create_key("default","viewer","viewer",["workforce:read"]); p=self.auth.authenticate(None,secret); self.assertEqual(p.name,"viewer"); self.assertTrue(p.has_scope("workforce:read")); self.db.revoke_api_key("default",key_id); self.assertIsNone(self.auth.authenticate(None,secret))
    def test_rate_limiter(self):
        r=RateLimiter(2); self.assertTrue(r.allow("x")[0]); self.assertTrue(r.allow("x")[0]); self.assertFalse(r.allow("x")[0])
    def test_redaction(self): self.assertEqual(redact({"api_key":"abc","nested":{"password":"p"}}),{"api_key":"[REDACTED]","nested":{"password":"[REDACTED]"}})
    def test_ssrf_private_address_rejected(self):
        from dataclasses import replace
        settings=replace(self.settings,http_allowlist=("localhost",)); tools=ToolExecutor(settings,self.db)
        with self.assertRaises(ToolError): tools._validate_url("http://localhost:8080/x")
    def test_shell_does_not_inherit_secrets(self):
        from dataclasses import replace
        os.environ["TOP_SECRET_FOR_TEST"]="do-not-leak"; settings=replace(self.settings,shell_enabled=True,shell_allowlist=("python3",),shell_env_allowlist=("PATH",)); tools=ToolExecutor(settings,self.db)
        result=tools.execute("shell_exec",{"command":"python3","args":["-c","import os; print(os.getenv('TOP_SECRET_FOR_TEST','missing'))"]},tenant_id="default",agent_id="software-engineer",actor="test"); self.assertIn("missing",result["stdout"])

if __name__ == "__main__": unittest.main()
