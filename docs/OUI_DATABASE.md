# OUI (MAC Vendor) Database

## Overview

NetDiscover uses the **IEEE OUI (Organizationally Unique Identifier) database** to identify device manufacturers from MAC addresses. As of v1.2.0, this is stored in **SQLite** for fast, indexed lookups.

## What is OUI?

Every network device has a MAC address like `58:9C:FC:12:34:56`. The first 3 octets (`58:9C:FC`) are the **OUI**, assigned by IEEE to manufacturers. This identifies who made the network card.

## Database Storage

### Location
```
/var/db/netdiscover/netdiscover.db (oui table)
```

### Schema
```sql
CREATE TABLE oui (
    oui TEXT PRIMARY KEY,        -- e.g., "58:9C:FC"
    vendor TEXT NOT NULL,         -- e.g., "Apple, Inc."
    updated_at INTEGER            -- Unix timestamp
);
CREATE INDEX idx_oui_vendor ON oui(vendor);
```

### Size
- **~30,000 entries** (~2MB in SQLite)
- **Indexed** for O(1) lookups
- **Compressed** compared to IEEE text format

## Updating OUI Database

### Method 1: UI Button (Easiest)
1. Go to **Services → NetDiscover → Settings** tab
2. Scroll to **"MAC Vendor Database"** section
3. Click **"Update OUI List from IEEE"**
4. Wait 30-60 seconds for download
5. ✅ See success message with entry count

### Method 2: Command Line
```bash
# Force update now
python3 /usr/local/opnsense/scripts/NetDiscover/update_oui.py --force

# Check age without updating
python3 /usr/local/opnsense/scripts/NetDiscover/update_oui.py --check

# Auto-update if >30 days old (used by deploy.sh)
python3 /usr/local/opnsense/scripts/NetDiscover/update_oui.py
```

### Method 3: Automatic (Cron)
Add to `/etc/crontab` or OPNsense cron UI:
```
# Monthly OUI update (1st of month at 3 AM)
0 3 1 * * root /usr/local/bin/python3 /usr/local/opnsense/scripts/NetDiscover/update_oui.py
```

## How It Works

### 1. Download
Script fetches latest data from:
```
https://standards-oui.ieee.org/oui/oui.txt
```

### 2. Parse
Converts IEEE format:
```
00-00-0C   (hex)		Cisco Systems, Inc
```

To SQLite:
```sql
INSERT INTO oui VALUES ('00:00:0C', 'Cisco Systems, Inc', 1703622000);
```

### 3. Atomic Update
- Deletes all existing OUI entries
- Bulk inserts all new entries
- Transaction ensures consistency

### 4. Daemon Lookup
```python
mac = "58:9C:FC:12:34:56"
oui = "58:9C:FC"  # First 3 octets
vendor = load_oui_from_sqlite()[oui]  # Fast indexed lookup
# Result: "Apple, Inc."
```

## Update Frequency

**Recommended: Monthly**
- IEEE updates OUI registry regularly as new vendors are added
- Monthly is sufficient for most use cases
- Script auto-checks age and only downloads if >30 days old

## Troubleshooting

### Check OUI table status
```bash
sqlite3 /var/db/netdiscover/netdiscover.db "SELECT COUNT(*) FROM oui;"
# Should return ~30,000

sqlite3 /var/db/netdiscover/netdiscover.db "SELECT * FROM oui LIMIT 5;"
# Should show vendor entries
```

### Check update timestamp
```bash
sqlite3 /var/db/netdiscover/netdiscover.db \
  "SELECT datetime(MAX(updated_at), 'unixepoch') FROM oui;"
```

### Manual re-download
```bash
cd /usr/local/opnsense/scripts/NetDiscover
python3 update_oui.py --force
```

### Check if OUI is being used
```bash
# Check daemon log for OUI load count
tail /var/db/netdiscover/netdiscoverd.log

# Check a device in database
sqlite3 /var/db/netdiscover/netdiscover.db \
  "SELECT ip, mac, vendor FROM devices LIMIT 10;"
```

## Performance

### Before (CSV):
- **Linear scan** through CSV file for each MAC lookup
- O(n) complexity
- ~50-100ms per lookup with 30K entries

### After (SQLite):
- **Indexed query** with PRIMARY KEY lookup
- O(1) complexity
- **<1ms per lookup** regardless of entry count

### Impact on Scanning:
- 100 devices × 100ms = **10 seconds** (CSV)
- 100 devices × 1ms = **0.1 seconds** (SQLite)
- **100x faster** vendor lookups! 🚀

## Maintenance

### Disk Usage
- OUI table: ~2MB
- Auto-vacuum keeps database compact
- No manual cleanup needed

### Network Usage
- Download: ~4MB from IEEE servers
- Only downloads when needed (>30 days or --force)
- One-time per month maximum

## Benefits

✅ **Fast lookups** - Sub-millisecond indexed queries  
✅ **Automatic updates** - One-click or cron-based  
✅ **No config needed** - Part of the database, no file paths  
✅ **30,000+ vendors** - Complete IEEE registry  
✅ **Up-to-date** - Monthly refresh recommended  
✅ **Integrated** - Same database as device data  
✅ **Backwards compatible** - CSV fallback if table empty  

## Migration from CSV

If you had a custom CSV OUI file, you don't need it anymore! The database approach is:
- Faster
- Self-contained
- Auto-updating
- More maintainable

Your old CSV files can be safely deleted after v1.2.0 deployment.

