#!/usr/local/bin/python3
"""
Migration script: Convert NetDiscover JSON data to SQLite
Run this once to migrate from v0.x (JSON) to v1.1+ (SQLite)
"""

import json
import os
import sys
import time
from db_helper import NetDiscoverDB

DB_DIR = "/var/db/netdiscover"
OLD_DEVICES_FILE = os.path.join(DB_DIR, "devices.json")
OLD_STATE_FILE = os.path.join(DB_DIR, "state.json")
BACKUP_DIR = os.path.join(DB_DIR, "json_backup")


def migrate():
    print("NetDiscover: Migrating JSON data to SQLite...")
    
    # Create backup directory
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    # Backup existing JSON files
    for src in [OLD_DEVICES_FILE, OLD_STATE_FILE]:
        if os.path.exists(src):
            dst = os.path.join(BACKUP_DIR, os.path.basename(src) + ".backup")
            import shutil
            shutil.copy2(src, dst)
            print(f"  Backed up: {src} -> {dst}")
    
    # Load JSON data
    devices = []
    events = []
    
    if os.path.exists(OLD_DEVICES_FILE):
        try:
            with open(OLD_DEVICES_FILE, 'r') as f:
                data = json.load(f)
                devices = data.get('devices', [])
                events = data.get('events', [])
            print(f"  Loaded {len(devices)} devices, {len(events)} events from devices.json")
        except Exception as e:
            print(f"  Error loading devices.json: {e}")
    
    if os.path.exists(OLD_STATE_FILE):
        try:
            with open(OLD_STATE_FILE, 'r') as f:
                state = json.load(f)
                state_devices = state.get('devices', {})
                if isinstance(state_devices, dict):
                    # Convert dict to list
                    for ip, dev in state_devices.items():
                        dev['ip'] = ip
                        devices.append(dev)
                print(f"  Merged {len(state_devices)} devices from state.json")
        except Exception as e:
            print(f"  Error loading state.json: {e}")
    
    # Initialize SQLite database
    db = NetDiscoverDB()
    
    # Migrate devices
    device_count = 0
    for device in devices:
        try:
            db.upsert_device(device)
            device_count += 1
        except Exception as e:
            print(f"  Error migrating device {device.get('ip')}: {e}")
    
    print(f"  Migrated {device_count} devices to SQLite")
    
    # Migrate events
    event_count = 0
    for event in events:
        try:
            db.add_event(
                event_type=event.get('type', 'unknown'),
                ip=event.get('ip', ''),
                mac=event.get('mac', ''),
                hostname=event.get('hostname', ''),
                details=event.get('details', {})
            )
            event_count += 1
        except Exception as e:
            print(f"  Error migrating event: {e}")
    
    print(f"  Migrated {event_count} events to SQLite")
    
    db.close()
    
    print("\n✅ Migration complete!")
    print(f"   Database: /var/db/netdiscover/netdiscover.db")
    print(f"   Backups:  {BACKUP_DIR}/")
    print("\n   Old JSON files are preserved. You can delete them after verifying the migration:")
    print(f"     rm {OLD_DEVICES_FILE}")
    print(f"     rm {OLD_STATE_FILE}")


if __name__ == '__main__':
    try:
        migrate()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

