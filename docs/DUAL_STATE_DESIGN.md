# Dual-State Device Status System (v1.5.0)

## Architecture

Devices have **TWO independent properties**:

### 1. Connection State (Required, Mutually Exclusive)
- **online** - Currently reachable
- **offline** - Not seen for 2+ scan cycles
- **missing** - Not seen for 30 days
- **gone** - Not seen for 60 days (30 days of missing)

### 2. Lifecycle Flags (Optional, Can Combine)
- **new** - First discovered (24h or until reviewed)
- **changed** - Attributes changed (24h or until reviewed)  
- **back** - Just returned online (24h or until reviewed)

## Examples

### Valid Combinations:
- **"new, online"** - Just discovered and currently reachable
- **"new, offline"** - Just discovered but not responding now
- **"changed, online"** - Hostname changed and device is online
- **"changed, offline"** - MAC changed but device is offline now
- **"back, online"** - Just came back from being offline
- **"online"** - Normal online device (no special flags)
- **"offline"** - Currently offline (no special flags)
- **"missing"** - Long-term offline (30 days)
- **"gone"** - Permanently offline (60 days)

### Invalid Combinations:
- ❌ Can't be both "online" AND "offline"
- ❌ Can't be both "missing" AND "online"
- ✅ CAN be "new" AND "offline"
- ✅ CAN be "changed" AND "online"

## Storage

### Database Fields:
```sql
-- Connection state (required)
connection_state TEXT NOT NULL DEFAULT 'online'  -- online|offline|missing|gone

-- Lifecycle flags (optional, comma-separated)
lifecycle_flags TEXT  -- new,changed,back (or empty)

-- Backward compatibility
status TEXT  -- Computed display: "new, online" or "offline" or "changed, online"
```

### Display:
```
Status Column: "new, online"
  ├── Flag: "new" (orange badge)
  ├── Separator: ","
  └── State: "online" (green dot)
```

## Timing Rules

### Connection State Transitions:

```
online → (not seen 2 cycles) → offline
offline → (not seen 30 days) → missing  
missing → (not seen 30 more days) → gone (60 days total)

Any → (seen again) → online
```

### Lifecycle Flag Expiration:

```
"new" flag → (reviewed OR 24h) → removed
"changed" flag → (reviewed OR 24h) → removed
"back" flag → (reviewed OR 24h) → removed
```

### When Flags Are Set:

- **"new"**: First discovery
- **"changed"**: Hostname, MAC, vendor, manufacturer, model, or interface changes
- **"back"**: Connection state transitions from offline/missing/gone → online

## Thresholds

```python
OFFLINE_THRESHOLD = scan_interval * 2  # 2 cycles
MISSING_THRESHOLD = 2592000  # 30 days
GONE_THRESHOLD = 5184000     # 60 days (30 + 30)
FLAG_EXPIRY = 86400          # 24 hours
NO_AUTO_PRUNE = True         # Never auto-delete
```

## UI Display

### Status Column:
```
┌─────────────────────────┐
│ Status                  │
├─────────────────────────┤
│ 🟠 new, 🟢 online       │ ← Badge + dot
│ 🟢 online               │ ← Just dot
│ 🔷 changed, 🟢 online   │ ← Badge + dot
│ 🟡 offline              │ ← Just dot
│ 🔴 missing              │ ← Just dot
│ ⚫ gone                 │ ← Just dot
└─────────────────────────┘
```

### Filter Buttons:
```
[All] [New] [Changed] [Back] | [Online] [Offline] [Missing] [Gone]
 └─── Lifecycle Flags ────┘    └─── Connection States ───┘
```

### Timeline Graph:
```
Connection state shown as bar segments:
████████░░░░████████████
└online┘    └─online──┘
     (offline)

Lifecycle flags shown as markers above bar:
  ◆     ◆
  new   back
```

## Implementation Changes

### Database:
- Add `connection_state` column
- Add `lifecycle_flags` column
- Compute `status` as display string

### Daemon:
- Update connection state based on timing
- Manage lifecycle flags separately
- Combine for display

### UI:
- Parse compound status
- Display badges for flags
- Display dots for connection state
- Filter by either dimension

## Migration

Old status → New representation:
- "new" → connection_state="online", flags="new"
- "up" → connection_state="online", flags=""
- "changed" → connection_state="online", flags="changed"
- "gone" → connection_state="gone", flags=""
- "offline" → connection_state="offline", flags=""

## Benefits

✅ **Clearer semantics** - Two independent concepts  
✅ **More accurate** - Can be new AND offline simultaneously  
✅ **Better filtering** - Filter by lifecycle OR connection  
✅ **Richer information** - See both dimensions at once  
✅ **No auto-prune** - Devices stay until manually deleted  
✅ **30-day grace** - "missing" before "gone"  

