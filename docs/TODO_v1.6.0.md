# NetDiscover v1.6.0 Implementation Tasks

## Status: ✅ COMPLETED (v2.0.6)

All v1.6.0 features have been implemented and are in production!

### Completed ✅

#### Core Features (v1.5.x)
- ✅ v1.5.1 Dual-state architecture
- ✅ v1.5.1 DHCP type detection  
- ✅ v1.5.1 Widget deduplication
- ✅ v1.5.1 Timeline visualization

#### High Priority Features (v1.6.0 - v2.0.x)

#### 1. Wireshark Model Hints Extraction ✅ (v1.6.2)
- ✅ Update `update_wireshark_manuf.py` to extract model information from extended MAC entries
- ✅ Store model hints in separate field (oui_models table)
- ✅ Backfill model field when OUI updates

#### 2. Override vs Discovered Display ✅ (v1.6.0)
- ✅ Add discovered_manufacturer, discovered_model fields to schema
- ✅ Show overrides in table (primary)
- ✅ Show discovered values greyed out in detail modal
- ✅ Clear distinction between user-set and auto-discovered

#### 3. Operating System Detection ✅ (v1.6.0-v1.6.2)
- ✅ Add os_name and os_version fields
- ✅ Extract from banners (SSH, HTTP Server headers)
- ✅ Extract from SNMP sysDescr
- ✅ Pattern matching from hostname
- ✅ Show in detail modal
- ✅ OS column in inventory table (sortable/hideable)

#### 4. Exhaustive Port Scan ✅ (v1.6.0-v1.6.1)
- ✅ Add "Port Scan" button to device detail modal
- ✅ Create `/api/netdiscover/scan/ports` endpoint
- ✅ Scan all 65535 ports (or configurable range)
- ✅ Store results in device record (exhaustive_ports field)
- ✅ Show scan progress with status messages
- ✅ Remember until next automatic scan
- ✅ Display in inventory table (v2.0.4)

#### 5. Detail Modal Enhancements
**Layout:**
```
Current Tab:
┌────────────────────────────────┐
│ IP: 192.168.1.50              │
│ MAC: aa:bb:cc:dd:ee:ff        │
│ Hostname: printer             │
│                               │
│ Manufacturer:                 │
│   User: HP Inc. ✏️           │
│   Discovered: Hewlett-Packard│
│                               │
│ Model:                        │
│   User: LaserJet Pro M428 ✏️ │
│   Discovered: M428fdw        │
│                               │
│ Operating System:             │
│   Name: Debian Linux         │
│   Version: 10.2              │
│                               │
│ Open Ports: [Port Scan]      │
│   22, 80, 443, 515, 631, 9100│
│   Last scan: 10 minutes ago  │
└────────────────────────────────┘
```

### Future Enhancements (v2.1+)

See ROADMAP.md for planned features. Key areas for future development:

#### Advanced Port Scanning Enhancements
- [ ] Configurable port ranges via UI (API supports custom ranges)
- [ ] Service detection per port (identify service name)
- [ ] Enhanced banner grabbing on all ports
- [ ] Save scan history (timeline of scans per device)

#### Enhanced Wireshark Integration
- [ ] Extract device categories from OUI database
- [ ] Parse vendor short names
- [ ] Model disambiguation (when multiple models match)

### Implementation Notes

**Wireshark Model Hints:**
Extended MAC entries in Wireshark format:
```
00:00:0C:07:AC/40	Cisco		Cisco IOS Software
```
The `/40` indicates a longer prefix with device-specific info.

**OS Detection Sources:**
1. SSH banner: `SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.1` → Ubuntu 20.04
2. HTTP Server: `Apache/2.4.41 (Ubuntu)` → Ubuntu
3. SNMP sysDescr: Full OS info
4. Hostname patterns: `debian-server` → Debian

**Port Scan Considerations:**
- Full 65K scan takes 3-5 minutes
- Use async/threaded scanning
- Show progress bar
- Configurable timeout per port
- Store in `exhaustive_ports` field separate from `open_ports`

**Override Precedence:**
```
Display in table: User override OR discovered
Display in detail: 
  - User override (if set) - highlighted/editable
  - Discovered value (always shown, greyed out)
```

---

## Implementation Summary

**Final Version:** v2.0.6 (Dec 2025)
**Version Progress:** v1.0.0 → v2.0.6
**Major Features Delivered:**
- ✅ SQLite backend with historical tracking
- ✅ Advanced device fingerprinting (6+ methods)
- ✅ Dual-state status architecture (lifecycle flags + connection state)
- ✅ Interactive timeline visualization
- ✅ DHCP type detection (static/reserved/dynamic)
- ✅ Resizable & sortable columns
- ✅ Bulk operations (tag, clear overrides)
- ✅ Device delete with confirmation
- ✅ Exhaustive port scanning (1-65535)
- ✅ Override vs discovered field tracking
- ✅ Operating system detection
- ✅ Wireshark model hints
- ✅ WiFi AP topology detection (v2.0.x)
- ✅ Recent Changes filtering (latest per device)
- ✅ Clickable event rows

**Status:** Production ready, all planned v1.6.0 features complete!

**Next Steps:** See ROADMAP.md for v2.1+ feature planning.

