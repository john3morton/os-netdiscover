#!/usr/local/bin/python3
"""
Download Wireshark's extended manufacturer database
More detailed than IEEE OUI - includes model hints and short names
"""

import urllib.request
import re
import os
import sys
import time
import sqlite3

MANUF_URL = "https://www.wireshark.org/download/automated/data/manuf"
OUI_DB_FILE = "/var/db/netdiscover/oui.db"


def download_wireshark_manuf():
    """Download Wireshark manuf file and store in SQLite"""
    print(f"Downloading Wireshark manufacturer database from {MANUF_URL}...")
    
    try:
        req = urllib.request.Request(MANUF_URL)
        req.add_header('User-Agent', 'NetDiscover-OPNsense/1.3.0')
        
        with urllib.request.urlopen(req, timeout=60) as response:
            data = response.read().decode('utf-8', errors='ignore')
        
        print(f"Downloaded {len(data)} bytes")
        
        # Parse Wireshark format
        # Examples:
        # 00:00:0C	Cisco		Cisco Systems, Inc
        # 00:00:0C:07:AC/40	Cisco		Cisco IOS Software  ← Model hint!
        
        entries = {}
        model_hints = {}  # Extended MAC entries with model info
        
        for line in data.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Match: MAC/mask<tab>ShortName<tab>LongName
            parts = re.split(r'\t+', line)
            if len(parts) < 2:
                continue
            
            mac_part = parts[0].upper().replace(':', '')
            short_name = parts[1].strip() if len(parts) > 1 else ''
            long_name = parts[2].strip() if len(parts) > 2 else short_name
            
            # Handle /mask notation (e.g., 00:00:0C:07:AC/40)
            has_model_hint = '/' in mac_part
            if has_model_hint:
                mac_part = mac_part.split('/')[0]
            
            # Convert to standard format
            if len(mac_part) >= 6:
                oui = f"{mac_part[0:2]}:{mac_part[2:4]}:{mac_part[4:6]}"
                
                # Use long name if available, else short name
                vendor = long_name if long_name else short_name
                
                if vendor:
                    # Store basic OUI
                    if oui not in entries:  # Don't overwrite with less specific entry
                        entries[oui] = vendor
                    
                    # If extended MAC with model hint, store separately
                    if has_model_hint and len(mac_part) > 6:
                        # This is a model hint - extract it
                        # The long_name often contains product info
                        model_hints[oui] = long_name
        
        if not entries:
            print("ERROR: No entries parsed from Wireshark manuf", file=sys.stderr)
            return False
        
        print(f"Parsed {len(entries)} entries")
        
        # Write to OUI database
        os.makedirs(os.path.dirname(OUI_DB_FILE), exist_ok=True)
        
        conn = sqlite3.connect(OUI_DB_FILE)
        cur = conn.cursor()
        
        # Create table if not exists
        cur.execute('''
            CREATE TABLE IF NOT EXISTS oui (
                oui TEXT PRIMARY KEY,
                vendor TEXT NOT NULL,
                updated_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        ''')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_oui_vendor ON oui(vendor)')
        
        # Clear and repopulate
        cur.execute('DELETE FROM oui')
        
        now = int(time.time())
        cur.executemany(
            'INSERT INTO oui (oui, vendor, updated_at) VALUES (?, ?, ?)',
            [(oui, vendor, now) for oui, vendor in entries.items()]
        )
        
        # Update metadata
        cur.execute('''
            CREATE TABLE IF NOT EXISTS oui_metadata (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at INTEGER
            )
        ''')
        # Create model hints table (v1.6.1)
        cur.execute('''
            CREATE TABLE IF NOT EXISTS oui_models (
                oui TEXT PRIMARY KEY,
                model_hint TEXT,
                updated_at INTEGER
            )
        ''')
        
        # Store model hints
        if model_hints:
            cur.execute('DELETE FROM oui_models')
            cur.executemany(
                'INSERT INTO oui_models (oui, model_hint, updated_at) VALUES (?, ?, ?)',
                [(oui, hint, now) for oui, hint in model_hints.items()]
            )
        
        cur.execute('INSERT OR REPLACE INTO oui_metadata VALUES (?, ?, ?)',
                   ('source', 'wireshark', now))
        cur.execute('INSERT OR REPLACE INTO oui_metadata VALUES (?, ?, ?)',
                   ('entry_count', str(len(entries)), now))
        cur.execute('INSERT OR REPLACE INTO oui_metadata VALUES (?, ?, ?)',
                   ('model_hints', str(len(model_hints)), now))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Wireshark manufacturer database written to {OUI_DB_FILE}")
        print(f"   {len(model_hints)} model hints extracted")
        print(f"   {len(entries)} vendor entries (extended format)")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='Download Wireshark extended manufacturer database')
    ap.add_argument('--force', action='store_true', help='Force download')
    args = ap.parse_args()
    
    success = download_wireshark_manuf()
    sys.exit(0 if success else 1)

