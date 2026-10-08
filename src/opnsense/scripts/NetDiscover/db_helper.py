#!/usr/local/bin/python3
"""
SQLite Database Helper for NetDiscover
Handles all database operations and historical tracking
v2.1.0 — device identity keyed by MAC
"""

import sqlite3
import json
import os
import time
from typing import Dict, List, Optional, Any

DB_DIR = "/var/db/netdiscover"
DB_FILE = os.path.join(DB_DIR, "netdiscover.db")
SCHEMA_FILE = "/usr/local/opnsense/scripts/NetDiscover/db_schema.sql"


def normalize_mac(mac: str) -> str:
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
    m = normalize_mac(mac)
    if m:
        return m
    if ip:
        return f"ip:{ip}"
    return ""


class NetDiscoverDB:
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self._ensure_db_dir()
        self.conn = None
        self._init_db()
    
    def _ensure_db_dir(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def _init_db(self):
        """Initialize database with schema if it doesn't exist"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
        if os.path.exists(SCHEMA_FILE):
            with open(SCHEMA_FILE, 'r') as f:
                schema = f.read()
                self.conn.executescript(schema)
        else:
            self._create_schema()
        
        self.conn.commit()
    
    def _create_schema(self):
        """Fallback schema creation if schema file missing"""
        cur = self.conn.cursor()
        
        cur.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                mac TEXT PRIMARY KEY,
                ip TEXT,
                hostname TEXT,
                hostname_override INTEGER DEFAULT 0,
                vendor TEXT,
                status TEXT,
                device_type TEXT,
                tags TEXT,
                manufacturer TEXT,
                model TEXT,
                mdns_services TEXT,
                open_ports TEXT,
                snmp_sysname TEXT,
                snmp_sysdescr TEXT,
                interface TEXT,
                subnet TEXT,
                first_seen INTEGER,
                last_seen INTEGER,
                notes TEXT,
                created_at INTEGER DEFAULT (strftime('%s', 'now')),
                updated_at INTEGER DEFAULT (strftime('%s', 'now'))
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
                details TEXT,
                created_at INTEGER DEFAULT (strftime('%s', 'now'))
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
                details TEXT,
                created_at INTEGER DEFAULT (strftime('%s', 'now'))
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
                location TEXT,
                tags TEXT,
                notes TEXT,
                created_at INTEGER DEFAULT (strftime('%s', 'now')),
                updated_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        ''')
        
        cur.execute('CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON devices(last_seen)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_devices_ip ON devices(ip)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_history_mac ON device_history(mac, timestamp DESC)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_history_timestamp ON device_history(timestamp DESC)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp DESC)')
        
        self.conn.commit()
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def upsert_device(self, device: Dict[str, Any]) -> None:
        """Insert or update a device by MAC, tracking changes in history"""
        ip = device.get('ip') or ''
        key = device_key(device.get('mac') or '', ip)
        if not key:
            return
        
        now = int(time.time())
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM devices WHERE mac = ?', (key,))
        existing = cur.fetchone()
        
        device_data = {
            'mac': key,
            'ip': ip,
            'hostname': device.get('hostname', ''),
            'hostname_override': 1 if device.get('hostname_override') else 0,
            'vendor': device.get('vendor', ''),
            'connection_state': device.get('connection_state', 'online'),
            'lifecycle_flags': device.get('lifecycle_flags', ''),
            'status': device.get('status', ''),
            'dhcp_type': device.get('dhcp_type', 'unknown'),
            'device_type': device.get('device_type', ''),
            'device_type_source': device.get('device_type_source', ''),
            'tags': json.dumps(device.get('tags', [])),
            'manufacturer': device.get('manufacturer', ''),
            'model': device.get('model', ''),
            'os': device.get('os', ''),
            'mdns_services': json.dumps(device.get('mdns_services', [])),
            'open_ports': json.dumps(device.get('open_ports', [])),
            'banners': json.dumps(device.get('banners', {})),
            'snmp_sysname': device.get('snmp_sysname', ''),
            'snmp_sysdescr': device.get('snmp_sysdescr', ''),
            'interface': device.get('interface', ''),
            'subnet': device.get('subnet', ''),
            'first_seen': device.get('first_seen', now),
            'last_seen': device.get('last_seen', now),
            'flag_set_time': device.get('flag_set_time', now),
            'flag_acknowledged': device.get('flag_acknowledged', 0),
            'connected_to_ap': device.get('connected_to_ap', ''),
            'ap_name': device.get('ap_name', ''),
            'ap_last_seen': device.get('ap_last_seen', 0),
            'notes': device.get('notes', ''),
            'updated_at': now
        }
        
        if existing:
            changes = []
            for field in ['hostname', 'vendor', 'status', 'device_type', 'manufacturer', 'model', 'interface', 'subnet', 'ip']:
                old_val = existing[field] if field in existing.keys() else ''
                new_val = device_data[field]
                if old_val != new_val and new_val:
                    changes.append((field, old_val, new_val))
            
            for field, old_val, new_val in changes:
                self.add_history(key, ip, 'attribute_change', field, old_val, new_val)
            
            cur.execute('''
                UPDATE devices SET
                    ip=?, hostname=?, hostname_override=?, vendor=?,
                    connection_state=?, lifecycle_flags=?, status=?, dhcp_type=?,
                    device_type=?, device_type_source=?, tags=?, manufacturer=?, model=?, os=?,
                    mdns_services=?, open_ports=?, banners=?, snmp_sysname=?, snmp_sysdescr=?,
                    interface=?, subnet=?, last_seen=?, flag_set_time=?, flag_acknowledged=?,
                    connected_to_ap=?, ap_name=?, ap_last_seen=?,
                    notes=?, updated_at=?
                WHERE mac=?
            ''', (
                device_data['ip'], device_data['hostname'], device_data['hostname_override'],
                device_data['vendor'],
                device_data['connection_state'], device_data['lifecycle_flags'], device_data['status'],
                device_data['dhcp_type'],
                device_data['device_type'], device_data['device_type_source'], device_data['tags'], 
                device_data['manufacturer'], device_data['model'], device_data['os'],
                device_data['mdns_services'], device_data['open_ports'], device_data['banners'],
                device_data['snmp_sysname'], device_data['snmp_sysdescr'],
                device_data['interface'], device_data['subnet'],
                device_data['last_seen'], device_data['flag_set_time'], device_data['flag_acknowledged'],
                device_data['connected_to_ap'], device_data['ap_name'], device_data['ap_last_seen'],
                device_data['notes'], device_data['updated_at'],
                key
            ))
        else:
            cur.execute('''
                INSERT INTO devices (
                    mac, ip, hostname, hostname_override, vendor,
                    connection_state, lifecycle_flags, status, dhcp_type,
                    device_type, device_type_source, tags, manufacturer, model, os,
                    mdns_services, open_ports, banners, snmp_sysname, snmp_sysdescr,
                    interface, subnet, first_seen, last_seen,
                    flag_set_time, flag_acknowledged,
                    connected_to_ap, ap_name, ap_last_seen,
                    notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                device_data['mac'], device_data['ip'], device_data['hostname'],
                device_data['hostname_override'], device_data['vendor'],
                device_data['connection_state'], device_data['lifecycle_flags'], device_data['status'],
                device_data['dhcp_type'],
                device_data['device_type'], device_data['device_type_source'], device_data['tags'],
                device_data['manufacturer'], device_data['model'], device_data['os'],
                device_data['mdns_services'], device_data['open_ports'], device_data['banners'],
                device_data['snmp_sysname'], device_data['snmp_sysdescr'],
                device_data['interface'], device_data['subnet'],
                device_data['first_seen'], device_data['last_seen'],
                device_data['flag_set_time'], device_data['flag_acknowledged'],
                device_data['connected_to_ap'], device_data['ap_name'], device_data['ap_last_seen'],
                device_data['notes'],
                now, now
            ))
            
            self.add_history(key, ip, 'discovered', None, None, None, 
                           json.dumps({'mac': key, 'hostname': device_data['hostname']}))
        
        self.conn.commit()
    
    def add_history(self, mac: str, ip: str, event_type: str, field_name: Optional[str] = None,
                   old_value: Optional[str] = None, new_value: Optional[str] = None,
                   details: Optional[str] = None) -> None:
        """Add an entry to device history"""
        cur = self.conn.cursor()
        cur.execute('''
            INSERT INTO device_history (mac, ip, timestamp, event_type, field_name, old_value, new_value, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (mac, ip or '', int(time.time()), event_type, field_name, old_value, new_value, details))
        self.conn.commit()
    
    def add_event(self, event_type: str, ip: str, mac: str = '', hostname: str = '', details: Dict = None) -> None:
        """Add an event to the events table"""
        cur = self.conn.cursor()
        key = device_key(mac, ip)
        cur.execute('''
            INSERT INTO events (timestamp, event_type, ip, mac, hostname, details)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (int(time.time()), event_type, ip, key, hostname, json.dumps(details or {})))
        self.conn.commit()
    
    def get_all_devices(self) -> List[Dict]:
        """Get all devices with their current state"""
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM devices ORDER BY last_seen DESC')
        rows = cur.fetchall()
        
        result = []
        for row in rows:
            device = dict(row)
            device['tags'] = json.loads(device['tags']) if device.get('tags') else []
            device['mdns_services'] = json.loads(device['mdns_services']) if device.get('mdns_services') else []
            device['open_ports'] = json.loads(device['open_ports']) if device.get('open_ports') else []
            # Present synthetic keys as empty MAC in UI consumers
            if str(device.get('mac') or '').startswith('ip:'):
                device['id'] = device['mac']
                device['mac'] = ''
            result.append(device)
        
        return result
    
    def get_device_history(self, mac: str = '', ip: str = '', limit: int = 100) -> List[Dict]:
        """Get history for a specific device (prefer MAC)."""
        cur = self.conn.cursor()
        key = device_key(mac, ip)
        if key:
            cur.execute('''
                SELECT * FROM device_history 
                WHERE mac = ? OR ip = ?
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (key, ip or '', limit))
        elif ip:
            cur.execute('''
                SELECT * FROM device_history 
                WHERE ip = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (ip, limit))
        else:
            return []
        
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    
    def get_recent_events(self, limit: int = 100) -> List[Dict]:
        """Get recent events"""
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM events ORDER BY timestamp DESC LIMIT ?', (limit,))
        rows = cur.fetchall()
        
        result = []
        for row in rows:
            event = dict(row)
            event['details'] = json.loads(event['details']) if event['details'] else {}
            event['time'] = event['timestamp']
            result.append(event)
        
        return result
    
    def set_override(self, mac: str = '', ip: str = '', hostname: str = None, device_type: str = None,
                    manufacturer: str = None, model: str = None, os: str = None,
                    location: str = None, tags: str = None, notes: str = None) -> None:
        """Set or update device overrides (keyed by MAC)."""
        key = device_key(mac, ip)
        if not key:
            return
        cur = self.conn.cursor()
        now = int(time.time())
        
        cur.execute('''
            INSERT INTO device_overrides (mac, ip, hostname, device_type, manufacturer, model, os, location, tags, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(mac) DO UPDATE SET
                ip=excluded.ip,
                hostname=excluded.hostname,
                device_type=excluded.device_type,
                manufacturer=excluded.manufacturer,
                model=excluded.model,
                os=excluded.os,
                location=excluded.location,
                tags=excluded.tags,
                notes=excluded.notes,
                updated_at=excluded.updated_at
        ''', (key, ip, hostname, device_type, manufacturer, model, os, location, tags, notes, now, now))
        
        self.conn.commit()
    
    def delete_override(self, mac: str = '', ip: str = '') -> None:
        """Delete device overrides"""
        key = device_key(mac, ip)
        cur = self.conn.cursor()
        if key:
            cur.execute('DELETE FROM device_overrides WHERE mac = ?', (key,))
        elif ip:
            cur.execute('DELETE FROM device_overrides WHERE ip = ?', (ip,))
        self.conn.commit()
    
    def get_override(self, mac: str = '', ip: str = '') -> Optional[Dict]:
        """Get override for a specific device"""
        key = device_key(mac, ip)
        cur = self.conn.cursor()
        if key:
            cur.execute('SELECT * FROM device_overrides WHERE mac = ?', (key,))
        elif ip:
            cur.execute('SELECT * FROM device_overrides WHERE ip = ?', (ip,))
        else:
            return None
        row = cur.fetchone()
        return dict(row) if row else None
    
    def cleanup_old_devices(self, max_age_seconds: int = 2592000):  # 30 days default
        """Remove devices not seen in max_age_seconds"""
        cur = self.conn.cursor()
        cutoff = int(time.time()) - max_age_seconds
        cur.execute('DELETE FROM devices WHERE last_seen < ?', (cutoff,))
        self.conn.commit()
        return cur.rowcount
    
    def get_device_stats(self) -> Dict:
        """Get summary statistics"""
        cur = self.conn.cursor()
        
        cur.execute('SELECT COUNT(*) as total FROM devices')
        total = cur.fetchone()['total']
        
        now = int(time.time())
        cur.execute('SELECT COUNT(*) as up FROM devices WHERE last_seen > ?', (now - 600,))
        up = cur.fetchone()['up']
        
        cur.execute(
            'SELECT COUNT(*) as new FROM devices WHERE last_seen > ? AND (lifecycle_flags LIKE ? OR status LIKE ?)',
            (now - 86400, '%new%', '%new%')
        )
        new = cur.fetchone()['new']
        
        cur.execute(
            'SELECT COUNT(*) as changed FROM devices WHERE last_seen > ? AND (lifecycle_flags LIKE ? OR status LIKE ?)',
            (now - 86400, '%changed%', '%changed%')
        )
        changed = cur.fetchone()['changed']
        
        cur.execute(
            'SELECT COUNT(*) as gone FROM devices WHERE last_seen > ? AND (connection_state = ? OR status LIKE ?)',
            (now - 86400, 'gone', '%gone%')
        )
        gone = cur.fetchone()['gone']
        
        return {
            'total': total,
            'up_10m': up,
            'new_24h': new,
            'changed_24h': changed,
            'gone_24h': gone
        }
