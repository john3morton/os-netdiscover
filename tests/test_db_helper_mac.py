"""Tests for MAC normalization / device key helpers."""

from __future__ import annotations

import unittest

import _paths  # noqa: F401
from db_helper import device_key, normalize_mac


class NormalizeMacTests(unittest.TestCase):
    def test_colon_and_hyphen(self):
        self.assertEqual(normalize_mac("AA-BB-CC-DD-EE-FF"), "aa:bb:cc:dd:ee:ff")
        self.assertEqual(normalize_mac("aa:bb:cc:dd:ee:ff"), "aa:bb:cc:dd:ee:ff")

    def test_short_octets_padded(self):
        self.assertEqual(normalize_mac("a:b:c:d:e:f"), "0a:0b:0c:0d:0e:0f")

    def test_empty_and_invalid(self):
        self.assertEqual(normalize_mac(""), "")
        self.assertEqual(normalize_mac("not-a-mac"), "")
        self.assertEqual(normalize_mac("aa:bb:cc"), "")

    def test_synthetic_ip_key_passthrough(self):
        self.assertEqual(normalize_mac("ip:192.168.1.10"), "ip:192.168.1.10")


class DeviceKeyTests(unittest.TestCase):
    def test_prefers_mac(self):
        self.assertEqual(device_key("AA:BB:CC:DD:EE:FF", "10.0.0.1"), "aa:bb:cc:dd:ee:ff")

    def test_falls_back_to_ip(self):
        self.assertEqual(device_key("", "10.0.0.1"), "ip:10.0.0.1")

    def test_empty(self):
        self.assertEqual(device_key("", ""), "")


if __name__ == "__main__":
    unittest.main()
