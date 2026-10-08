#!/usr/local/bin/python3
"""Webhook alerts for NetDiscover lifecycle events (v2.1.0)."""

import json
import os
import urllib.request

CONFIG_PATH = "/var/db/netdiscover/alerts.json"


def load_config():
    defaults = {
        "enabled": False,
        "webhook_url": "",
        "events": ["new", "gone", "back", "changed"],
    }
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


def send_alerts(events):
    """POST matching events to configured webhook. Non-fatal on failure."""
    cfg = load_config()
    if not cfg.get("enabled") or not cfg.get("webhook_url"):
        return
    wanted = set(cfg.get("events") or [])
    for ev in events or []:
        et = ev.get("type") or ev.get("event_type") or ""
        if et not in wanted:
            continue
        body = {
            "source": "os-netdiscover",
            "event": et,
            "ip": ev.get("ip", ""),
            "mac": ev.get("mac", ""),
            "hostname": ev.get("hostname", ""),
            "time": ev.get("time") or ev.get("timestamp"),
            "details": ev.get("details") or {},
        }
        try:
            req = urllib.request.Request(
                cfg["webhook_url"],
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            continue
