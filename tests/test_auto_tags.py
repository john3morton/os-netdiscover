"""Tests for auto-tag rule matching (config path monkeypatched)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _paths  # noqa: F401
import auto_tags


class AutoTagsTests(unittest.TestCase):
    def test_disabled_returns_existing_tags(self):
        with mock.patch.object(auto_tags, "load_config", return_value={"enabled": False, "rules": []}):
            tags = auto_tags.apply_auto_tags({"tags": ["keep"], "vendor": "Apple"})
        self.assertEqual(tags, ["keep"])

    def test_vendor_and_subnet_rules(self):
        cfg = {
            "enabled": True,
            "rules": [
                {"match": {"vendor_contains": "Apple"}, "add_tags": ["apple"]},
                {"match": {"subnet_prefix": "192.168.10."}, "add_tags": ["vlan10"]},
                {"match": {"hostname_regex": "^iot-"}, "add_tags": ["iot"]},
            ],
        }
        with mock.patch.object(auto_tags, "load_config", return_value=cfg):
            tags = auto_tags.apply_auto_tags(
                {
                    "tags": [],
                    "vendor": "Apple Inc.",
                    "ip": "192.168.10.50",
                    "hostname": "iot-sensor-1",
                }
            )
        self.assertEqual(tags, ["apple", "vlan10", "iot"])

    def test_does_not_duplicate_tags(self):
        cfg = {
            "enabled": True,
            "rules": [{"match": {"vendor_contains": "Apple"}, "add_tags": ["apple"]}],
        }
        with mock.patch.object(auto_tags, "load_config", return_value=cfg):
            tags = auto_tags.apply_auto_tags({"tags": ["apple"], "vendor": "Apple"})
        self.assertEqual(tags, ["apple"])

    def test_load_config_from_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "auto_tags.json"
            path.write_text(
                json.dumps({"enabled": True, "rules": []}),
                encoding="utf-8",
            )
            with mock.patch.object(auto_tags, "CONFIG_PATH", str(path)):
                cfg = auto_tags.load_config()
        self.assertTrue(cfg["enabled"])
        self.assertEqual(cfg["rules"], [])


if __name__ == "__main__":
    unittest.main()
