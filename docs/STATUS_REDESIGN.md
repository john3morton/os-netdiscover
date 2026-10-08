# Status Terminology Redesign (v1.4.0)

## Current Problem

**Current status meanings are confusing:**
- "changed" = device came back online OR something changed
- "gone" = not seen in last scan cycle (could be 5 minutes!)
- Too aggressive - marks devices gone too quickly
- Can't distinguish between "back online" and "attribute changed"

## Proposed New Status System

### Status Values:

| Status | Meaning | Duration | Color |
|--------|---------|----------|-------|
| **new** | First time discovered | Until viewed or 48h | 🟠 Orange |
| **up** | Online and stable | Default active state | 🟢 Green |
| **back** | Was offline, now back | First scan after return | 🔵 Blue |
| **changed** | Attribute changed (hostname/MAC/etc) | Until next scan | 🔷 Light Blue |
| **offline** | Not seen recently | 2 scan cycles - 14 days | 🟡 Yellow |
| **gone** | Not seen for 14+ days | After 14 days offline | 🔴 Red |

### Status Transitions:

```
┌──────┐
│ new  │ First discovery
└──┬───┘
   │ (user views OR 24h)
   ↓
┌──────┐
│  up  │ Normal online state
└──┬───┘
   │
   ├─→ (attribute changes) ──→ ┌─────────┐
   │                            │ changed │ → (next scan) → back to "up"
   │                            └─────────┘
   │
   ├─→ (not seen 30min) ────→ ┌─────────┐
   │                           │ offline │
   │                           └────┬────┘
   │                                │ (seen again)
   │                                ↓
   │                           ┌────────┐
   │                           │  back  │ → (next scan) → "up"
   │                           └────────┘
   │                                │ (not seen 14 days)
   │                                ↓
   └────────────────────────→ ┌──────┐
                               │ gone │ Permanent until rediscovered
                               └──────┘
```

### Rules (v1.4.1):

1. **"new"** → "up" after user views device OR **48 hours**
2. **"up"** → "offline" if not seen for **2 consecutive scan cycles** (dynamic)
3. **"offline"** → "back" when seen again
4. **"back"** → "up" on next scan (transient state)
5. **"offline"** → "gone" after 14 days
6. **"gone"** → "new" if rediscovered (was truly gone, now back)
7. **Any status** → "changed" if hostname/MAC/vendor/model changes
8. **"changed"** → previous status on next scan (transient)

### Dynamic Offline Threshold:

**Formula:** `offline_threshold = scan_interval × 2`

**Examples:**
- Scan interval = 5 minutes → Offline after **10 minutes**
- Scan interval = 2 hours → Offline after **4 hours**
- Scan interval = 5 hours → Offline after **10 hours**

**Why this is better:**
- Adapts to your network's scan frequency
- Faster scans = faster offline detection
- Slower scans = more tolerance (prevents false positives)
- No magic numbers - relative to your configuration

### What Triggers "changed":

**Changes that set "changed" status:**
- Hostname changed
- MAC address changed (rare but possible)
- Vendor changed (OUI update)
- Manufacturer changed (SSDP update)
- Model changed (SSDP update)
- Interface changed (moved to different network)

**Does NOT trigger "changed":**
- Coming back online (that's "back")
- Going offline (that's "offline")
- Normal scan updates (stays "up")

---

## Timeline Graph Visualization

### Mockup:

```
Device History: 192.168.1.50

Timeline (Last 30 Days):
┌─────────────────────────────────────────────────────────────┐
│ Dec 1        Dec 10         Dec 20         Dec 26 (now)     │
├─────────────────────────────────────────────────────────────┤
│ ███████████░░░░░██████████████████████████░░░████████████  │
│ └─ up ─────┘    └─── offline ──────┘         └── up ───┘   │
│          ↑ (offline 8h)              ↑ (back)              │
└─────────────────────────────────────────────────────────────┘

Legend: █ Online ░ Offline

Uptime: 92.3% over last 30 days
```

### Implementation:

**HTML Structure:**
```html
<div class="timeline-container" style="height:60px;">
  <div class="timeline-bar" style="display:flex;">
    <div class="up-segment" style="width:60%;background:#5cb85c;"></div>
    <div class="offline-segment" style="width:10%;background:#f0ad4e;"></div>
    <div class="up-segment" style="width:30%;background:#5cb85c;"></div>
  </div>
  <div class="timeline-labels">
    <span>Dec 1</span>
    <span>Dec 15</span>
    <span>Dec 26</span>
  </div>
</div>
```

**Data Source:**
Query device_history for status_change events, build timeline segments.

---

## Migration Path

**For existing deployments:**
- One-time status normalization on daemon start
- Convert old "changed" to "up" or "back" based on context
- Convert old "gone" to "offline" if <14 days, keep "gone" if >14 days

---

## Would You Like Me To Implement This?

I can implement:
1. **Status redesign** (2-3 hours) - Better status logic in daemon
2. **Timeline graph** (2-3 hours) - Visual uptime history
3. **Both** (4-6 hours total)

The status redesign is a **major improvement** - much clearer and more useful! The timeline graph would make history beautiful and easy to understand at a glance.

Should I proceed with implementing both?

