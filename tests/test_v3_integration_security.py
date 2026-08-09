import unittest

from zworkforce.outbox import OutboxDispatcher, OutboxError
from zworkforce.skill_registry import RemoteSkillRegistry, SkillRegistryError
from zworkforce.secret_store import SecretResolver, SecretStoreError
from zworkforce.telemetry import OtlpHttpExporter


class IntegrationSecurityTests(unittest.TestCase):
    def test_outbox_remote_requires_https_and_allowlist(self):
        d=OutboxDispatcher(object())
        with self.assertRaises(OutboxError):d._validate_destination("http://example.com/hook")
        with self.assertRaises(OutboxError):d._validate_destination("https://example.com/hook")
        OutboxDispatcher(object(),allow_hosts=("example.com",))._validate_destination("https://hooks.example.com/x")
    def test_skill_registry_requires_allowlist(self):
        r=RemoteSkillRegistry(object(),"x"*32,())
        with self.assertRaises(SkillRegistryError):r._validate_url("https://skills.example.com/a")
        RemoteSkillRegistry(object(),"x"*32,("example.com",))._validate_url("https://skills.example.com/a")
    def test_vault_and_otlp_remote_http_rejected(self):
        with self.assertRaises(SecretStoreError):SecretResolver(vault_addr="http://vault.example.com",vault_token="x")
        with self.assertRaises(ValueError):OtlpHttpExporter("http://otel.example.com/v1/traces")

if __name__=="__main__":unittest.main()
