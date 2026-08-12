from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


WINDOWS_APP = (
    Path(__file__).resolve().parents[1]
    / "packages"
    / "zarvis"
    / "apps"
    / "zarvis-windows"
)


class ZarvisWindowsTargetingTests(unittest.TestCase):
    def test_linux_restore_is_enabled_for_all_windows_projects(self):
        props = WINDOWS_APP / "Directory.Build.props"

        self.assertTrue(props.is_file(), "zarvis-windows must define shared build properties")
        root = ET.parse(props).getroot()
        values = [
            element.text.strip().lower()
            for element in root.iter("EnableWindowsTargeting")
            if element.text
        ]
        self.assertIn("true", values)


if __name__ == "__main__":
    unittest.main()
