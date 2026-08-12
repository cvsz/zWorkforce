from pathlib import Path
import unittest


REQUIREMENTS = Path(__file__).resolve().parents[1] / "requirements.txt"


class DependencySecurityTests(unittest.TestCase):
    def test_asgi_dependencies_include_patched_security_versions(self):
        requirements = set(REQUIREMENTS.read_text(encoding="utf-8").splitlines())

        self.assertIn("fastapi==0.141.1", requirements)
        self.assertIn("starlette==1.6.0", requirements)


if __name__ == "__main__":
    unittest.main()
