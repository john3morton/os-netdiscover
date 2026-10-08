#!/usr/local/bin/python3
"""
Download and update IEEE OUI (MAC vendor) database in SQLite
Can be run manually or automatically via cron
"""

import urllib.request
import re
import os
import sys
import time
import sqlite3

OUI_URL = "https://standards-oui.ieee.org/oui/oui.txt"
OUI_DB_FILE = "/var/db/netdiscover/oui.db"
DEVICES_DB_FILE = "/var/db/netdiscover/netdiscover.db"


def mac_to_oui(mac):
    """Extract OUI (first 3 octets) from MAC address"""
    if not mac:
        return None
    
    mac = mac.upper().replace('-', ':')
    parts = mac.split(':')
    if len(parts) >= 3:
        return f"{parts[0]}:{parts[1]}:{parts[2]}"
    return None


def backfill_device_vendors(devices_conn, oui_conn=None):
    """
    Update vendor field for devices with MAC but no/incorrect vendor.
    devices_conn: connection to netdiscover.db
    oui_conn: optional connection to oui.db (will open if None)
    Returns count of devices updated.
    """
    # Open OUI database if not provided
    close_oui = False
    if oui_conn is None:
        if not os.path.exists(OUI_DB_FILE):
            return 0
        oui_conn = sqlite3.connect(OUI_DB_FILE)
        oui_conn.row_factory = sqlite3.Row
        close_oui = True
    
    devices_cur = devices_conn.cursor()
    oui_cur = oui_conn.cursor()
    
    # Find devices with MAC but missing or empty vendor
    devices_cur.execute('''
        SELECT ip, mac, vendor FROM devices 
        WHERE mac IS NOT NULL AND mac != '' 
        AND (vendor IS NULL OR vendor = '')
    ''')
    
    devices_to_update = devices_cur.fetchall()
    updated_count = 0
    
    for row in devices_to_update:
        ip = row[0]
        mac = row[1]
        old_vendor = row[2] or ''
        
        oui = mac_to_oui(mac)
        if not oui:
            continue
        
        # Lookup vendor from OUI database
        oui_cur.execute('SELECT vendor FROM oui WHERE oui = ?', (oui,))
        oui_row = oui_cur.fetchone()
        
        if oui_row:
            new_vendor = oui_row[0] if isinstance(oui_row, tuple) else oui_row['vendor']
            
            # Update device in devices database
            devices_cur.execute('UPDATE devices SET vendor = ? WHERE ip = ?', (new_vendor, ip))
            
            # Log to device history
            devices_cur.execute('''
                INSERT INTO device_history (ip, timestamp, event_type, field_name, old_value, new_value, details)
                VALUES (?, ?, 'attribute_change', 'vendor', ?, ?, ?)
            ''', (ip, int(time.time()), old_vendor, new_vendor, 
                  f'{{"source": "oui_update", "mac": "{mac}", "oui": "{oui}"}}'))
            
            updated_count += 1
    
    devices_conn.commit()
    
    if close_oui:
        oui_conn.close()
    
    return updated_count


def download_oui():
    """Download IEEE OUI database and store in SQLite"""
    print(f"Downloading OUI database from {OUI_URL}...")
    
    try:
        # Download with timeout
        req = urllib.request.Request(OUI_URL)
        req.add_header('User-Agent', 'NetDiscover-OPNsense/1.2.0')
        
        with urllib.request.urlopen(req, timeout=60) as response:
            data = response.read().decode('utf-8', errors='ignore')
        
        print(f"Downloaded {len(data)} bytes")
        
        # Parse OUI format
        # Example lines:
        # 00-00-00   (hex)		XEROX CORPORATION
        # 00-00-01   (hex)		XEROX CORPORATION
        
        entries = {}
        for line in data.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Match OUI pattern: XX-XX-XX   (hex)		Vendor Name
            match = re.match(r'^([0-9A-F]{2})-([0-9A-F]{2})-([0-9A-F]{2})\s+\(hex\)\s+(.+)$', line, re.IGNORECASE)
            if match:
                oui = f"{match.group(1)}:{match.group(2)}:{match.group(3)}".upper()
                vendor = match.group(4).strip()
                entries[oui] = vendor
        
        if not entries:
            print("ERROR: No OUI entries parsed from downloaded file", file=sys.stderr)
            return False
        
        print(f"Parsed {len(entries)} OUI entries")
        
        # Write to separate OUI database
        os.makedirs(os.path.dirname(OUI_DB_FILE), exist_ok=True)
        
        oui_conn = sqlite3.connect(OUI_DB_FILE)
        cur = oui_conn.cursor()
        
        # Create OUI table if not exists
        cur.execute('''
            CREATE TABLE IF NOT EXISTS oui (
                oui TEXT PRIMARY KEY,
                vendor TEXT NOT NULL,
                updated_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        ''')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_oui_vendor ON oui(vendor)')
        
        # Metadata table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS oui_metadata (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        ''')
        
        # Clear existing entries
        cur.execute('DELETE FROM oui')
        
        # Bulk insert
        now = int(time.time())
        cur.executemany(
            'INSERT INTO oui (oui, vendor, updated_at) VALUES (?, ?, ?)',
            [(oui, vendor, now) for oui, vendor in entries.items()]
        )
        
        # Update metadata
        cur.execute('INSERT OR REPLACE INTO oui_metadata (key, value, updated_at) VALUES (?, ?, ?)',
                   ('last_update', str(now), now))
        cur.execute('INSERT OR REPLACE INTO oui_metadata (key, value, updated_at) VALUES (?, ?, ?)',
                   ('entry_count', str(len(entries)), now))
        cur.execute('INSERT OR REPLACE INTO oui_metadata (key, value, updated_at) VALUES (?, ?, ?)',
                   ('source_url', OUI_URL, now))
        
        oui_conn.commit()
        oui_conn.close()
        
        print(f"✅ OUI database written to {OUI_DB_FILE}")
        print(f"   {len(entries)} vendor entries")
        
        # Backfill vendor info for existing devices (separate connection)
        if os.path.exists(DEVICES_DB_FILE):
            print("\nBackfilling vendor info for existing devices...")
            devices_conn = sqlite3.connect(DEVICES_DB_FILE)
            backfilled = backfill_device_vendors(devices_conn, oui_conn=None)
            devices_conn.close()
            print(f"✅ Updated {backfilled} device(s) with vendor information")
        else:
            print("Devices database not found yet, skipping backfill")
        
        return True
        
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.reason}", file=sys.stderr)
        return False
    except urllib.error.URLError as e:
        print(f"URL Error: {e.reason}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


def get_oui_age():
    """Return age of OUI data in database (days), or None if doesn't exist"""
    if not os.path.exists(OUI_DB_FILE):
        return None
    
    try:
        conn = sqlite3.connect(OUI_DB_FILE)
        cur = conn.cursor()
        
        # Check if OUI table exists and has data
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='oui'")
        if not cur.fetchone():
            conn.close()
            return None
        
        cur.execute('SELECT COUNT(*) as cnt FROM oui')
        count = cur.fetchone()[0]
        if count == 0:
            conn.close()
            return None
        
        # Get most recent update timestamp
        cur.execute('SELECT MAX(updated_at) as latest FROM oui')
        latest = cur.fetchone()[0]
        conn.close()
        
        if latest:
            age_seconds = time.time() - latest
            age_days = age_seconds / 86400
            return age_days
        
        return None
    except Exception:
        return None


def main():
    import argparse
    ap = argparse.ArgumentParser(description='Update IEEE OUI (MAC vendor) database')
    ap.add_argument('--force', action='store_true', help='Download even if data is recent')
    ap.add_argument('--check', action='store_true', help='Only check age, do not download')
    ap.add_argument('--backfill-only', action='store_true', help='Only backfill vendors, do not download')
    args = ap.parse_args()
    
    if args.backfill_only:
        # Just backfill vendors for existing devices
        if not os.path.exists(DEVICES_DB_FILE):
            print("Devices database not found", file=sys.stderr)
            sys.exit(1)
        
        if not os.path.exists(OUI_DB_FILE):
            print("OUI database not found", file=sys.stderr)
            sys.exit(1)
        
        try:
            devices_conn = sqlite3.connect(DEVICES_DB_FILE)
            updated = backfill_device_vendors(devices_conn)
            devices_conn.close()
            print(f"✅ Backfilled vendor info for {updated} device(s)")
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    
    age = get_oui_age()
    
    if args.check:
        if age is None:
            print("OUI database not found")
            sys.exit(1)
        else:
            print(f"OUI database age: {age:.1f} days")
            print(f"Database: {OUI_DB_FILE}")
            sys.exit(0)
    
    # Download if data doesn't exist or is older than 30 days
    should_update = False
    
    if age is None:
        print("OUI database not found, downloading...")
        should_update = True
    elif age > 30:
        print(f"OUI database is {age:.1f} days old (>30 days), updating...")
        should_update = True
    elif args.force:
        print("Force update requested")
        should_update = True
    else:
        print(f"OUI database is {age:.1f} days old, no update needed")
        print("Use --force to update anyway")
        sys.exit(0)
    
    if should_update:
        success = download_oui()
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

