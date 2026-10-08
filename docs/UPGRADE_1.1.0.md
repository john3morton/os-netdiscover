# Upgrading to NetDiscover v1.1.0

## Overview

Version 1.1.0 introduces **SQLite database backend** with **historical tracking**. This is a major architectural change from the previous JSON-based storage.

## What's New

- ✅ **SQLite Database** - Fast, reliable, scalable storage
- ✅ **Historical Tracking** - Complete device history timeline
- ✅ **Uptime Statistics** - Track device availability over time
- ✅ **Better Performance** - Indexed queries, faster searches
- ✅ **Automatic Cleanup** - Old data purged automatically

## Upgrade Process

### Automatic Upgrade (Recommended)

When you deploy v1.1.0, the system will:

1. **Auto-create SQLite database** on first run
2. **Write to both formats** (JSON + SQLite) simultaneously
3. **Read from SQLite** (with JSON fallback)

**Your existing data remains intact** - the daemon writes to both formats during transition.

### Manual Migration (Optional)

If you want to migrate historical JSON data into SQLite:

```bash
# Run migration script
cd /usr/local/opnsense/scripts/NetDiscover
python3 migrate_to_sqlite.py
```

This will:
- ✅ Backup existing JSON files to `/var/db/netdiscover/json_backup/`
- ✅ Import all devices from `devices.json` and `state.json`
- ✅ Import all events
- ✅ Preserve all data

### Verify Migration

```bash
# Check database exists
ls -lh /var/db/netdiscover/netdiscover.db

# Check device count
sqlite3 /var/db/netdiscover/netdiscover.db "SELECT COUNT(*) FROM devices;"

# Check events count
sqlite3 /var/db/netdiscover/netdiscover.db "SELECT COUNT(*) FROM events;"

# Check history is tracking
sqlite3 /var/db/netdiscover/netdiscover.db "SELECT COUNT(*) FROM device_history;"
```

## New Features Available After Upgrade

### 1. Device History Timeline

Click any device in Inventory → **History tab** shows:
- When device was first discovered
- Every status change (up → gone, gone → back)
- Every attribute change (hostname, vendor, etc.)
- Timestamp for each event

### 2. Uptime Statistics

Click any device → **Uptime tab** shows:
- Uptime percentage (last 30 days)
- Number of status changes
- Total downtime duration

### 3. Historical Queries

Use SQLite directly for advanced queries:

```bash
# Find devices with most status changes
sqlite3 /var/db/netdiscover/netdiscover.db \
  "SELECT ip, COUNT(*) as changes FROM device_history 
   WHERE event_type='status_change' GROUP BY ip ORDER BY changes DESC LIMIT 10;"

# Find when specific device went offline
sqlite3 /var/db/netdiscover/netdiscover.db \
  "SELECT datetime(timestamp, 'unixepoch') as time, old_value, new_value 
   FROM device_history WHERE ip='192.168.1.50' AND event_type='status_change';"
```

## Database Schema

### Tables Created:

- **`devices`** - Current device inventory (replaces devices.json)
- **`device_history`** - Complete change history for all devices
- **`events`** - Recent network events (replaces events array)
- **`device_overrides`** - Custom user settings per device
- **`scan_stats`** - Performance metrics (future use)

### Automatic Cleanup:

- Events older than last 1000 are auto-deleted
- History older than 90 days is auto-purged
- Old devices (>30 days not seen) can be manually cleaned

## Rollback (If Needed)

If you need to rollback to JSON-only mode:

1. Stop the service:
   ```bash
   service netdiscoverd stop
   ```

2. Restore JSON backup (if you migrated):
   ```bash
   cp /var/db/netdiscover/json_backup/*.json /var/db/netdiscover/
   ```

3. Downgrade plugin to v1.0.x

4. Restart service:
   ```bash
   service netdiscover start
   ```

The JSON files are preserved during the transition, so rollback is safe.

## Performance Impact

**Positive:**
- ✅ Faster queries (indexed)
- ✅ Less memory usage (no full JSON parse)
- ✅ Better concurrency (SQLite locking)

**Minimal:**
- Slightly larger disk usage (~2-3x JSON size)
- Additional CPU for history tracking (negligible)

## Troubleshooting

### Database not created

```bash
# Check permissions
ls -ld /var/db/netdiscover/
# Should be writable by netdiscover daemon user

# Manually initialize
cd /usr/local/opnsense/scripts/NetDiscover
python3 -c "from db_helper import NetDiscoverDB; NetDiscoverDB()"
```

### Widget/API showing old data

```bash
# Force refresh
service netdiscoverd restart
configctl webgui restart
```

### Check daemon logs

```bash
tail -f /var/db/netdiscover/netdiscoverd.log
```

Look for "SQLite database initialized" message.

## Questions?

See ROADMAP.md for future enhancements and CHANGELOG.md for complete change list.

