"""Ensure documented / packaged versions stay aligned with Makefile PLUGIN_VERSION."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def makefile_version() -> str:
    text = (ROOT / "Makefile").read_text(encoding="utf-8")
    m = re.search(r"^PLUGIN_VERSION=\s*(\S+)", text, re.M)
    if not m:
        raise AssertionError("PLUGIN_VERSION not found in Makefile")
    return m.group(1)


class VersionConsistencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.version = makefile_version()

    def test_readme_version(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(f"**Version:** {self.version}", readme)
        self.assertIn(f"os-netdiscover-{self.version}.pkg", readme)

    def test_model_xml_version(self):
        xml = (
            ROOT
            / "src/opnsense/mvc/app/models/OPNsense/NetDiscover/NetDiscover.xml"
        ).read_text(encoding="utf-8")
        self.assertIn(f"<version>{self.version}</version>", xml)

    def test_ui_badge_version(self):
        volt = (
            ROOT / "src/opnsense/mvc/app/views/OPNsense/NetDiscover/index.volt"
        ).read_text(encoding="utf-8")
        self.assertIn(f">v{self.version}<", volt)

    def test_install_doc_pkg_name(self):
        install = (ROOT / "docs/INSTALL_OPNSENSE.md").read_text(encoding="utf-8")
        self.assertIn(f"os-netdiscover-{self.version}.pkg", install)
        self.assertNotRegex(install, r"os-netdiscover-2\.1\.0\.pkg")

    def test_changelog_leads_with_version(self):
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        # First ## heading after title should be the current version
        headings = re.findall(r"^##\s+(\S+)", changelog, re.M)
        self.assertTrue(headings, "CHANGELOG.md has no ## version headings")
        self.assertEqual(headings[0], self.version)


if __name__ == "__main__":
    unittest.main()
