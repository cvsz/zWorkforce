from pathlib import Path
import re
import unittest


REQUIREMENTS = Path(__file__).resolve().parents[1] / "requirements.txt"


class DependencySecurityTests(unittest.TestCase):
    def test_asgi_dependencies_include_patched_security_versions(self):
        requirements = {}
        for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
            match = re.fullmatch(r"([A-Za-z0-9_-]+)==([0-9]+(?:\.[0-9]+)*)", line.strip())
            if match:
                requirements[match.group(1).lower()] = tuple(
                    int(part) for part in match.group(2).split(".")
                )

        self.assertGreaterEqual(requirements.get("fastapi", ()), (0, 141, 1))
        self.assertGreaterEqual(requirements.get("starlette", ()), (1, 6, 0))


if __name__ == "__main__":
    unittest.main()
