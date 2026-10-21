"""Tests for hostname / port fingerprint helpers."""

from __future__ import annotations

import unittest

import _paths  # noqa: F401
from device_patterns import guess_device_type_from_hostname, guess_device_type_from_ports


class HostnamePatternTests(unittest.TestCase):
    def test_iphone(self):
        self.assertEqual(guess_device_type_from_hostname("iPhone-John"), "iPhone")

    def test_raspberry(self):
        self.assertEqual(guess_device_type_from_hostname("raspberrypi"), "Raspberry Pi")

    def test_printer(self):
        self.assertEqual(guess_device_type_from_hostname("office-printer-1"), "Printer")

    def test_empty(self):
        self.assertIsNone(guess_device_type_from_hostname(""))
        self.assertIsNone(guess_device_type_from_hostname(None))  # type: ignore[arg-type]


class PortPatternTests(unittest.TestCase):
    def test_network_printer(self):
        self.assertEqual(guess_device_type_from_ports([631, 9100]), "Network Printer")

    def test_empty(self):
        self.assertIsNone(guess_device_type_from_ports([]))


if __name__ == "__main__":
    unittest.main()
