# NetDiscover v1.5.0 - Dual-State Architecture

## 🎉 Major Architectural Release

Version 1.5.0 introduces a **revolutionary two-dimensional status system** that separates connection state from lifecycle events, providing much clearer device monitoring.

---

## The Problem with Single-State Status

**Old System (v1.4.x):**
- Status could be: new, up, back, changed, offline, gone
- **Problem:** Can't be "new" AND "offline" simultaneously
- **Confusion:** "changed" meant online OR attribute changed
- **Too aggressive:** "gone" after just 14 days

---

## The Solution: Dual-State System

**Two Independent Dimensions:**

### 1. Connection State (Always One):
| State | Meaning | Timing | Color |
|-------|---------|--------|-------|
| **online** | Currently reachable | Default | 🟢 Green |
| **offline** | Not responding | 2+ scan cycles | 🟡 Yellow |
| **missing** | Long-term offline | 30 days | 🟠 Dark Orange |
| **gone** | Permanently offline | 60 days | 🔴 Red |

### 2. Lifecycle Flags (Zero or More):
| Flag | Meaning | Duration | Color |
|------|---------|----------|-------|
| **new** | First discovered | 24h or reviewed | 🟠 Orange |
| **changed** | Attributes modified | 24h or reviewed | 🔷 Lt Blue |
| **back** | Just returned | 24h or reviewed | 🔵 Cyan |

---

## Now You Can Have:

✅ **"new, offline"** - Just discovered but not responding  
✅ **"new, online"** - Just discovered and reachable  
✅ **"changed, online"** - Hostname changed on active device  
✅ **"changed, offline"** - MAC changed while device is offline  
✅ **"back, online"** - Just came back from being offline  
✅ **"online"** - Normal device (no special flags)  
✅ **"missing"** - Been offline 30 days  

---

## UI Display

### Table Columns:

```
☑ | 👁️ | 🏴 | ● | IP | MAC | Hostname | ...
         ↑    ↑
      Flags Connection
```

### Flags Column (🏴):
- Shows 0-3 colored balls (12px each)
- 🟠 Orange ball = "new"
- 🔷 Blue ball = "changed"
- 🔵 Cyan ball = "back"
- Empty if no flags
- Hover for explanation

### Connection Column (●):
- Shows 1 colored ball (12px)
- 🟢 Green = "online"
- 🟡 Yellow = "offline"
- 🟠 Dark orange = "missing"
- 🔴 Red = "gone"
- Always present
- Hover for explanation

### Examples:

```
🟠 🟢  = new, online
🔷 🟢  = changed, online
🔵 🟢  = back, online
   🟡  = offline (no flags)
   🟠  = missing (30 days)
   🔴  = gone (60 days)
🟠🔷 🟢 = new AND changed, online (both flags!)
```

---

## Filter System

### Two Independent Filter Groups:

**Lifecycle Filters:**
```
[All] [New] [Changed] [Back]
```

**Connection Filters:**
```
[All] [Online] [Offline] [Missing] [Gone]
```

**Can Combine:**
- Filter by "New" → All new devices (regardless if online/offline)
- Filter by "Offline" → All offline devices (regardless of flags)
- Filter by "New" AND "Offline" → New devices that are offline

---

## Timing Rules

| Threshold | Value | Calculation |
|-----------|-------|-------------|
| **Offline** | Dynamic | **2 × scan_interval** |
| **Missing** | Fixed | **30 days** |
| **Gone** | Fixed | **60 days** (30 days of missing) |
| **Flag Expiry** | Fixed | **24 hours or reviewed** |
| **Auto-Prune** | **NEVER** | Devices stay forever |

### With Your 120s Scan Interval:
- Offline after: **240 seconds (4 minutes)**
- Missing after: **30 days**
- Gone after: **60 days**
- Flags clear: **24 hours or when you view device**

---

## Status Legend Button

**New "Legend" button in toolbar:**
- Click to see color code explanation
- Modal with two sections:
  - Lifecycle Flags (🏴)
  - Connection States (●)
- Example combinations
- Always available for reference

---

## Database Schema

### New Columns:
```sql
connection_state TEXT DEFAULT 'online'
lifecycle_flags TEXT  -- Comma-separated
flag_set_time INTEGER
flag_acknowledged INTEGER DEFAULT 0
```

### Removed:
```sql
new_acknowledged  -- Replaced by flag_acknowledged
```

### Auto-Migration:

Daemon automatically migrates old data on first run:
```sql
Old "new" → connection_state="online", flags="new"
Old "changed" → connection_state="online", flags="changed"
Old "offline" → connection_state="offline", flags=""
Old "gone" → connection_state="gone", flags=""
```

---

## No Auto-Prune!

**Important Change:**
- Devices are **NEVER** automatically deleted
- "gone" devices remain for historical record
- User must manually delete unwanted devices
- Prevents surprise data loss

---

## API Changes

### New Fields Returned:
- `connection_state` - online|offline|missing|gone
- `lifecycle_flags` - Comma-separated: new,changed,back
- `flag_set_time` - When flags were set
- `flag_acknowledged` - Whether user reviewed device
- `status` - Computed display string (for compatibility)

### Acknowledge Endpoint:
- Clears ALL lifecycle flags
- Sets flag_acknowledged = 1
- Recalculates status display

---

## Deploy

```bash
./deploy.sh
```

**After deployment:**

1. **Check daemon started successfully:**
   ```bash
   tail /var/db/netdiscover/startup.log
   # Should show: "✓ Daemon ready - entering main loop"
   ```

2. **Wait for first scan** (2 minutes with 120s interval)

3. **Refresh browser** - See new dual-column layout!

4. **Click "Legend" button** - Understand color codes

5. **Try filters:**
   - Click "New" → See new devices
   - Click "Online" → See online devices
   - Click both → See new AND online devices

6. **View a device:**
   - Click any "new" device
   - See detail modal
   - Flag automatically clears on next scan!

---

## Visual Example

### Table Display:

```
┌──┬───┬────┬────┬─────────────┬──────────┬──────────┐
│☑│👁️│🏴 │ ● │ IP          │ Hostname │ ...      │
├──┼───┼────┼────┼─────────────┼──────────┼──────────┤
│☐│👁️│🟠  │🟢  │192.168.1.10 │ iPhone   │ ...      │ ← new, online
│☐│👁️│🔷  │🟢  │192.168.1.20 │ Printer  │ ...      │ ← changed, online
│☐│👁️│    │🟡  │192.168.1.30 │ Camera   │ ...      │ ← offline
│☐│👁️│🔵  │🟢  │192.168.1.40 │ NAS      │ ...      │ ← back, online
│☐│👁️│🟠🔷│🟢  │192.168.1.50 │ Server   │ ...      │ ← new+changed, online!
│☐│👁️│    │🟠  │192.168.1.60 │ Switch   │ ...      │ ← missing (30d)
└──┴───┴────┴────┴─────────────┴──────────┴──────────┘
```

---

## Benefits Summary

✅ **Crystal clear** - Connection vs lifecycle separated  
✅ **More accurate** - Can be new AND offline simultaneously  
✅ **Better filtering** - Filter by either dimension  
✅ **Compact display** - Just colored balls, no text clutter  
✅ **Informative tooltips** - Hover to understand  
✅ **No auto-deletion** - Devices stay until you remove them  
✅ **30-day grace** - "missing" before "gone"  
✅ **User-driven** - Flags clear when you review  
✅ **Adaptive offline** - Works with any scan interval  

---

**v1.5.0 is a major architectural improvement!** Device status is now intuitive, clear, and powerful. 🚀

