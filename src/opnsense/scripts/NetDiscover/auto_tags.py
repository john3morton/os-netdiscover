#!/usr/local/bin/python3
"""
Auto-tagging rules for NetDiscover (v2.1.0).

Config file /var/db/netdiscover/auto_tags.json example:
{
  "enabled": true,
  "rules": [
    {"match": {"vendor_contains": "Apple"}, "add_tags": ["apple"]},
    {"match": {"hostname_regex": "^iot-"}, "add_tags": ["iot"]},
    {"match": {"subnet_prefix": "192.168.10."}, "add_tags": ["vlan10"]}
  ]
}
"""

import json
import os
import re

CONFIG_PATH = "/var/db/netdiscover/auto_tags.json"


def load_config():
    defaults = {"enabled": False, "rules": []}
    if not os.path.exists(CONFIG_PATH):
        return defaults
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            defaults.update(data)
    except Exception:
        pass
    return defaults


def apply_auto_tags(rec: dict) -> list:
    """Return tags list after applying rules (does not overwrite existing tags)."""
    cfg = load_config()
    tags = list(rec.get("tags") or [])
    if isinstance(tags, str):
        try:
            tags = json.loads(tags) if tags else []
        except Exception:
            tags = []
    if not cfg.get("enabled"):
        return tags

    vendor = (rec.get("vendor") or rec.get("manufacturer") or "").lower()
    hostname = (rec.get("hostname") or "").lower()
    ip = rec.get("ip") or ""
    device_type = (rec.get("device_type") or "").lower()

    for rule in cfg.get("rules") or []:
        match = rule.get("match") or {}
        ok = True
        if "vendor_contains" in match:
            ok = ok and match["vendor_contains"].lower() in vendor
        if "hostname_contains" in match:
            ok = ok and match["hostname_contains"].lower() in hostname
        if "hostname_regex" in match:
            try:
                ok = ok and bool(re.search(match["hostname_regex"], hostname, re.I))
            except re.error:
                ok = False
        if "subnet_prefix" in match:
            ok = ok and ip.startswith(match["subnet_prefix"])
        if "device_type" in match:
            ok = ok and device_type == match["device_type"].lower()
        if not ok:
            continue
        for t in rule.get("add_tags") or []:
            if t and t not in tags:
                tags.append(t)
    return tags
