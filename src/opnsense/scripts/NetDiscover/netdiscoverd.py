#!/usr/local/bin/python3
# NetDiscover v2.1.0 — device identity keyed by MAC

import sys
import os
import sqlite3

# Early startup logging to catch crashes
STARTUP_LOG = "/var/db/netdiscover/startup.log"
try:
    os.makedirs("/var/db/netdiscover", exist_ok=True)
    with open(STARTUP_LOG, "a") as f:
        import datetime
        f.write(f"\n{datetime.datetime.now()} === DAEMON STARTING PID={os.getpid()} ===\n")
        f.flush()
except Exception:
    pass

# Import device fingerprinting patterns
try:
    sys.path.insert(0, '/usr/local/opnsense/scripts/NetDiscover')
    from device_patterns import (
        guess_device_type_from_hostname,
        guess_device_type_from_ports,
        guess_device_type_from_mdns,
        guess_device_from_banner,
        merge_device_identifications
    )
    HAS_PATTERNS = True
    with open(STARTUP_LOG, "a") as f:
        f.write("  ✓ device_patterns imported successfully\n")
        f.flush()
except ImportError as e:
    HAS_PATTERNS = False
    with open(STARTUP_LOG, "a") as f:
        f.write(f"  ✗ device_patterns import failed: {e}\n")
        f.flush()
except Exception as e:
    HAS_PATTERNS = False
    with open(STARTUP_LOG, "a") as f:
        f.write(f"  ✗ device_patterns error: {e}\n")
        f.flush()

# Import DHCP analyzer
try:
    from dhcp_analyzer import get_dhcp_info_batch
    HAS_DHCP_ANALYZER = True
except ImportError:
    HAS_DHCP_ANALYZER = False

# Import AP detector (v2.0.0)
try:
    from ap_detector import discover_ap_clients
    HAS_AP_DETECTOR = True
except ImportError:
    HAS_AP_DETECTOR = False

# Import AP syslog parser (v2.0.2)
try:
    from ap_syslog_parser import parse_multiple_syslogs, resolve_ap_identifier
    HAS_SYSLOG_PARSER = True
except ImportError:
    HAS_SYSLOG_PARSER = False

try:
    from alerts import send_alerts
    HAS_ALERTS = True
except ImportError:
    HAS_ALERTS = False

try:
    from auto_tags import apply_auto_tags
    HAS_AUTO_TAGS = True
except ImportError:
    HAS_AUTO_TAGS = False

import argparse
import json
import os
import re
import shlex
import socket
import struct
import subprocess
import threading
import time
import urllib.request
import xml.etree.ElementTree as ET
from ipaddress import ip_network, ip_address
from typing import Dict, List, Optional, Set, Tuple

DB_DIR = "/var/db/netdiscover"
OUT_FILE = os.path.join(DB_DIR, "devices.json")
STATE_FILE = os.path.join(DB_DIR, "state.json")
LOG_FILE = os.path.join(DB_DIR, "netdiscoverd.log")
DB_FILE = os.path.join(DB_DIR, "netdiscover.db")
OUI_DB_FILE = os.path.join(DB_DIR, "oui.db")
DEFAULT_OUI = "/var/db/netdiscover/oui.csv"

# Status timing thresholds (v1.5.0 - Dual State System)
# OFFLINE_THRESHOLD calculated dynamically (2 × scan_interval)
MISSING_THRESHOLD = 2592000  # 30 days - mark as missing
GONE_THRESHOLD = 5184000     # 60 days (30 + 30) - mark as gone after being missing for 30 days
FLAG_EXPIRY = 86400          # 24 hours - lifecycle flags expire
NO_AUTO_PRUNE = True         # Never automatically prune devices

def log_error(msg):
    """Log errors and important events only"""
    try:
        ensure_db_dir()
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            import datetime
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"{ts} {msg}\n")
            f.flush()
    except Exception:
        # Silently fail - don't cascade logging errors
        pass

SSDP_MCAST = ("239.255.255.250", 1900)
MDNS_MCAST = ("224.0.0.251", 5353)
LLMNR_MCAST = ("224.0.0.252", 5355)

BUF = 65535

def run(cmd: str, timeout: int = 30) -> str:
    try:
        p = subprocess.run(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            check=False,
            text=True,
        )
        return p.stdout or ""
    except Exception:
        return ""

def which(binname: str) -> str:
    out = run(f"command -v {shlex.quote(binname)}")
    return out.strip()

def ensure_db_dir():
    try:
        os.makedirs(DB_DIR, exist_ok=True)
    except Exception as e:
        print(f"ERROR creating DB_DIR: {e}", file=sys.stderr)
        raise

def load_json(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path: str, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    os.replace(tmp, path)

def normalize_mac(mac: str) -> str:
    """Normalize MAC to lowercase colon-separated form; empty if invalid/missing."""
    if not mac:
        return ""
    m = str(mac).strip().lower().replace("-", ":")
    parts = [p for p in m.split(":") if p != ""]
    if len(parts) != 6:
        return m if m.startswith("ip:") else ""
    try:
        return ":".join(f"{int(p, 16):02x}" for p in parts)
    except ValueError:
        return ""

def device_key(mac: str, ip: str) -> str:
    """Stable device identity: real MAC, or synthetic ip:<addr> when MAC unknown."""
    m = normalize_mac(mac)
    if m:
        return m
    if ip:
        return f"ip:{ip}"
    return ""

def _devices_pk_is_mac(cur) -> bool:
    cur.execute("PRAGMA table_info(devices)")
    rows = cur.fetchall()
    if not rows:
        return False
    pk_cols = [r[1] for r in rows if r[5]]
    return pk_cols == ["mac"]

def _override_pk_is_mac(cur) -> bool:
    cur.execute("PRAGMA table_info(device_overrides)")
    rows = cur.fetchall()
    pk_cols = [r[1] for r in rows if r[5]]
    return pk_cols == ["mac"]

def _merge_device_rows(rows: List[Dict]) -> Dict:
    """Pick newest row by last_seen; keep earliest first_seen; fill empty fields from others."""
    best = max(rows, key=lambda r: int(r.get("last_seen") or 0))
    merged = dict(best)
    first_vals = [int(r.get("first_seen") or 0) for r in rows if r.get("first_seen")]
    if first_vals:
        merged["first_seen"] = min(first_vals)
    ordered = sorted(rows, key=lambda r: int(r.get("last_seen") or 0), reverse=True)
    fill_keys = [
        "hostname", "vendor", "connection_state", "lifecycle_flags", "status", "dhcp_type",
        "device_type", "device_type_source", "device_category", "manufacturer", "model", "os",
        "os_version", "discovered_manufacturer", "discovered_model", "discovered_os",
        "snmp_sysname", "snmp_sysdescr", "interface", "subnet", "notes",
        "connected_to_ap", "ap_name", "exhaustive_ports", "mdns_services", "open_ports",
        "banners", "tags",
    ]
    for k in fill_keys:
        if merged.get(k):
            continue
        for r in ordered:
            if r.get(k):
                merged[k] = r[k]
                break
    if any(int(r.get("flag_acknowledged") or 0) for r in rows):
        merged["flag_acknowledged"] = 1
    return merged

def migrate_devices_to_mac_pk(conn) -> bool:
    """Rebuild devices/overrides with MAC primary key; dedupe IP-keyed duplicates."""
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='devices'")
    if not cur.fetchone():
        return False
    if _devices_pk_is_mac(cur):
        return False

    log_error("Migrating devices table from IP primary key to MAC primary key...")
    cur.execute("ALTER TABLE devices RENAME TO devices_ip_legacy")

    cur.execute('''
        CREATE TABLE devices (
            mac TEXT PRIMARY KEY,
            ip TEXT,
            hostname TEXT,
            hostname_override INTEGER DEFAULT 0,
            vendor TEXT,
            connection_state TEXT DEFAULT 'online',
            lifecycle_flags TEXT,
            status TEXT,
            dhcp_type TEXT,
            device_type TEXT,
            device_type_source TEXT,
            device_category TEXT,
            tags TEXT,
            discovered_manufacturer TEXT,
            discovered_model TEXT,
            discovered_os TEXT,
            manufacturer TEXT,
            model TEXT,
            os TEXT,
            os_version TEXT,
            exhaustive_ports TEXT,
            exhaustive_ports_time INTEGER,
            mdns_services TEXT,
            open_ports TEXT,
            banners TEXT,
            snmp_sysname TEXT,
            snmp_sysdescr TEXT,
            interface TEXT,
            subnet TEXT,
            first_seen INTEGER,
            last_seen INTEGER,
            flag_set_time INTEGER,
            flag_acknowledged INTEGER DEFAULT 0,
            connected_to_ap TEXT,
            ap_name TEXT,
            ap_last_seen INTEGER,
            notes TEXT,
            created_at INTEGER,
            updated_at INTEGER
        )
    ''')

    # Ensure history can store mac before inserts during migration
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='device_history'")
    if cur.fetchone():
        cur.execute("PRAGMA table_info(device_history)")
        hcols = {r[1] for r in cur.fetchall()}
        if "mac" not in hcols:
            cur.execute("ALTER TABLE device_history ADD COLUMN mac TEXT")
    else:
        cur.execute('''
            CREATE TABLE device_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mac TEXT,
                ip TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                field_name TEXT,
                old_value TEXT,
                new_value TEXT,
                details TEXT
            )
        ''')

    cur.execute("SELECT * FROM devices_ip_legacy")
    legacy_rows = [dict(r) for r in cur.fetchall()]
    groups: Dict[str, List[Dict]] = {}
    ip_to_key: Dict[str, str] = {}
    for row in legacy_rows:
        key = device_key(row.get("mac") or "", row.get("ip") or "")
        if not key:
            continue
        groups.setdefault(key, []).append(row)
        if row.get("ip"):
            ip_to_key[row["ip"]] = key

    now = int(time.time())
    for key, group in groups.items():
        m = _merge_device_rows(group)
        cur.execute('''
            INSERT OR REPLACE INTO devices (
                mac, ip, hostname, hostname_override, vendor,
                connection_state, lifecycle_flags, status, dhcp_type,
                device_type, device_type_source, device_category, tags,
                discovered_manufacturer, discovered_model, discovered_os,
                manufacturer, model, os, os_version,
                exhaustive_ports, exhaustive_ports_time,
                mdns_services, open_ports, banners,
                snmp_sysname, snmp_sysdescr, interface, subnet,
                first_seen, last_seen, flag_set_time, flag_acknowledged,
                connected_to_ap, ap_name, ap_last_seen, notes,
                created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            key, m.get("ip") or "", m.get("hostname") or "", int(m.get("hostname_override") or 0),
            m.get("vendor") or "", m.get("connection_state") or "online", m.get("lifecycle_flags") or "",
            m.get("status") or "", m.get("dhcp_type") or "unknown", m.get("device_type") or "",
            m.get("device_type_source") or "", m.get("device_category") or "", m.get("tags") or "[]",
            m.get("discovered_manufacturer") or "", m.get("discovered_model") or "", m.get("discovered_os") or "",
            m.get("manufacturer") or "", m.get("model") or "", m.get("os") or "", m.get("os_version") or "",
            m.get("exhaustive_ports") or "", m.get("exhaustive_ports_time"),
            m.get("mdns_services") or "[]", m.get("open_ports") or "[]", m.get("banners") or "{}",
            m.get("snmp_sysname") or "", m.get("snmp_sysdescr") or "", m.get("interface") or "",
            m.get("subnet") or "", int(m.get("first_seen") or now), int(m.get("last_seen") or now),
            m.get("flag_set_time"), int(m.get("flag_acknowledged") or 0),
            m.get("connected_to_ap") or "", m.get("ap_name") or "", m.get("ap_last_seen") or 0,
            m.get("notes") or "", m.get("created_at") or now, now
        ))
        current_ip = m.get("ip") or ""
        for r in group:
            old_ip = r.get("ip") or ""
            if old_ip and old_ip != current_ip:
                cur.execute('''
                    INSERT INTO device_history (mac, ip, timestamp, event_type, field_name, old_value, new_value, details)
                    VALUES (?, ?, ?, 'attribute_change', 'ip', ?, ?, ?)
                ''', (key, current_ip, now, old_ip, current_ip,
                      json.dumps({"reason": "mac_pk_migration_dedupe"})))

    cur.execute("DROP TABLE devices_ip_legacy")

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='device_overrides'")
    if cur.fetchone():
        if not _override_pk_is_mac(cur):
            cur.execute("ALTER TABLE device_overrides RENAME TO device_overrides_ip_legacy")
            cur.execute('''
                CREATE TABLE device_overrides (
                    mac TEXT PRIMARY KEY,
                    ip TEXT,
                    hostname TEXT,
                    device_type TEXT,
                    manufacturer TEXT,
                    model TEXT,
                    os TEXT,
                    location TEXT,
                    tags TEXT,
                    notes TEXT,
                    created_at INTEGER,
                    updated_at INTEGER
                )
            ''')
            cur.execute("SELECT * FROM device_overrides_ip_legacy")
            for row in cur.fetchall():
                rd = dict(row)
                ip = rd.get("ip") or ""
                key = ip_to_key.get(ip) or device_key("", ip)
                if not key:
                    continue
                cur.execute('''
                    INSERT OR REPLACE INTO device_overrides
                    (mac, ip, hostname, device_type, manufacturer, model, os, location, tags, notes, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    key, ip, rd.get("hostname"), rd.get("device_type"), rd.get("manufacturer"),
                    rd.get("model"), rd.get("os"), rd.get("location"), rd.get("tags"), rd.get("notes"),
                    rd.get("created_at") or now, now
                ))
            cur.execute("DROP TABLE device_overrides_ip_legacy")

    for ip, key in ip_to_key.items():
        cur.execute("UPDATE device_history SET mac = ? WHERE (mac IS NULL OR mac = '') AND ip = ?", (key, ip))

    cur.execute("CREATE INDEX IF NOT EXISTS idx_devices_ip ON devices(ip)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON devices(last_seen)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_history_mac ON device_history(mac, timestamp DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_overrides_ip ON device_overrides(ip)")

    cur.execute("DROP VIEW IF EXISTS devices_with_overrides")
    cur.execute('''
        CREATE VIEW devices_with_overrides AS
        SELECT d.*, o.hostname AS override_hostname, o.device_type AS override_device_type,
               o.tags AS override_tags, o.notes AS override_notes,
               CASE WHEN o.mac IS NOT NULL THEN 1 ELSE 0 END AS has_override
        FROM devices d
        LEFT JOIN device_overrides o ON d.mac = o.mac
    ''')

    _clear_stale_new_flags(cur, now)

    log_error(f"MAC primary-key migration complete: {len(groups)} devices from {len(legacy_rows)} IP rows")
    return True

def _clear_stale_new_flags(cur, now: Optional[int] = None) -> int:
    """Remove lifecycle 'new' from devices first seen more than 48 hours ago."""
    now = int(now or time.time())
    cutoff = now - 172800
    cleared = 0
    try:
        cur.execute('''
            SELECT mac, lifecycle_flags, connection_state, first_seen FROM devices
            WHERE first_seen IS NOT NULL AND first_seen > 0 AND first_seen < ?
              AND lifecycle_flags IS NOT NULL AND lifecycle_flags != ''
        ''', (cutoff,))
        rows = cur.fetchall()
        for row in rows:
            mac, flags_s, conn, _fs = row[0], row[1], row[2], row[3]
            flags = [f.strip() for f in (flags_s or "").split(",") if f.strip()]
            if "new" not in flags:
                continue
            flags = [f for f in flags if f != "new"]
            conn = conn or "online"
            new_flags = ",".join(flags)
            new_status = (new_flags + ", " + conn) if new_flags else conn
            cur.execute(
                'UPDATE devices SET lifecycle_flags = ?, status = ? WHERE mac = ?',
                (new_flags, new_status, mac)
            )
            cleared += 1
    except Exception as e:
        log_error(f"clear stale new flags failed: {e}")
    return cleared


def init_sqlite_db():
    """Initialize SQLite database with schema; migrate IP-keyed DBs to MAC PK."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='devices'")
    table_exists = cur.fetchone() is not None

    if table_exists and not _devices_pk_is_mac(cur):
        migrate_devices_to_mac_pk(conn)
    else:
        schema_path = "/usr/local/opnsense/scripts/NetDiscover/db_schema.sql"
        if os.path.exists(schema_path):
            with open(schema_path, "r", encoding="utf-8") as f:
                conn.executescript(f.read())
        else:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS devices (
                    mac TEXT PRIMARY KEY,
                    ip TEXT,
                    hostname TEXT,
                    hostname_override INTEGER DEFAULT 0,
                    vendor TEXT,
                    connection_state TEXT DEFAULT 'online',
                    lifecycle_flags TEXT,
                    status TEXT,
                    dhcp_type TEXT,
                    device_type TEXT,
                    device_type_source TEXT,
                    device_category TEXT,
                    tags TEXT,
                    manufacturer TEXT,
                    model TEXT,
                    os TEXT,
                    mdns_services TEXT,
                    open_ports TEXT,
                    banners TEXT,
                    snmp_sysname TEXT,
                    snmp_sysdescr TEXT,
                    interface TEXT,
                    subnet TEXT,
                    first_seen INTEGER,
                    last_seen INTEGER,
                    flag_set_time INTEGER,
                    flag_acknowledged INTEGER DEFAULT 0,
                    connected_to_ap TEXT,
                    ap_name TEXT,
                    ap_last_seen INTEGER,
                    notes TEXT,
                    updated_at INTEGER
                )
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS device_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mac TEXT,
                    ip TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    field_name TEXT,
                    old_value TEXT,
                    new_value TEXT,
                    details TEXT
                )
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    ip TEXT NOT NULL,
                    mac TEXT,
                    hostname TEXT,
                    details TEXT
                )
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS device_overrides (
                    mac TEXT PRIMARY KEY,
                    ip TEXT,
                    hostname TEXT,
                    device_type TEXT,
                    manufacturer TEXT,
                    model TEXT,
                    os TEXT,
                    location TEXT,
                    tags TEXT,
                    notes TEXT,
                    created_at INTEGER,
                    updated_at INTEGER
                )
            ''')

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='devices'")
    if cur.fetchone():
        cur.execute("PRAGMA table_info(devices)")
        existing_cols = {row[1] for row in cur.fetchall()}
        for col, decl in [
            ("device_type_source", "TEXT"),
            ("os", "TEXT"),
            ("banners", "TEXT"),
            ("connection_state", "TEXT DEFAULT 'online'"),
            ("lifecycle_flags", "TEXT"),
            ("flag_set_time", "INTEGER"),
            ("flag_acknowledged", "INTEGER DEFAULT 0"),
            ("dhcp_type", "TEXT DEFAULT 'unknown'"),
            ("discovered_manufacturer", "TEXT"),
            ("discovered_model", "TEXT"),
            ("discovered_os", "TEXT"),
            ("os_version", "TEXT"),
            ("device_category", "TEXT"),
            ("exhaustive_ports", "TEXT"),
            ("exhaustive_ports_time", "INTEGER"),
            ("connected_to_ap", "TEXT"),
            ("ap_name", "TEXT"),
            ("ap_last_seen", "INTEGER"),
            ("hostname_override", "INTEGER DEFAULT 0"),
            ("notes", "TEXT"),
            ("created_at", "INTEGER"),
        ]:
            if col not in existing_cols:
                cur.execute(f"ALTER TABLE devices ADD COLUMN {col} {decl}")

        cur.execute("PRAGMA table_info(device_history)")
        hcols = {row[1] for row in cur.fetchall()}
        if "mac" not in hcols:
            cur.execute("ALTER TABLE device_history ADD COLUMN mac TEXT")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_devices_ip ON devices(ip)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON devices(last_seen)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_history_ip ON device_history(ip, timestamp DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_history_mac ON device_history(mac, timestamp DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp DESC)")

    # Always scrub stale "new" flags left over from migration / old IP clones
    try:
        n = _clear_stale_new_flags(cur)
        if n:
            log_error(f"Cleared stale 'new' flags on {n} devices")
    except Exception:
        pass

    conn.commit()
    conn.close()

def write_to_sqlite(devices: List[Dict], events: List[Dict]):
    """Write current device state and events to SQLite (keyed by MAC)."""
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10.0)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute('''
            SELECT mac, ip, hostname, status, vendor, connection_state, lifecycle_flags,
                   flag_acknowledged, flag_set_time, first_seen
            FROM devices
        ''')
        existing = {}
        for row in cur.fetchall():
            rd = dict(row)
            key = rd.get("mac") or device_key("", rd.get("ip") or "")
            if key:
                existing[key] = rd
    except Exception as e:
        log_error(f"SQLite connection failed: {e}")
        raise

    devices_written = 0
    now = int(time.time())
    for dev in devices:
        ip = dev.get("ip") or ""
        key = device_key(dev.get("mac") or "", ip)
        if not key:
            continue

        try:
            old_dev = existing.get(key)

            if old_dev:
                if old_dev.get("status") != dev.get("status"):
                    cur.execute('''
                        INSERT INTO device_history (mac, ip, timestamp, event_type, field_name, old_value, new_value)
                        VALUES (?, ?, ?, 'status_change', 'status', ?, ?)
                    ''', (key, ip, now, old_dev.get("status", ""), dev.get("status", "")))
                if old_dev.get("hostname") != dev.get("hostname"):
                    cur.execute('''
                        INSERT INTO device_history (mac, ip, timestamp, event_type, field_name, old_value, new_value)
                        VALUES (?, ?, ?, 'attribute_change', 'hostname', ?, ?)
                    ''', (key, ip, now, old_dev.get("hostname", ""), dev.get("hostname", "")))
                if old_dev.get("ip") and ip and old_dev.get("ip") != ip:
                    cur.execute('''
                        INSERT INTO device_history (mac, ip, timestamp, event_type, field_name, old_value, new_value)
                        VALUES (?, ?, ?, 'attribute_change', 'ip', ?, ?)
                    ''', (key, ip, now, old_dev.get("ip", ""), ip))

            flag_ack = dev.get("flag_acknowledged", 0)
            if old_dev and old_dev.get("flag_acknowledged"):
                flag_ack = 1

            first_seen = int(dev.get("first_seen", now))
            if old_dev and old_dev.get("first_seen"):
                first_seen = min(first_seen, int(old_dev["first_seen"]))

            cur.execute('''
                INSERT INTO devices (
                    mac, ip, hostname, vendor,
                    connection_state, lifecycle_flags, status, dhcp_type,
                    device_type, device_type_source, device_category, tags, manufacturer, model, os,
                    mdns_services, open_ports, banners, snmp_sysname, snmp_sysdescr,
                    interface, subnet, first_seen, last_seen,
                    flag_set_time, flag_acknowledged, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(mac) DO UPDATE SET
                    ip=excluded.ip,
                    hostname=excluded.hostname,
                    vendor=excluded.vendor,
                    connection_state=excluded.connection_state,
                    lifecycle_flags=excluded.lifecycle_flags,
                    status=excluded.status,
                    dhcp_type=excluded.dhcp_type,
                    device_type=excluded.device_type,
                    device_type_source=excluded.device_type_source,
                    device_category=excluded.device_category,
                    tags=excluded.tags,
                    manufacturer=excluded.manufacturer,
                    model=excluded.model,
                    os=excluded.os,
                    mdns_services=excluded.mdns_services,
                    open_ports=excluded.open_ports,
                    banners=excluded.banners,
                    snmp_sysname=excluded.snmp_sysname,
                    snmp_sysdescr=excluded.snmp_sysdescr,
                    interface=excluded.interface,
                    subnet=excluded.subnet,
                    last_seen=excluded.last_seen,
                    flag_set_time=excluded.flag_set_time,
                    updated_at=excluded.updated_at
            ''', (
                key,
                ip,
                dev.get("hostname", ""),
                dev.get("vendor", ""),
                dev.get("connection_state", "online"),
                dev.get("lifecycle_flags", ""),
                dev.get("status", ""),
                dev.get("dhcp_type", "unknown"),
                dev.get("device_type", ""),
                dev.get("device_type_source", ""),
                dev.get("device_category", ""),
                json.dumps(dev.get("tags", [])),
                dev.get("manufacturer", ""),
                dev.get("model", ""),
                dev.get("os", ""),
                json.dumps(dev.get("mdns_services", [])),
                json.dumps(dev.get("open_ports", [])),
                json.dumps(dev.get("banners", {})),
                dev.get("snmp_sysname", ""),
                dev.get("snmp_sysdescr", ""),
                dev.get("interface", ""),
                dev.get("subnet", ""),
                first_seen,
                int(dev.get("last_seen", now)),
                int(dev.get("flag_set_time", now)),
                flag_ack,
                now,
            ))
            devices_written += 1
        except Exception as e:
            log_error(f"Error writing device {key}: {e}")
            continue

    events_written = 0
    try:
        cur.execute("DELETE FROM events WHERE id NOT IN (SELECT id FROM events ORDER BY timestamp DESC LIMIT 1000)")
        # Collapse rows already duplicated by older builds that re-inserted the ring buffer
        cur.execute('''
            DELETE FROM events WHERE id NOT IN (
                SELECT MIN(id) FROM events
                GROUP BY timestamp, event_type, IFNULL(ip,''), IFNULL(mac,''), IFNULL(hostname,''), IFNULL(details,'')
            )
        ''')
        for evt in events[:100]:
            if evt.get("_persisted"):
                continue
            try:
                # Store real MAC only in events; keep synthetic ip: keys out of the MAC column
                emac = normalize_mac(evt.get("mac") or "")
                if not emac:
                    emac = ""
                cur.execute('''
                    INSERT INTO events (timestamp, event_type, ip, mac, hostname, details)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    int(evt.get("time", time.time())),
                    evt.get("type", ""),
                    evt.get("ip", ""),
                    emac,
                    evt.get("hostname", ""),
                    json.dumps(evt.get("details", {})),
                ))
                evt["_persisted"] = True
                events_written += 1
            except Exception as e:
                log_error(f"Error writing event: {e}")
                continue
    except Exception as e:
        log_error(f"Error managing events table: {e}")

    try:
        conn.commit()
    except Exception as e:
        log_error(f"SQLite commit failed: {e}")
        raise
    finally:
        conn.close()

    if devices_written > 0:
        log_error(f"SQLite: wrote {devices_written} devices, {events_written} events")


def load_oui_from_sqlite() -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Load OUI mappings and model hints from separate OUI SQLite database.
    Returns: (vendor_map, model_hints_map)
    v1.6.10: Now also loads model hints
    """
    vendor_map: Dict[str, str] = {}
    model_map: Dict[str, str] = {}
    
    if not os.path.exists(OUI_DB_FILE):
        return vendor_map, model_map
    
    try:
        conn = sqlite3.connect(OUI_DB_FILE)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Load vendors
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='oui'")
        if cur.fetchone():
            cur.execute('SELECT oui, vendor FROM oui')
            for row in cur.fetchall():
                vendor_map[row['oui']] = row['vendor']
        
        # Load model hints (v1.6.10)
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='oui_models'")
        if cur.fetchone():
            cur.execute('SELECT oui, model_hint FROM oui_models')
            for row in cur.fetchall():
                model_map[row['oui']] = row['model_hint']
        
        conn.close()
        return vendor_map, model_map
    except Exception:
        return vendor_map, model_map

def load_oui(path: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Load OUI mappings (try SQLite first, then CSV fallback).
    Returns: (vendor_map, model_hints_map)
    v1.6.10: Now returns tuple
    """
    # Try SQLite first
    vendor_map, model_map = load_oui_from_sqlite()
    if vendor_map:
        return vendor_map, model_map
    
    # Fallback to CSV file if provided (no model hints from CSV)
    vendor_map = {}
    if path and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = [p.strip() for p in line.split(",", 1)]
                    if len(parts) != 2:
                        continue
                    oui = parts[0].upper().replace("-", ":")
                    if re.fullmatch(r"([0-9A-F]{2}:){2}[0-9A-F]{2}", oui):
                        vendor_map[oui] = parts[1]
        except Exception:
            pass
    
    return vendor_map, {}

def mac_oui(mac: str) -> str:
    mac = mac.upper().replace("-", ":")
    m = re.match(r"^([0-9A-F]{2}):([0-9A-F]{2}):([0-9A-F]{2})", mac)
    if not m:
        return ""
    return f"{m.group(1)}:{m.group(2)}:{m.group(3)}"

def ifconfig_inet() -> Dict[str, List[Tuple[str, int]]]:
    out = run("ifconfig -a")
    iface = None
    res: Dict[str, List[Tuple[str, int]]] = {}
    for line in out.splitlines():
        if re.match(r"^[a-zA-Z0-9_.:-]+: flags=", line):
            iface = line.split(":", 1)[0]
            res.setdefault(iface, [])
            continue
        if iface is None:
            continue
        m = re.search(r"\binet\s+(\d+\.\d+\.\d+\.\d+)\s+netmask\s+(0x[0-9a-fA-F]+)", line)
        if m:
            ip = m.group(1)
            netmask_hex = int(m.group(2), 16)
            prefix = bin(netmask_hex).count("1")
            res[iface].append((ip, prefix))
    return {k: v for k, v in res.items() if v}

def iface_primary_ipv4() -> Dict[str, str]:
    inet = ifconfig_inet()
    out: Dict[str, str] = {}
    for iface, addrs in inet.items():
        if addrs:
            out[iface] = addrs[0][0]
    return out

def iface_subnets(interfaces_filter: Optional[Set[str]] = None) -> List[Tuple[str, str]]:
    inet = ifconfig_inet()
    subnets: List[Tuple[str, str]] = []
    for iface, addrs in inet.items():
        if interfaces_filter and iface not in interfaces_filter:
            continue
        for ip, prefix in addrs:
            try:
                net = ip_network(f"{ip}/{prefix}", strict=False)
            except Exception:
                continue
            if net.prefixlen >= 31:
                continue
            subnets.append((iface, str(net)))
    return subnets

def parse_arp() -> Dict[str, Tuple[str, str]]:
    out = run("arp -an")
    res: Dict[str, Tuple[str, str]] = {}
    for line in out.splitlines():
        m = re.search(r"\((\d+\.\d+\.\d+\.\d+)\)\s+at\s+([0-9a-fA-F:.-]+)\s+on\s+(\S+)", line)
        if not m:
            continue
        ip, mac, iface = m.group(1), m.group(2), m.group(3)
        if mac.lower() == "(incomplete)":
            continue
        res[ip] = (mac.lower().replace("-", ":"), iface)
    return res

def parse_dnsmasq_leases() -> Dict[str, Tuple[str, str]]:
    candidates = [
        "/var/db/dnsmasq.leases",
        "/var/dnsmasq/var/db/dnsmasq.leases",
        "/var/db/dnsmasq/dnsmasq.leases",
    ]
    res: Dict[str, Tuple[str, str]] = {}
    for path in candidates:
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split()
                    if len(parts) < 4:
                        continue
                    if not re.match(r"^\d+$", parts[0]):
                        continue
                    mac = parts[1].lower().replace("-", ":")
                    ip = parts[2]
                    hn = parts[3] if parts[3] != "*" else ""
                    if re.match(r"^\d+\.\d+\.\d+\.\d+$", ip):
                        res[ip] = (mac, hn)
        except Exception:
            pass
    return res

def reverse_dns(ip: str, timeout_sec: float = 0.25) -> str:
    try:
        socket.setdefaulttimeout(timeout_sec)
        name, _aliases, _ips = socket.gethostbyaddr(ip)
        return name.rstrip(".")
    except Exception:
        return ""

def ping_sweep(subnet: str, max_hosts: int, rate_limit_ms: int):
    try:
        net = ip_network(subnet, strict=False)
    except Exception:
        return
    if net.version != 4:
        return
    if net.num_addresses > max_hosts:
        return
    for ip in net.hosts():
        run(f"ping -c 1 -t 1 -q {shlex.quote(str(ip))}", timeout=2)
        if rate_limit_ms:
            time.sleep(rate_limit_ms / 1000.0)

def tag_subnet(ip_str: str, nets: List[Tuple[str, object]]) -> Tuple[str, str]:
    try:
        ip_obj = ip_address(ip_str)
    except Exception:
        return ("", "")
    for ifn, net in nets:
        if net.version == 4 and ip_obj.version == 4 and ip_obj in net:
            return (ifn, str(net))
    return ("", "")

def parse_http_headers(payload: str) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    for line in payload.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip().lower()] = v.strip()
    return headers

def join_multicast(sock: socket.socket, mcast_ip: str, iface_ip: str):
    mreq = socket.inet_aton(mcast_ip) + socket.inet_aton(iface_ip)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

def udp_listener(stop_evt: threading.Event, bind_port: int, mcast: Optional[Tuple[str,int]], iface_ip: str, on_msg):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("", bind_port))
        except OSError:
            sock.bind((iface_ip, bind_port))
        if mcast is not None:
            join_multicast(sock, mcast[0], iface_ip)
        sock.settimeout(0.5)
    except Exception:
        return
    while not stop_evt.is_set():
        try:
            data, addr = sock.recvfrom(BUF)
            on_msg(data, addr[0])
        except socket.timeout:
            continue
        except Exception:
            break
    try:
        sock.close()
    except Exception:
        pass

def fetch_upnp_xml(location: str, timeout_sec: float = 0.7) -> Dict[str, str]:
    try:
        req = urllib.request.Request(location, headers={"User-Agent": "NetDiscover/0.5.0"})
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read(128 * 1024)
        root = ET.fromstring(raw)

        def find_text(suffix: str) -> str:
            for el in root.iter():
                if el.tag.lower().endswith(suffix.lower()) and (el.text or "").strip():
                    return (el.text or "").strip()
            return ""

        return {
            "friendlyName": find_text("friendlyName"),
            "manufacturer": find_text("manufacturer"),
            "modelName": find_text("modelName"),
            "deviceType": find_text("deviceType"),
        }
    except Exception:
        return {}

def tcp_probe(ip: str, ports: List[int], timeout_ms: int):
    open_ports: List[int] = []
    banners: Dict[str, str] = {}
    timeout = max(0.05, timeout_ms / 1000.0)

    for port in ports:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            r = s.connect_ex((ip, port))
            if r == 0:
                open_ports.append(port)
                
                # Banner grabbing for identification
                try:
                    if port == 22:  # SSH
                        b = s.recv(128)
                        if b:
                            banners[str(port)] = b.decode("utf-8", errors="ignore").strip()[:200]
                    elif port in [80, 443, 8080, 8443]:  # HTTP/HTTPS
                        s.sendall(b"HEAD / HTTP/1.0\r\nHost: " + ip.encode() + b"\r\n\r\n")
                        b = s.recv(512)
                        if b:
                            # Extract Server header
                            response = b.decode("utf-8", errors="ignore")
                            for line in response.splitlines():
                                if line.lower().startswith('server:'):
                                    banners[str(port)] = line[7:].strip()[:200]
                                    break
                            if str(port) not in banners:
                                banners[str(port)] = response.splitlines()[0][:120]
                    elif port == 21:  # FTP
                        b = s.recv(256)
                        if b:
                            banners[str(port)] = b.decode("utf-8", errors="ignore").strip()[:200]
                    elif port == 23:  # Telnet
                        b = s.recv(256)
                        if b:
                            banners[str(port)] = b.decode("utf-8", errors="ignore").strip()[:200]
                    elif port == 25:  # SMTP
                        b = s.recv(256)
                        if b:
                            banners[str(port)] = b.decode("utf-8", errors="ignore").strip()[:200]
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            try:
                s.close()
            except Exception:
                pass

    return sorted(list(set(open_ports))), banners

# ---- DNS name decoding (mDNS/LLMNR) ----
def dns_read_name(data: bytes, offset: int):
    labels = []
    jumped = False
    orig = offset
    while True:
        if offset >= len(data):
            return ("", offset)
        length = data[offset]
        if length == 0:
            offset += 1
            break
        if (length & 0xC0) == 0xC0:
            if offset + 1 >= len(data):
                break
            ptr = ((length & 0x3F) << 8) | data[offset + 1]
            if not jumped:
                orig = offset + 2
                jumped = True
            offset = ptr
            continue
        offset += 1
        if offset + length > len(data):
            break
        label = data[offset:offset + length]
        labels.append(label.decode("utf-8", errors="ignore"))
        offset += length
    name = ".".join([l for l in labels if l])
    return (name, (orig if jumped else offset))

def mdns_extract_services(pkt: bytes) -> List[str]:
    if len(pkt) < 12:
        return []
    try:
        _id, _flags, qd, an, ns, ar = struct.unpack("!HHHHHH", pkt[:12])
    except Exception:
        return []
    off = 12
    services = set()
    for _ in range(qd):
        name, off = dns_read_name(pkt, off)
        if off + 4 > len(pkt):
            return sorted(list(services))
        off += 4
        parts = name.split(".")
        if len(parts) >= 3 and parts[1] in ("_tcp", "_udp"):
            services.add(".".join(parts[:3]))
    rr_total = an + ns + ar
    for _ in range(rr_total):
        name, off = dns_read_name(pkt, off)
        if off + 10 > len(pkt):
            break
        rtype, _rclass, _ttl, rdlen = struct.unpack("!HHIH", pkt[off:off + 10])
        off += 10
        rstart = off
        off += rdlen
        if rstart + rdlen > len(pkt):
            break
        if rtype == 12:  # PTR
            ptr_name, _ = dns_read_name(pkt, rstart)
            parts = ptr_name.split(".")
            if len(parts) >= 3 and parts[1] in ("_tcp", "_udp"):
                services.add(".".join(parts[:3]))
        else:
            parts = name.split(".")
            if len(parts) >= 3 and parts[1] in ("_tcp", "_udp"):
                services.add(".".join(parts[:3]))
    return sorted(list(services))

def llmnr_extract_hostname(pkt: bytes) -> str:
    # Heuristic: if response contains A/AAAA records, return the queried name (without .local)
    if len(pkt) < 12:
        return ""
    try:
        _id, flags, qd, an, ns, ar = struct.unpack("!HHHHHH", pkt[:12])
    except Exception:
        return ""
    # response bit set?
    if (flags & 0x8000) == 0:
        return ""
    off = 12
    qname = ""
    for _ in range(qd):
        qname, off = dns_read_name(pkt, off)
        if off + 4 > len(pkt):
            return ""
        off += 4
    # if it looks like "HOST.local" or "HOST", return first label
    if not qname:
        return ""
    host = qname.split(".")[0]
    if host and len(host) <= 63 and re.fullmatch(r"[A-Za-z0-9_-]+", host):
        return host
    return ""

# ---- NBNS decoding (UDP/137) ----
def nbns_decode_name(encoded32: bytes) -> str:
    # NetBIOS name encoding: 32 bytes, each nibble encoded as 'A'..'P'
    if len(encoded32) < 32:
        return ""
    out = bytearray()
    try:
        for i in range(0, 32, 2):
            c1 = encoded32[i] - 0x41
            c2 = encoded32[i+1] - 0x41
            if not (0 <= c1 <= 15 and 0 <= c2 <= 15):
                return ""
            out.append((c1 << 4) | c2)
        name = out[:15].decode("ascii", errors="ignore").rstrip()
        name = name.strip()
        # ignore wildcard/empty
        if name and name != "*":
            return name
    except Exception:
        return ""
    return ""

def nbns_extract_hostname(pkt: bytes) -> str:
    # Minimal NBNS parser: decode first question name
    if len(pkt) < 12:
        return ""
    try:
        _tid, _flags, qd, _an, _ns, _ar = struct.unpack("!HHHHHH", pkt[:12])
    except Exception:
        return ""
    off = 12
    if qd < 1:
        return ""
    # name format: 1 byte len (should be 0x20), 32 bytes encoded, 1 byte 0x00, then type/class
    if off >= len(pkt):
        return ""
    if pkt[off] != 0x20:
        return ""
    off += 1
    if off + 32 > len(pkt):
        return ""
    enc = pkt[off:off+32]
    off += 32
    if off >= len(pkt) or pkt[off] != 0x00:
        return ""
    # skip 0x00
    name = nbns_decode_name(enc)
    return name

def ports_from_csv(s: str) -> List[int]:
    out: List[int] = []
    for part in (s or "").split(","):
        part = part.strip()
        if not part:
            continue
        if re.fullmatch(r"\d+", part):
            p = int(part)
            if 1 <= p <= 65535:
                out.append(p)
    seen = set()
    dedup = []
    for p in out:
        if p not in seen:
            seen.add(p)
            dedup.append(p)
    return dedup

def make_event(ev_type: str, now: int, ip: str, mac: str, hostname: str, details: Optional[dict] = None) -> dict:
    ev = {"time": now, "type": ev_type, "ip": ip or "", "mac": mac or "", "hostname": hostname or ""}
    if details:
        ev["details"] = details
    return ev

def merge(devs: Dict[str, Dict], now: int, ip: str, mac: str, hostname: str,
          iface: str, subnet: str, vendor_map: Dict[str, str], model_hints: Dict[str, str], src: str, up: bool):
    mac_n = normalize_mac(mac)
    key = device_key(mac_n, ip)
    rec = devs.get(key)
    changed_fields = []

    if rec is None:
        rec = {
            "ip": ip,
            "mac": mac_n,
            "hostname": hostname or "",
            "vendor": "",
            "first_seen": now,
            "last_seen": now,
            "state": "UP" if up else "UNKNOWN",
            "source": [],
            "interface": iface or "",
            "subnet": subnet or "",
            "device_type": "",
            "manufacturer": "",
            "model": "",
            "mdns_services": [],
            "open_ports": [],
            "banners": {},
            "snmp_sysname": "",
            "snmp_sysdescr": "",
            # Dual-state system (v1.5.0)
            "connection_state": "online" if up else "offline",
            "lifecycle_flags": "new",  # New device gets "new" flag
            "status": "new, online" if up else "new, offline",  # Display string
            "flag_set_time": now,
            "flag_acknowledged": 0,
            "last_change": now,
            "change_fields": [],
        }
    else:
        if ip and ip != rec.get("ip"):
            rec["ip"] = ip
            changed_fields.append("ip")
        if hostname and hostname != rec.get("hostname"):
            # prefer DHCP hostname if present; but allow overwrite from LLMNR/NBNS if empty
            if not rec.get("hostname") or src in ("llmnr", "nbns"):
                rec["hostname"] = hostname
                changed_fields.append("hostname")
        if iface and iface != rec.get("interface"):
            rec["interface"] = iface
        if subnet and subnet != rec.get("subnet"):
            rec["subnet"] = subnet
        if mac_n and not rec.get("mac"):
            rec["mac"] = mac_n

    rec["last_seen"] = now
    rec["state"] = "UP" if up else rec.get("state", "UNKNOWN")

    if src and src not in rec.get("source", []):
        rec.setdefault("source", []).append(src)

    # Set vendor from OUI lookup
    if rec.get("mac") and not rec.get("vendor") and not str(rec.get("mac")).startswith("ip:"):
        vend = vendor_map.get(mac_oui(rec["mac"]))
        if vend:
            rec["vendor"] = vend
            rec["discovered_manufacturer"] = vend  # v1.6.10: Track as discovered
    
    # Set model hint from OUI lookup (v1.6.10)
    if rec.get("mac") and not rec.get("discovered_model"):
        model_hint = model_hints.get(mac_oui(rec["mac"]))
        if model_hint:
            rec["discovered_model"] = model_hint
            if not rec.get("model"):  # Only set if not already set by SSDP/SNMP
                rec["model"] = model_hint
    
    # Apply pattern-based device identification (v1.3.0+)
    if HAS_PATTERNS and not rec.get("device_type"):
        # Try pattern matching if device_type not already set
        device_type = (
            guess_device_type_from_mdns(rec.get("mdns_services", [])) or
            guess_device_type_from_hostname(rec.get("hostname", "")) or
            guess_device_type_from_ports(rec.get("open_ports", []))
        )
        if device_type:
            rec["device_type"] = device_type
            rec["device_type_source"] = "pattern_match"
            if "device_type" not in changed_fields:
                changed_fields.append("device_type")
    
    # Set device category based on device_type (v2.0.9)
    if HAS_PATTERNS and rec.get("device_type") and not rec.get("device_category"):
        from device_patterns import get_device_category
        category = get_device_category(rec["device_type"])
        if category:
            rec["device_category"] = category

    # Auto-tagging rules (v2.1.0)
    if HAS_AUTO_TAGS:
        try:
            rec["tags"] = apply_auto_tags(rec)
        except Exception:
            pass

    return key, rec, changed_fields

def reconcile_ip_mac(devs: Dict[str, Dict], ip: str, mac: str) -> None:
    """If we have a temporary ip-key record (ip:<addr>) and later learn the MAC, merge and dedupe."""
    if not ip or not mac:
        return
    ip_key = f"ip:{ip}"
    mac_key = normalize_mac(mac)
    if not mac_key:
        return
    ip_rec = devs.get(ip_key)
    if ip_rec is None:
        return
    mac_rec = devs.get(mac_key)

    if mac_rec is None:
        ip_rec["mac"] = mac_key
        devs[mac_key] = ip_rec
        del devs[ip_key]
        return

    # Merge ip_rec fields into mac_rec (only if missing)
    for k in ["hostname","vendor","device_type","manufacturer","model","interface","subnet","snmp_sysname","snmp_sysdescr"]:
        if (not mac_rec.get(k)) and ip_rec.get(k):
            mac_rec[k] = ip_rec[k]

    # Merge arrays/lists
    for k in ["mdns_services","open_ports","source"]:
        a = mac_rec.get(k) or []
        b = ip_rec.get(k) or []
        if isinstance(a, list) and isinstance(b, list):
            mac_rec[k] = sorted(list(set(a).union(set(b))))

    mac_rec.setdefault("banners", {})
    if isinstance(ip_rec.get("banners"), dict):
        mac_rec["banners"].update(ip_rec["banners"])

    mac_rec["first_seen"] = min(int(mac_rec.get("first_seen", 0) or 0), int(ip_rec.get("first_seen", 0) or 0)) or mac_rec.get("first_seen", 0)
    mac_rec["last_seen"] = max(int(mac_rec.get("last_seen", 0) or 0), int(ip_rec.get("last_seen", 0) or 0))
    mac_rec["ip"] = ip
    mac_rec["mac"] = mac_key

    devs[mac_key] = mac_rec
    del devs[ip_key]


def find_record_key_for_ip(devs: Dict[str, Dict], ip: str) -> Optional[str]:
    if not ip:
        return None
    ip_key = f"ip:{ip}"
    if ip_key in devs:
        return ip_key
    for k, r in devs.items():
        if isinstance(r, dict) and r.get("ip") == ip:
            return k
    return None


def update_connection_state(rec: dict, now: int, seen_now: bool, scan_interval: int) -> str:
    """
    Determine connection state based on last_seen timing.
    Returns: online|offline|missing|gone
    v1.5.0: Dual-state system
    """
    last_seen = int(rec.get("last_seen", 0))
    time_since_seen = now - last_seen
    
    offline_threshold = scan_interval * 2  # 2 consecutive probe cycles
    
    if seen_now:
        return "online"
    
    # Not seen - check timing
    if time_since_seen >= GONE_THRESHOLD:
        return "gone"  # 60 days
    elif time_since_seen >= MISSING_THRESHOLD:
        return "missing"  # 30 days
    elif time_since_seen >= offline_threshold:
        return "offline"  # 2 scan cycles
    else:
        # Within 2 cycles, still consider online
        return rec.get("connection_state", "online")

def update_lifecycle_flags(rec: dict, now: int, old_connection_state: str, new_connection_state: str) -> List[str]:
    """
    Manage lifecycle flags (new, changed, back).
    Returns: list of active flags
    v1.5.0: Dual-state system
    """
    flags = []
    current_flags = (rec.get("lifecycle_flags", "") or "").split(",")
    current_flags = [f.strip() for f in current_flags if f.strip()]
    flag_set_time = int(rec.get("flag_set_time", 0))
    flag_acknowledged = rec.get("flag_acknowledged", 0)
    first_seen = int(rec.get("first_seen", now))
    
    # Check if flags should expire (24h or acknowledged)
    flags_age = now - flag_set_time if flag_set_time > 0 else 0
    flags_expired = flag_acknowledged or flags_age >= FLAG_EXPIRY
    
    # "new" flag
    device_age = now - first_seen if first_seen > 0 else 0
    if device_age < FLAG_EXPIRY and not flag_acknowledged:
        if "new" in current_flags or device_age < 60:  # Keep new flag
            flags.append("new")
    
    # "changed" flag (set externally by mark_changed)
    if "changed" in current_flags and not flags_expired:
        flags.append("changed")
    
    # "back" flag - set when transitioning to online from offline/missing/gone
    if old_connection_state in ["offline", "missing", "gone"] and new_connection_state == "online":
        flags.append("back")
        rec["flag_set_time"] = now  # Reset timer
    elif "back" in current_flags and not flags_expired:
        flags.append("back")
    
    return flags

def prune(devs: Dict[str, Dict]) -> Dict[str, Dict]:
    """
    v1.5.0: NO AUTO-PRUNE
    Keep all devices regardless of age. User must manually delete.
    Return all devices unchanged.
    """
    return devs

def snmp_enrich(ip: str, communities: List[str], timeout_ms: int) -> Tuple[str, str]:
    # Uses snmpget if available. Returns (sysName, sysDescr) possibly empty.
    snmpget = which("snmpget")
    if not snmpget:
        return ("", "")
    tsec = max(0.1, timeout_ms / 1000.0)
    for comm in communities:
        comm = comm.strip()
        if not comm:
            continue
        cmd = f"{shlex.quote(snmpget)} -v2c -c {shlex.quote(comm)} -t {tsec} -r 0 {shlex.quote(ip)} sysName.0 sysDescr.0"
        out = run(cmd, timeout=int(tsec) + 1)
        if not out:
            continue
        sysname = ""
        sysdescr = ""
        for line in out.splitlines():
            # examples: SNMPv2-MIB::sysName.0 = STRING: MyHost
            if "sysName.0" in line:
                m = re.search(r"=\s+\w+:\s+(.*)$", line)
                if m: sysname = m.group(1).strip().strip('"')
            if "sysDescr.0" in line:
                m = re.search(r"=\s+\w+:\s+(.*)$", line)
                if m: sysdescr = m.group(1).strip().strip('"')
        if sysname or sysdescr:
            return (sysname[:120], sysdescr[:240])
    return ("", "")

def main():
    try:
        with open(STARTUP_LOG, "a") as f:
            f.write("  Parsing arguments...\n")
            f.flush()
    except: pass
    
    # Service starts are logged by rc.d - no need to duplicate
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=300)
    ap.add_argument("--active", action="store_true")
    ap.add_argument("--reverse-dns", action="store_true")
    ap.add_argument("--interfaces", default="")
    ap.add_argument("--max-hosts", type=int, default=4096)
    ap.add_argument("--rate-limit-ms", type=int, default=3)
    ap.add_argument("--ssdp", action="store_true")
    ap.add_argument("--ssdp-fetch-xml", action="store_true")
    ap.add_argument("--ssdp-xml-rate-limit", type=int, default=10)
    ap.add_argument("--mdns", action="store_true")
    ap.add_argument("--llmnr", action="store_true")
    ap.add_argument("--nbns", action="store_true")
    ap.add_argument("--tcp-probe", action="store_true")
    ap.add_argument("--tcp-ports", default="22,80,443,445,3389,9100")
    ap.add_argument("--tcp-timeout-ms", type=int, default=250)
    ap.add_argument("--snmp", action="store_true")
    ap.add_argument("--snmp-communities", default="public")
    ap.add_argument("--snmp-timeout-ms", type=int, default=400)
    ap.add_argument("--snmp-rate-limit", type=int, default=3600)
    ap.add_argument("--oui", default=DEFAULT_OUI, help="OUI file (deprecated, now uses SQLite)")
    ap.add_argument("--once", action="store_true")
    
    try:
        args = ap.parse_args()
    except Exception as e:
        with open(STARTUP_LOG, "a") as f:
            f.write(f"  ✗ ARGPARSE FAILED: {e}\n")
            f.write(f"  sys.argv = {sys.argv}\n")
            f.flush()
        raise

    try:
        with open(STARTUP_LOG, "a") as f:
            f.write("  Arguments parsed OK\n")
            f.write(f"  Interval: {args.interval}s\n")
            f.write("  Loading OUI database...\n")
            f.flush()
    except: pass

    # Treat blank / _LAN_ / all as "all interfaces" (v2.1.0)
    raw_ifaces = [x.strip() for x in (args.interfaces or "").split(",") if x.strip()]
    if not raw_ifaces or all(x.upper() in ("_LAN_", "LAN", "ALL", "*") for x in raw_ifaces):
        iface_filter = None
    else:
        iface_filter = set(raw_ifaces)
    vendor_map, model_hints = load_oui(DEFAULT_OUI)  # Reads from SQLite first, CSV fallback (v1.6.10)
    
    try:
        with open(STARTUP_LOG, "a") as f:
            f.write(f"  OUI loaded: {len(vendor_map)} vendors\n")
            f.write("  Parsing ports and communities...\n")
            f.flush()
    except: pass
    
    ports = ports_from_csv(args.tcp_ports)
    communities = [c.strip() for c in (args.snmp_communities or "").split(",") if c.strip()]

    try:
        with open(STARTUP_LOG, "a") as f:
            f.write("  Ensuring DB directory...\n")
            f.flush()
    except: pass
    
    ensure_db_dir()
    
    # Initialize SQLite database
    try:
        with open(STARTUP_LOG, "a") as f:
            f.write(f"  Initializing SQLite at {DB_FILE}...\n")
            f.flush()
        init_sqlite_db()
        log_error(f"NetDiscover v2.1.0 started - PID {os.getpid()}, interval {args.interval}s")
        with open(STARTUP_LOG, "a") as f:
            f.write(f"  ✓ SQLite initialized successfully\n")
            f.write(f"  ✓ Daemon ready - entering main loop\n")
            f.flush()
    except Exception as e:
        with open(STARTUP_LOG, "a") as f:
            f.write(f"  ✗ SQLite init FAILED: {e}\n")
            f.flush()
        log_error(f"SQLite init failed: {e}")
        sys.exit(1)

    # Rehydrate in-memory state from SQLite so offline→missing→gone continues across restarts
    devs: Dict[str, Dict] = {}
    events: List[dict] = []
    try:
        if os.path.exists(DB_FILE):
            rconn = sqlite3.connect(DB_FILE, timeout=5.0)
            rconn.row_factory = sqlite3.Row
            rcur = rconn.cursor()
            rcur.execute("SELECT * FROM devices")
            for row in rcur.fetchall():
                rd = dict(row)
                key = rd.get("mac") or device_key("", rd.get("ip") or "")
                if not key:
                    continue
                # Parse JSON columns when present as strings
                for jk in ("tags", "mdns_services", "open_ports", "exhaustive_ports"):
                    if isinstance(rd.get(jk), str) and rd[jk]:
                        try:
                            rd[jk] = json.loads(rd[jk])
                        except Exception:
                            rd[jk] = []
                if isinstance(rd.get("banners"), str) and rd["banners"]:
                    try:
                        rd["banners"] = json.loads(rd["banners"])
                    except Exception:
                        rd["banners"] = {}
                if str(rd.get("mac") or "").startswith("ip:"):
                    rd["mac"] = ""
                else:
                    rd["mac"] = normalize_mac(rd.get("mac") or "") or rd.get("mac") or ""
                devs[key] = rd
            rcur.execute("SELECT * FROM events ORDER BY timestamp DESC LIMIT 100")
            for row in rcur.fetchall():
                ev = dict(row)
                ev["time"] = ev.get("timestamp", 0)
                ev["type"] = ev.get("event_type", "")
                if isinstance(ev.get("details"), str):
                    try:
                        ev["details"] = json.loads(ev["details"] or "{}")
                    except Exception:
                        ev["details"] = {}
                ev["_persisted"] = True
                events.append(ev)
            rconn.close()
            log_error(f"Rehydrated {len(devs)} devices from SQLite")
    except Exception as e:
        log_error(f"SQLite rehydrate failed (continuing empty): {e}")
        state = load_json(STATE_FILE, {"devices": {}, "events": []})
        devs_raw = state.get("devices", {}) if isinstance(state, dict) else {}
        devs = devs_raw if isinstance(devs_raw, dict) else {}
        events_raw = state.get("events", []) if isinstance(state, dict) else []
        events = events_raw if isinstance(events_raw, list) else []

    stop_evt = threading.Event()
    state_lock = threading.Lock()
    iface_ip_map = iface_primary_ipv4()
    xml_last: Dict[str, int] = {}
    snmp_last: Dict[str, int] = {}

    def mark_changed(rec: dict, now: int, fields: List[str], ip: str):
        """
        Mark device as changed when attributes change.
        v1.5.0: Adds "changed" to lifecycle_flags, doesn't change connection_state
        """
        if not fields:
            return
        
        # Only set "changed" flag for meaningful attribute changes
        meaningful_changes = ["hostname", "mac", "vendor", "manufacturer", "model", "device_type", "interface"]
        has_meaningful_change = any(f in meaningful_changes for f in fields)
        
        if has_meaningful_change:
            # Add "changed" to lifecycle flags
            current_flags = (rec.get("lifecycle_flags", "") or "").split(",")
            current_flags = [f.strip() for f in current_flags if f.strip()]
            if "changed" not in current_flags:
                current_flags.append("changed")
                rec["lifecycle_flags"] = ",".join(current_flags)
                rec["flag_set_time"] = now
                
                # Recompute display status
                conn_state = rec.get("connection_state", "online")
                rec["status"] = ", ".join(current_flags) + ", " + conn_state if current_flags else conn_state
        
        rec["last_change"] = now
        rec["change_fields"] = sorted(list(set(rec.get("change_fields", []) + fields)))
        
        # Create event for meaningful changes
        if has_meaningful_change:
            events.insert(0, make_event("changed", now, ip, rec.get("mac",""), rec.get("hostname",""), {"fields": fields}))

    def on_ssdp(pkt: bytes, src_ip: str):
        nonlocal devs, events, xml_last
        msg = pkt.decode("utf-8", errors="ignore")
        h = parse_http_headers(msg)
        st = h.get("st") or h.get("nt") or ""
        usn = h.get("usn", "")
        server = h.get("server", "")
        location = h.get("location", "")
        now = int(time.time())

        fetch_xml = False
        rec_key = None
        with state_lock:
            key, rec, changed = merge(devs, now, src_ip, "", "", "", "", vendor_map, model_hints, "ssdp", up=True)
            if st and not rec.get("device_type"):
                rec["device_type"] = st[:200]
                changed.append("device_type")
            if server:
                rec.setdefault("banners", {})["ssdp_server"] = server[:200]
            if usn:
                rec.setdefault("banners", {})["ssdp_usn"] = usn[:200]
            mark_changed(rec, now, changed, src_ip)
            devs[key] = rec

            if args.ssdp_fetch_xml and location:
                last = xml_last.get(src_ip, 0)
                if now - last >= max(1, int(args.ssdp_xml_rate_limit)):
                    xml_last[src_ip] = now
                    fetch_xml = True
                    rec_key = key

        if fetch_xml and rec_key:
            info = fetch_upnp_xml(location)
            if info:
                fields = []
                with state_lock:
                    rec = devs.get(rec_key, {})
                    if info.get("manufacturer") and not rec.get("manufacturer"):
                        rec["manufacturer"] = info["manufacturer"][:120]; fields.append("manufacturer")
                    if info.get("modelName") and not rec.get("model"):
                        rec["model"] = info["modelName"][:120]; fields.append("model")
                    if info.get("friendlyName") and not rec.get("hostname"):
                        rec["hostname"] = info["friendlyName"][:120]; fields.append("hostname")
                    if info.get("deviceType") and (not rec.get("device_type") or "urn:" not in rec.get("device_type","")):
                        rec["device_type"] = info["deviceType"][:200]; fields.append("device_type")
                    mark_changed(rec, now, fields, src_ip)
                    if fields:
                        rec.setdefault("source", [])
                        if "upnp_xml" not in rec["source"]:
                            rec["source"].append("upnp_xml")
                    devs[rec_key] = rec

    def on_mdns(pkt: bytes, src_ip: str):
        nonlocal devs, events
        now = int(time.time())
        services = mdns_extract_services(pkt)
        if not services:
            return
        with state_lock:
            key, rec, _ = merge(devs, now, src_ip, "", "", "", "", vendor_map, model_hints, "mdns", up=True)
            cur = rec.get("mdns_services") or []
            merged = sorted(list(set(cur).union(set(services))))
            if merged != cur:
                rec["mdns_services"] = merged
                mark_changed(rec, now, ["mdns_services"], src_ip)
            devs[key] = rec

    def on_llmnr(pkt: bytes, src_ip: str):
        nonlocal devs, events
        now = int(time.time())
        host = llmnr_extract_hostname(pkt)
        if not host:
            return
        with state_lock:
            existing_key = find_record_key_for_ip(devs, src_ip)
            if existing_key and existing_key in devs:
                rec = devs[existing_key]
                if not rec.get("hostname"):
                    rec["hostname"] = host
                    if "llmnr" not in rec.get("source", []):
                        rec.setdefault("source", []).append("llmnr")
                    mark_changed(rec, now, ["hostname"], src_ip)
                rec["last_seen"] = now
                rec["state"] = "UP"
                devs[existing_key] = rec
                return

            key, rec, changed = merge(devs, now, src_ip, "", host, "", "", vendor_map, model_hints, "llmnr", up=True)
            if "hostname" in changed:
                mark_changed(rec, now, ["hostname"], src_ip)
            devs[key] = rec


    def on_nbns(pkt: bytes, src_ip: str):
        nonlocal devs, events
        now = int(time.time())
        host = nbns_extract_hostname(pkt)
        if not host:
            return
        with state_lock:
            existing_key = find_record_key_for_ip(devs, src_ip)
            if existing_key and existing_key in devs:
                rec = devs[existing_key]
                if not rec.get("hostname"):
                    rec["hostname"] = host
                    if "nbns" not in rec.get("source", []):
                        rec.setdefault("source", []).append("nbns")
                    mark_changed(rec, now, ["hostname"], src_ip)
                rec["last_seen"] = now
                rec["state"] = "UP"
                devs[existing_key] = rec
                return

            key, rec, changed = merge(devs, now, src_ip, "", host, "", "", vendor_map, model_hints, "nbns", up=True)
            if "hostname" in changed:
                mark_changed(rec, now, ["hostname"], src_ip)
            devs[key] = rec


    # start listeners
    threads = []
    if args.ssdp:
        for iface, ip in iface_ip_map.items():
            if iface_filter and iface not in iface_filter:
                continue
            t = threading.Thread(target=udp_listener, args=(stop_evt, 1900, SSDP_MCAST, ip, on_ssdp), daemon=True)
            t.start(); threads.append(t)

    if args.mdns:
        for iface, ip in iface_ip_map.items():
            if iface_filter and iface not in iface_filter:
                continue
            t = threading.Thread(target=udp_listener, args=(stop_evt, 5353, MDNS_MCAST, ip, on_mdns), daemon=True)
            t.start(); threads.append(t)

    if args.llmnr:
        for iface, ip in iface_ip_map.items():
            if iface_filter and iface not in iface_filter:
                continue
            t = threading.Thread(target=udp_listener, args=(stop_evt, 5355, LLMNR_MCAST, ip, on_llmnr), daemon=True)
            t.start(); threads.append(t)

    if args.nbns:
        # NBNS is typically broadcast; join-mcast isn't needed.
        for iface, ip in iface_ip_map.items():
            if iface_filter and iface not in iface_filter:
                continue
            t = threading.Thread(target=udp_listener, args=(stop_evt, 137, None, ip, on_nbns), daemon=True)
            t.start(); threads.append(t)

    # Main collection loop
    while True:
        now = int(time.time())
        
        # Sync flag_acknowledged from SQLite (v1.5.0 - updated by UI when user views device)
        try:
            if os.path.exists(DB_FILE):
                sync_conn = sqlite3.connect(DB_FILE, timeout=5.0)
                sync_cur = sync_conn.cursor()
                sync_cur.execute('''
                    SELECT mac, ip, flag_acknowledged, lifecycle_flags, flag_set_time, first_seen
                    FROM devices
                    WHERE flag_acknowledged = 1 OR lifecycle_flags != ""
                ''')
                for row in sync_cur.fetchall():
                    found_key = row[0] or device_key("", row[1] or "")
                    if found_key and found_key not in devs:
                        # Fallback match by current IP
                        for k, rec in devs.items():
                            if rec.get('ip') == row[1]:
                                found_key = k
                                break
                        else:
                            found_key = None
                    if found_key and found_key in devs:
                        devs[found_key]['flag_acknowledged'] = row[2]
                        if row[2] == 1:  # If acknowledged, clear flags
                            devs[found_key]['lifecycle_flags'] = ''
                        if not devs[found_key].get('first_seen'):
                            devs[found_key]['first_seen'] = row[5]
                sync_conn.close()
        except Exception as e:
            # Non-fatal - continue without sync
            pass
        subnets = iface_subnets(iface_filter)
        nets = [(iface, ip_network(cidr, strict=False)) for iface, cidr in subnets]

        if args.active:
            for _iface, cidr in subnets:
                ping_sweep(cidr, args.max_hosts, args.rate_limit_ms)

        # Dual-state aging (offline/missing/gone) is handled later in this loop — no legacy 600s gone block.

        arp = parse_arp()
        leases = parse_dnsmasq_leases()
        seen_ips: Set[str] = set()

        with state_lock:
            for ip, (mac, iface) in arp.items():
                ifn, sn = tag_subnet(ip, nets)
                key, rec, changed = merge(devs, now, ip, mac, "", iface or ifn, sn, vendor_map, model_hints, "arp", up=True)
                seen_ips.add(ip)

                if rec.get("status") == "gone":
                    rec["status"] = "changed"
                    rec["last_change"] = now
                    events.insert(0, make_event("back", now, ip, rec.get("mac",""), rec.get("hostname","")))

                mark_changed(rec, now, changed, ip)
                devs[key] = rec
                if mac:
                    reconcile_ip_mac(devs, ip, mac)

            for ip, (mac, hn) in leases.items():
                ifn, sn = tag_subnet(ip, nets)
                # v2.0.11: DHCP lease doesn't mean device is "up" - only use for discovery/tracking
                key, rec, changed = merge(devs, now, ip, mac, hn, ifn, sn, vendor_map, model_hints, "dnsmasq", up=False)
                # Don't add to seen_ips - DHCP lease alone doesn't mean device is reachable

                if rec.get("status") == "gone":
                    rec["status"] = "changed"
                    rec["last_change"] = now
                    events.insert(0, make_event("back", now, ip, rec.get("mac",""), rec.get("hostname","")))

                mark_changed(rec, now, changed, ip)
                devs[key] = rec

        if args.reverse_dns:
            reverse_targets: List[Tuple[str, str]] = []
            with state_lock:
                for k, rec in list(devs.items()):
                    ip = rec.get("ip", "")
                    if ip and ip in seen_ips and not rec.get("hostname"):
                        reverse_targets.append((k, ip))
            for k, ip in reverse_targets:
                hn = reverse_dns(ip)
                if hn:
                    with state_lock:
                        rec = devs.get(k)
                        if rec and not rec.get("hostname"):
                            rec["hostname"] = hn
                            if "ptr" not in rec.get("source", []):
                                rec.setdefault("source", []).append("ptr")
                            mark_changed(rec, now, ["hostname"], ip)
                            devs[k] = rec

        if args.tcp_probe and ports:
            probe_targets: List[Tuple[str, str]] = []
            with state_lock:
                for k, rec in list(devs.items()):
                    ip = rec.get("ip", "")
                    if ip and ip in seen_ips:
                        probe_targets.append((k, ip))

            for k, ip in probe_targets:
                open_ports, banners = tcp_probe(ip, ports, args.tcp_timeout_ms)
                with state_lock:
                    rec = devs.get(k)
                    if not rec or rec.get("ip") != ip:
                        continue
                    fields = []
                    if open_ports != rec.get("open_ports", []):
                        rec["open_ports"] = open_ports
                        fields.append("open_ports")
                    if banners:
                        rec.setdefault("banners", {}).update(banners)
                        
                        # Analyze banners for device info (v1.6.3+)
                        if HAS_PATTERNS:
                            from device_patterns import extract_os_from_banner
                            for port_str, banner in banners.items():
                                banner_info = guess_device_from_banner(int(port_str), banner)
                                if banner_info.get('device_type') and not rec.get('device_type'):
                                    rec['device_type'] = banner_info['device_type']
                                    fields.append('device_type')
                                
                                # Extract OS and version (v1.6.3)
                                os_info = extract_os_from_banner(int(port_str), banner)
                                if os_info.get('os'):
                                    if not rec.get('discovered_os'):
                                        rec['discovered_os'] = os_info['os']
                                    if not rec.get('os'):
                                        rec['os'] = os_info['os']
                                        fields.append('os')
                                if os_info.get('os_version'):
                                    if not rec.get('os_version'):
                                        rec['os_version'] = os_info['os_version']
                                        fields.append('os_version')
                    
                    if fields:
                        mark_changed(rec, now, fields, ip)
                    if "tcp_probe" not in rec.get("source", []):
                        rec.setdefault("source", []).append("tcp_probe")
                    devs[k] = rec

        if args.snmp and communities:
            snmp_targets: List[Tuple[str, str]] = []
            with state_lock:
                for k, rec in list(devs.items()):
                    ip = rec.get("ip", "")
                    if not ip or ip not in seen_ips:
                        continue
                    last = snmp_last.get(ip, 0)
                    if now - last < max(60, int(args.snmp_rate_limit)):
                        continue
                    snmp_last[ip] = now
                    snmp_targets.append((k, ip))

            for k, ip in snmp_targets:
                sysname, sysdescr = snmp_enrich(ip, communities, args.snmp_timeout_ms)
                with state_lock:
                    rec = devs.get(k)
                    if not rec or rec.get("ip") != ip:
                        continue
                    fields = []
                    if sysname and sysname != rec.get("snmp_sysname",""):
                        rec["snmp_sysname"] = sysname
                        fields.append("snmp_sysname")
                    if sysdescr and sysdescr != rec.get("snmp_sysdescr",""):
                        rec["snmp_sysdescr"] = sysdescr
                        fields.append("snmp_sysdescr")
                    if fields:
                        if "snmp" not in rec.get("source", []):
                            rec.setdefault("source", []).append("snmp")
                        mark_changed(rec, now, fields, ip)
                    devs[k] = rec

        with state_lock:
            events = events[:500]
            devs = prune(devs)
            
            # Update device statuses using dual-state system (v1.5.0, v2.0.11 - use seen_ips)
            for k, rec in devs.items():
                ip = rec.get("ip")
                if ip:
                    # Check if device was seen this cycle (v2.0.11: use seen_ips not timestamp)
                    # seen_ips only includes ARP entries, not DHCP leases
                    was_seen_this_scan = ip in seen_ips
                    
                    # Update connection state
                    old_conn_state = rec.get("connection_state", "online")
                    new_conn_state = update_connection_state(rec, now, was_seen_this_scan, args.interval)
                    rec["connection_state"] = new_conn_state
                    
                    # Update lifecycle flags
                    flags = update_lifecycle_flags(rec, now, old_conn_state, new_conn_state)
                    rec["lifecycle_flags"] = ",".join(flags) if flags else ""
                    
                    # Compute display status (for compatibility and UI)
                    if flags:
                        rec["status"] = ", ".join(flags) + ", " + new_conn_state
                    else:
                        rec["status"] = new_conn_state
                    
                    # Create events for connection state changes
                    if old_conn_state != new_conn_state:
                        event_type = new_conn_state
                        if new_conn_state == "offline":
                            events.insert(0, make_event("offline", now, ip, rec.get("mac",""), rec.get("hostname",""), {}))
                        elif new_conn_state == "missing":
                            events.insert(0, make_event("missing", now, ip, rec.get("mac",""), rec.get("hostname",""), {}))
                        elif new_conn_state == "gone":
                            events.insert(0, make_event("gone", now, ip, rec.get("mac",""), rec.get("hostname",""), {}))
                        elif new_conn_state == "online" and old_conn_state in ["offline", "missing", "gone"]:
                            events.insert(0, make_event("back", now, ip, rec.get("mac",""), rec.get("hostname",""), {}))
            
            snapshot_devices = list(devs.values())
            snapshot_events = list(events)

        snapshot_devices.sort(key=lambda d: int(d.get("last_seen", 0)), reverse=True)
        
        # Determine DHCP type for all devices (v1.5.1)
        if HAS_DHCP_ANALYZER:
            try:
                ip_list = [d.get('ip') for d in snapshot_devices if d.get('ip')]
                dhcp_types = get_dhcp_info_batch(ip_list)
                for dev in snapshot_devices:
                    ip = dev.get('ip')
                    if ip:
                        dev['dhcp_type'] = dhcp_types.get(ip, 'unknown')
            except Exception as e:
                # Non-fatal - continue without DHCP type
                pass
        
        # Discover WiFi AP associations (v2.0.2 - syslog + SNMP)
        client_to_ap_id = {}
        
        # Method 1: Try syslog parsing first (works with all APs)
        if HAS_SYSLOG_PARSER:
            try:
                # Parse syslogs for client associations (last 24 hours)
                associations = parse_multiple_syslogs(hours_back=24)
                # Returns: {mac: (ap_identifier, timestamp)}
                
                if associations:
                    # Build known APs map for identifier resolution
                    known_aps = {}
                    for d in snapshot_devices:
                        dt = d.get('device_type', '').lower()
                        hn = d.get('hostname', '').lower()
                        if 'access point' in dt or 'ap' in dt or 'ap-' in hn or 'unifi' in hn:
                            known_aps[d.get('ip')] = d.get('hostname', '')
                    
                    # Resolve identifiers to IPs
                    for mac, (ap_id, timestamp) in associations.items():
                        resolved_ip = resolve_ap_identifier(ap_id, known_aps)
                        client_to_ap_id[mac] = (resolved_ip, timestamp)
            except Exception as e:
                # Non-fatal - try SNMP fallback
                pass
        
        # Method 2: Try SNMP if syslog didn't work or SNMP explicitly enabled
        if (not client_to_ap_id) and HAS_AP_DETECTOR and args.snmp:
            try:
                # Find all APs in inventory
                ap_devices = [d for d in snapshot_devices if d.get('device_type') and 
                             ('access point' in d.get('device_type', '').lower() or 
                              'ap' in d.get('device_type', '').lower() or
                              'unifi' in d.get('hostname', '').lower() or
                              'ap-' in d.get('hostname', '').lower())]
                
                if ap_devices:
                    # Query all APs for their clients
                    ap_list = [{'ip': ap.get('ip'), 'hostname': ap.get('hostname')} for ap in ap_devices]
                    snmp_client_to_ap = discover_ap_clients(ap_list, communities)
                    
                    # Convert to same format
                    for mac, ap_ip in snmp_client_to_ap.items():
                        client_to_ap_id[mac] = (ap_ip, now)
            except Exception as e:
                # Non-fatal - continue without AP detection
                pass
        
        # Apply AP associations to devices
        if client_to_ap_id:
            ap_name_cache = {}
            for dev in snapshot_devices:
                mac = dev.get('mac', '').upper()
                if mac and mac in client_to_ap_id:
                    ap_identifier, timestamp = client_to_ap_id[mac]
                    dev['connected_to_ap'] = ap_identifier
                    dev['ap_last_seen'] = timestamp
                    
                    # Find AP name (cache for efficiency)
                    if ap_identifier not in ap_name_cache:
                        for other_dev in snapshot_devices:
                            if other_dev.get('ip') == ap_identifier:
                                ap_name_cache[ap_identifier] = other_dev.get('hostname', ap_identifier)
                                break
                        if ap_identifier not in ap_name_cache:
                            ap_name_cache[ap_identifier] = ap_identifier
                    
                    dev['ap_name'] = ap_name_cache[ap_identifier]
        
        # Write to SQLite only (v1.1.2+)
        try:
            write_to_sqlite(snapshot_devices, snapshot_events)
            if HAS_ALERTS and snapshot_events:
                try:
                    send_alerts(snapshot_events[:50])
                except Exception as e:
                    log_error(f"Alert dispatch error: {e}")
        except Exception as e:
            log_error(f"SQLite write error: {e}")
            # Emergency fallback: write JSON if SQLite fails
            try:
                save_json(STATE_FILE, {"devices": devs, "events": snapshot_events})
                out = {"generated_at": now, "devices": snapshot_devices, "events": snapshot_events}
                tmp = OUT_FILE + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(out, f, indent=2, sort_keys=False)
                os.replace(tmp, OUT_FILE)
                log_error("SQLite failed, wrote emergency JSON backup")
            except Exception as json_err:
                log_error(f"Emergency JSON write also failed: {json_err}")

        if args.once:
            break
        time.sleep(max(10, int(args.interval)))

    stop_evt.set()

if __name__ == "__main__":
    try:
        with open(STARTUP_LOG, "a") as f:
            f.write("  Entering main()...\n")
            f.flush()
        main()
    except Exception as e:
        # Log to both startup log and error log
        import traceback
        tb = traceback.format_exc()
        
        try:
            with open(STARTUP_LOG, "a") as f:
                f.write(f"\n  ✗✗✗ FATAL ERROR ✗✗✗\n")
                f.write(f"  {e}\n")
                f.write(f"  {tb}\n")
                f.flush()
        except Exception:
            pass
        
        log_error(f"FATAL ERROR: {e}")
        log_error(tb)
        sys.exit(1)
