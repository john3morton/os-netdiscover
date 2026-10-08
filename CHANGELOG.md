# Changelog

## 2.1.1 - Dashboard Counter Fixes
- **New/Changed counts**: Use token-matched `lifecycle_flags` only (no longer `status LIKE '%new%'` which over-counted after migration).
- **Up count**: Uses `connection_state = online` only (removed `OR last_seen` inflation).
- **Stale "new" flags**: Cleared on daemon start for devices first seen > 48h ago (migration leftover).

## 2.1.0 - MAC Identity + Hardening + Expansion
- **MAC primary key**: Devices are identified by MAC (synthetic `ip:<addr>` only when MAC unknown). Automatic DB migration dedupes prior IP-keyed clones.
- **API/UI keyed by MAC**: Overrides, acknowledge, history, delete, and bulk actions prefer MAC; IP retained for scans and display.
- **IP history in device details**: Current tab shows prior IP changes; History tab queries by MAC so trails survive DHCP churn.
- **Overrides SQLite fixed**: `ON CONFLICT(mac)` (was silently failing after MAC migration).
- **Dashboard/uptime fixed**: Counts use `connection_state` / `lifecycle_flags` instead of composite `status` strings.
- **Passive discovery default**: Blank / `_LAN_` means all interfaces (no longer silently disables SSDP/mDNS/etc.).
- **Removed legacy 600s "gone" aging** that fought the dual-state engine.
- **Daemon rehydrates from SQLite** on startup so offline→missing→gone continues across restarts.
- **XSS hardening**: Device detail/history interpolations escaped in JS.
- **Service OUI actions**: UI calls use POST.
- **Webhook alerts** (optional): `/var/db/netdiscover/alerts.json` — enable + `webhook_url` + event list.
- **Auto-tag rules** (optional): `/var/db/netdiscover/auto_tags.json` — match vendor/hostname/subnet/type and add tags.

## 2.0.14 - Executable Bit Fix
- **rc.d / scripts**: Source files now carry the git executable bit so `make package` installs `netdiscoverd` and Python helpers as mode 755.
- Fixes `service netdiscoverd` reporting “does not exist … or is not executable” after a fresh install on OPNsense 26.7.

## 2.0.13 - OPNsense 26.7 Packaging
- **Target ABI**: Ready for OPNsense 26.7.x (Python 3.13 / FreeBSD 15.1).
- **Standard Package Name**: Builds as `os-netdiscover` (removed custom `PLUGIN_PREFIX=opnsense`).
- **Python Dependency**: Dropped hardcoded `python311`; uses system `python3` link provided by OPNsense core.
- **Docs**: README and install guide updated for 26.7+ and the new package name.

## 2.0.12 - Pre-Scan ARP Verification
- **ARP Check Before Port Scan**: Verifies device is reachable via ARP before starting port scan.
- **Ping Fallback**: If not in ARP, sends ping to populate ARP table, then rechecks.
- **Offline Detection**: If device still not in ARP after ping, marks device as offline and aborts scan.
- **Status Update**: Automatically updates device connection_state to "offline" in database.
- **User Feedback**: Shows warning message explaining device is offline, not just generic scan failure.
- **Auto-Refresh**: Detail view and inventory table automatically update to show offline status.
- **Prevents Wasted Time**: Avoids 5-10 minute port scans on unreachable devices.
- **Smart Alert**: "Device Offline" warning with suggestion to try again when device is back online.
- Use case: User tries to scan device that's powered off → immediate feedback instead of long timeout.

## 2.0.11 - DHCP Lease Detection Logic Change
- **DHCP Lease ≠ Device Up**: DHCP leases no longer mark devices as "online" by themselves.
- **ARP-Based Detection**: Only ARP table entries indicate a device is actually reachable/up.
- **Discovery Still Works**: DHCP leases still used for device discovery, hostname, MAC tracking.
- **More Accurate Status**: Prevents devices with stale DHCP leases from appearing online.
- **Offline Detection**: Devices will go offline if not seen in ARP for 2 scan cycles (10 minutes).
- **Use Case**: Device gets DHCP lease but is powered off → now correctly shows as offline.
- **Technical**: `merge()` called with `up=False` for dnsmasq, IP not added to `seen_ips` set.
- **Connection State**: Based on ARP presence only, not DHCP lease existence.

## 2.0.10 - Modal Display Fix
- **Modal Context Fix**: Fixed device detail modal showing in wrong tab when opened from Recent Changes.
- **DOM Reparenting**: Modals now automatically append to document body when opened.
- **Tab Independence**: Modals display properly regardless of which tab is active.
- **Edit Modal Fixed**: Applied same fix to edit device modal.
- **Bootstrap Pattern**: Uses standard Bootstrap modal best practice for dynamic content.
- Issue: Opening device detail from Recent Changes tab, then switching to Inventory tab showed modal in wrong context.
- Solution: JavaScript moves modal to body element on open, escaping tab-pane containers.

## 2.0.9 - Device Categories
- **Device Category Classification**: Automatically categorizes devices into 9 broad categories.
- **Categories**: Network, Computer, Mobile, Printer, Storage, Camera, Media, IoT, Other.
- **Icon Filter Buttons**: Quick-filter toolbar with icons for each category (sitemap, desktop, mobile, print, etc.).
- **Auto-Classification**: Uses existing device_type field to determine category automatically.
- **Database Column**: Added device_category column to devices table with auto-migration.
- **Persistent Filter**: Category filter preference saved in localStorage.
- **Combined Filtering**: Works alongside lifecycle flags and connection state filters.
- **Count Display**: Shows active category filter in status bar.
- **Backend Logic**: Category assigned during device merge based on device_type patterns.
- Use case: Quickly filter to show only "Network" devices (routers/switches/APs), or only "IoT" devices, etc.

## 2.0.8 - Service Name Mapping
- **Port Service Names**: Open ports now display with service names (e.g., "80/HTTP", "443/HTTPS", "22/SSH").
- **Common Services**: Maps 40+ common ports including web, mail, database, remote access, and printer services.
- **Inventory Table**: Service names shown in Open Ports column for quick identification.
- **Detail Modal**: Enhanced port display with service names in device details.
- **Scan Results**: Port scan completion shows service names for discovered ports.
- **Better Readability**: Format like "22/SSH, 80/HTTP, 443/HTTPS" instead of just "22, 80, 443".
- **Fallback Display**: Unknown ports show as just port number (no service name clutter).
- Use case: Instantly identify what services are running without memorizing port numbers (e.g., see "3389/RDP" instead of just "3389").

## 2.0.7 - Configurable Port Scan Ranges
- **Port Range Selector**: Added dropdown to choose scan range before running port scan.
- **Preset Ranges**: Quick options for top 1000 ports (fast), top 10K ports, or all 65535 ports.
- **Custom Range**: Option to specify custom start/end ports (e.g., 8000-9000).
- **Smart Validation**: Validates port range (1-65535) and ensures start ≤ end.
- **Time Estimates**: Shows estimated scan time based on port count (30s for 1K, 5-10min for 65K).
- **Better UX**: Confirmation dialog shows range details and port count before scanning.
- **Visual Feedback**: Disables controls during scan, shows port count in progress message.
- Use case: Scan only relevant ports (e.g., 80-443 for web, 20-25 for FTP/SSH) instead of always scanning all 65K ports.

## 2.0.6 - Recent Changes Enhancements
- **Latest Per Device Filter**: Added option to filter Recent Changes to show only the most recent event per device.
- **Toggle Buttons**: "All Events" vs "Latest Per Device" buttons on Recent Changes tab.
- **Smart Grouping**: Groups events by IP address and shows only the latest timestamp per device.
- **Persistent State**: Filter preference saved in localStorage and restored on page reload.
- **Count Display**: Shows how many devices/events are displayed with current filter.
- **Clickable Rows**: Click any event row to open the device detail modal (same as Inventory tab).
- **Auto-Load**: Automatically loads inventory data if needed when clicking from Recent Changes tab.
- **Visual Feedback**: Hover effect on clickable rows to indicate interactivity.
- Use case: Quickly see the current status of all devices without scanning through duplicate events, and view full details with a single click.

## 2.0.4 - Exhaustive Ports in Table
- **Exhaustive Ports Show in Table**: Open Ports column now displays exhaustive scan results if available.
- **Smart Fallback**: Shows exhaustive_ports (full 65K scan) if exists, otherwise shows open_ports (quick scan).
- **Priority to Detail**: User-initiated exhaustive scans take precedence over automatic quick scans.
- **Combined Display**: After running port scan on device, those results appear in inventory table.
- **Consistent Data**: Table and detail modal now show same port information.
- Use case: Run exhaustive scan on critical devices, see full port list in table without opening detail modal.

## 2.0.3 - CRITICAL FIX: Device Edit Save
- **CRITICAL FIX**: Fixed "Unexpected error" when saving device edits.
- **Root Cause**: device_overrides table missing 'os' column, SQL prepare() failed.
- **Fix**: OverridesController now checks for 'os' column and adds if missing before save.
- **Safety**: Added check for successful prepare() before executing query.
- **Graceful Degradation**: Continues to JSON fallback if SQLite fails.
- Device edits now save successfully with all fields including OS override.

## 2.0.2 - Syslog-Based AP Detection (Consumer AP Support!)

### WiFi AP Detection via Syslog Parsing:
- **Works WITHOUT SNMP!** Parses OPNsense syslogs for WiFi client association messages.
- **Zero Configuration**: No SNMP setup needed on APs - works out of the box!
- **Multi-Vendor Support**: Recognizes log formats from:
  - Ubiquiti UniFi (all models)
  - TP-Link Omada
  - OpenWrt / DD-WRT
  - MikroTik (RouterOS)
  - AsusWRT / Merlin firmware
  - Generic hostapd
- **Dual Method**: Tries syslog first, falls back to SNMP if enabled.
- **Last 24 Hours**: Parses last 24 hours of logs for associations.
- **Most Recent Wins**: If device appears on multiple APs, uses most recent association.
- **Automatic AP Resolution**: Maps AP identifiers from logs to actual AP IPs/hostnames.

### Log Pattern Matching:
**Recognizes patterns like:**
```
hostapd: STA aa:bb:cc:dd:ee:ff associated
Client aa:bb:cc:dd:ee:ff connected to AP-Living
WLAN access accepted: aa:bb:cc:dd:ee:ff
```

### Syslog Locations Checked:
- `/var/log/messages`
- `/var/log/syslog`
- `/var/log/system.log`
- Rotated logs (`.0`, `.1`)

### How It Works:
1. Daemon parses OPNsense syslog files every scan cycle
2. Extracts WiFi client connect/disconnect events (last 24h)
3. Builds MAC → AP identifier mapping
4. Resolves AP identifiers to known AP IPs/hostnames
5. Updates devices with connected_to_ap and ap_name
6. **No AP configuration needed!** (if APs send logs to OPNsense)

### Module:
- **ap_syslog_parser.py**: Syslog parsing engine
- **6 vendor patterns**: Pre-configured for common AP types
- **Timestamp extraction**: Handles multiple syslog date formats
- **CLI testing**: `python3 ap_syslog_parser.py` (shows all associations found)

### Benefits Over SNMP:
✅ **Zero AP configuration** - No SNMP setup needed  
✅ **Works immediately** - If APs log to OPNsense  
✅ **Consumer AP friendly** - Most don't support SNMP  
✅ **Passive detection** - No active queries  
✅ **Historical data** - Can parse old logs  
✅ **Automatic fallback** - If SNMP not available  

### Setup (Optional):

**If APs don't log to OPNsense by default:**
1. Configure APs to send syslog to OPNsense IP
2. Or ensure hostapd logs are being written
3. That's it! No SNMP community strings, no firewall rules

**Priority:** Syslog tried first, SNMP second

### Use Case:
Perfect for home users and consumer APs (UniFi, TP-Link, Asus, etc.) that don't support SNMP or make it difficult to configure.

---

**v2.0.2 makes AP detection work for everyone, not just enterprise gear!** 🏠📡

## 2.0.1 - Timeline Reversed
- **Timeline Direction Reversed**: Most recent events now on LEFT, oldest on right (more intuitive).
- **Labels Updated**: Left shows "NOW" with current date/time, right shows "30 DAYS AGO".
- **Segment Order**: Timeline bar segments reversed so newest status appears first (left side).
- **Markers Repositioned**: Attribute change diamonds correctly positioned on reversed timeline.
- **Click Handlers**: Updated to work with reversed direction.
- **Better UX**: Left-to-right reading shows current state first, then scrolls back in time.
- Header: "Connection State Timeline (Last 30 Days) - Most Recent on Left"

## 2.0.0 - Network Topology Discovery (MAJOR RELEASE)

### WiFi Access Point Detection:
- **AP Client Association**: Discovers which WiFi clients are connected to which Access Points.
- **SNMP-Based Discovery**: Queries APs via SNMP to get client MAC address tables.
- **Multi-Vendor Support**: Supports MikroTik, Ubiquiti UniFi, Cisco, Aruba, and generic bridge tables.
- **Automatic AP Identification**: Identifies APs by device_type or hostname patterns (unifi, ap-, etc.).
- **Client Mapping**: Maps client MAC addresses to AP IP addresses.
- **AP Name Resolution**: Shows friendly AP hostname instead of just IP.
- **Timestamp Tracking**: Records when AP association was last confirmed (ap_last_seen).

### Schema Changes:
- **connected_to_ap** TEXT - AP IP address client connects through
- **ap_name** TEXT - Friendly AP hostname
- **ap_last_seen** INTEGER - When association was confirmed
- **Index**: idx_devices_connected_to_ap for fast AP-based queries

### UI Display:
**Detail Modal:**
```
Connected Via:
  📡 WiFi Access Point
  AP-Living-Room (192.168.1.100)
  Association confirmed 5 min ago
```

**Inventory Table:**
- New "Via AP" column (sortable, hideable)
- Shows AP name for WiFi-connected devices
- Empty for wired devices
- WiFi icon (📡) in header

### Requirements:
- **SNMP enabled on APs** (community string configured)
- **SNMP option enabled** in NetDiscover settings
- **APs must be discoverable** in network scan

### How It Works:
1. Daemon identifies APs (device_type contains "access point" or hostname patterns)
2. For each AP, queries SNMP client table using vendor-specific OIDs
3. Extracts client MAC addresses from SNMP responses
4. Matches client MACs to devices in inventory
5. Updates devices with connected_to_ap and ap_name fields
6. Runs every scan cycle (updates as clients roam between APs)

### Vendor Support:
- **MikroTik**: OID 1.3.6.1.4.1.14988.1.1.1.2.1.1
- **Ubiquiti UniFi**: OID 1.3.6.1.4.1.41112.1.6.1.2.1.6
- **Cisco**: OID 1.3.6.1.4.1.9.9.273.1.1.2.1.1
- **Aruba**: OID 1.3.6.1.4.1.14823.2.2.1.5.2.1.5.1.3
- **Generic**: Bridge table fallback

### Module:
- **ap_detector.py**: Standalone module for AP client detection
- **discover_ap_clients()**: Main function for batch AP queries
- **parse_mac_from_snmp()**: Handles various SNMP MAC formats (hex, colon, OID index)
- **CLI Testing**: `python3 ap_detector.py <ap_ip> [community]`

### Benefits:
✅ **Know which AP** each WiFi device uses  
✅ **Troubleshoot roaming** - See AP switches over time  
✅ **Load balancing** - Identify crowded APs  
✅ **Coverage mapping** - See which rooms/areas devices prefer  
✅ **No controller needed** - Works with standalone APs  
✅ **Historical tracking** - AP association changes logged  

### Use Cases:
- "Which AP is my iPhone connected to right now?"
- "How many devices on AP-Living-Room?"
- "Did device roam between APs today?" (check history)
- "Is AP-Bedroom being used?" (check connected clients)

### Future Enhancements (v2.1.0+):
- Switch port mapping (MAC address tables)
- Signal strength tracking
- LLDP neighbor discovery
- Full network topology graph
- Path visualization

---

**This is a MAJOR feature unlocking WiFi network visibility!** 

**Use:** Enable SNMP on your APs, configure community string in NetDiscover Settings, and watch the "Via AP" column populate!

## 1.7.2 - Full Port Scan & Visual Headers

### Full 65K Port Scan:
- **ALL Ports**: Exhaustive scan now scans ALL 65,535 ports (was 1-1000).
- **Proper Warning**: Confirmation dialog warns about full scan and 5-10 minute duration.
- **Optimized nmap**: Uses -T5 (insane) timing with --min-rate 1000 for full scans.
- **No Retries**: Full scan uses --max-retries 0 for maximum speed.
- **Python Fallback Enhanced**: Increased to 200 concurrent threads, 0.3s timeout per port.
- **Longer Timeout**: AJAX timeout increased to 10 minutes (600s) to accommodate full scan.
- **Expected Duration**: 5-7 minutes with nmap, 8-10 minutes with Python fallback.
- Use case: Complete port profile for security audits and comprehensive device identification.

### Visual Column Header Indicators:
- **Color Legend in Headers**: Status column headers now show visual color indicators.
- **Flags Column (🏴)**: Shows 3 colored dots (orange/blue/cyan) for new/changed/back.
- **Connection Column (●)**: Shows 4 colored dots (green/yellow/orange/red) for online/offline/missing/gone.
- **DHCP Column (⇄)**: Shows 3 colored dots (cyan/yellow/green) for static/reserved/dynamic.
- **Pie Chart Style**: Small colored circles (6-8px) arranged horizontally above icon.
- **At-a-Glance Reference**: Users can see all possible status colors without opening legend.
- **Hover Tooltips**: Each dot has tooltip explaining the color/state.
- **Compact Design**: Fits in narrow column headers without cluttering.
- No need to memorize color codes - visual reference always visible!

## 1.7.1 - JSON Field Parsing Fix
- **FIXED: Open Ports Not Showing**: Open ports now display correctly in inventory table.
- **Root Cause**: JSON array fields (open_ports, mdns_services, tags) sometimes not parsed from string.
- **Fix Applied**: JavaScript now safely parses JSON strings before rendering.
- **Defensive Parsing**: Added try/catch with Array.isArray() check for all JSON array fields.
- **Fields Fixed**: open_ports, mdns_services, tags, banners.
- **PHP Enhancement**: Added banners JSON parsing in InventoryController.
- **Graceful Degradation**: If parsing fails, shows empty string instead of crashing.
- All array fields now render reliably regardless of data format.

## 1.7.0 - Model Hints Active (Major Feature Complete)

### Wireshark Model Hints Now Functional:
- **Model Hints Used**: Daemon now actually uses model hints from Wireshark extended database.
- **oui_models Table**: Daemon loads model hints at startup from oui_models table.
- **Auto-Population**: discovered_model field populated from OUI model hints.
- **Fallback Chain**: Model populated as: User override → SSDP/SNMP discovered → OUI model hint → empty.
- **All merge() Calls Updated**: All 5 device merge points now pass model_hints parameter.
- **discovered_manufacturer**: Also populated from OUI vendor lookup for override tracking.
- **Ready for Display**: Model column will now show Wireshark model hints for matching devices.

### Technical Changes:
- `load_oui_from_sqlite()` now returns tuple: (vendor_map, model_hints_map)
- `load_oui()` wrapper updated to return tuple
- `merge()` function signature updated with model_hints parameter
- All 5 merge() call sites updated: ssdp, mdns, llmnr, nbns, arp, dnsmasq
- Model hints applied after vendor lookup in merge()

### Benefits:
✅ **Richer device data** - Model information from 38K+ Wireshark entries  
✅ **Better identification** - Many devices now have model populated automatically  
✅ **Override tracking** - Discovered values tracked separately from user overrides  
✅ **No manual work** - Model hints applied automatically on discovery  

### Next Device Scan:
After deployment, next scan cycle will:
1. Load model hints at daemon startup
2. Apply model hints to all devices with matching OUIs
3. Populate discovered_model field
4. Display in Model column

**This completes the Wireshark Extended integration!** Model hints are no longer just extracted - they're actively used.

## 1.6.9 - Port Scan Display Fix
- **FIXED: Port Scan Results Legibility**: Port scan messages now have explicit black text (color:#000).
- **Better Formatting**: Multi-line display with bold headers and line breaks for clarity.
- **Success Message**: Shows count and port list on separate lines.
- **No Open Ports**: Shows italic "No open ports detected" when scan finds nothing.
- **All Alerts Fixed**: Info, success, and danger alerts now readable on all themes.
- Root cause: Green alert background with default text color was illegible.

## 1.6.8 - Source Archiving
- **Automatic Source Archive**: deploy.sh now creates versioned source tar.gz archive after deployment.
- **Archive Location**: `./archive/os-netdiscover-devel-v[version].tar.gz`
- **Version in Filename**: Archive automatically named with current version from Makefile.
- **Excludes**: work/, archive/, .git/, and .pkg files excluded from archive.
- **Archive Directory**: Created automatically if it doesn't exist.
- **File Size Shown**: Displays archive size after creation.
- Use case: Keep versioned snapshots of source code for rollback or reference.

## 1.6.7 - Documentation Organization
- **Documentation Folder**: Moved all .md files into `docs/` subfolder for better organization.
- **Kept in Root**: README.md and CHANGELOG.md remain in root (standard practice).
- **Documentation Index**: Created docs/INDEX.md with organized links to all documentation.
- **Updated README**: Modernized README.md with feature overview, links to docs, and quick start guide.
- **Files Moved (16)**: All release notes, guides, architecture docs, and development notes now in docs/.
- Better organization for maintainability and navigation.

## 1.6.6 - Interactive Timeline
- **Interactive Timeline**: Timeline segments and markers now clickable/touchable.
- **Segment Click**: Click any timeline bar segment to see full date/time details in popup below.
- **Shows Period Info**: Period number, state, start date/time, end date/time, duration.
- **Marker Click**: Click magenta diamonds to see which attribute changed and when.
- **Date + Time Labels**: Timeline now shows both date and time at start/end (not just dates).
- **White Boundary Lines**: Visual separators between status periods (clickable).
- **Detail Popup**: Appears below timeline with full timestamp information.
- **Cursor Changes**: Pointer cursor on hover indicates clickable areas.
- Use case: Click segment to see exact timestamp when device went offline, came back, etc.

## 1.6.5 - CRITICAL FIX: Detail Modal After Port Scan
- **CRITICAL BUG FIX**: Detail modal now opens correctly for devices that have had a port scan.
- **Root Cause**: exhaustive_ports stored as JSON string in database, JavaScript tried to call .length and .join() on string.
- **Fix #1**: JavaScript now parses exhaustive_ports string before using it.
- **Fix #2**: PHP InventoryController now parses exhaustive_ports JSON before sending to frontend.
- **Result**: Modal opens properly for all devices regardless of port scan status.
- Also added null checks to prevent errors if data is malformed.

## 1.6.4 - OS Override & Detection Complete
- **OS Override in Edit Modal**: Added Operating System field to device edit form.
- **OS Detection Enhanced**: extract_os_from_banner() now extracts both OS name and version.
- **Discovered OS Field**: daemon populates discovered_os separate from os (for override tracking).
- **OS Version Parsing**: Extracts versions from SSH banners (e.g., "Ubuntu-4ubuntu0.1" → version "20.04").
- **Multiple OS Sources**: SSH, HTTP Server headers, SNMP sysDescr, hostname patterns.
- **OS Override**: User can override detected OS in edit modal.
- **OverridesController**: Handles os field in save/load operations.
- **InventoryController**: Merges os overrides with discovered values.
- **db_helper**: Updated set_override() signature to include os parameter.

## 1.6.3 - Enhanced Timeline Visualization
- **Timeline Redesign**: Connection states now shown as horizontal bar segments (online/offline/missing/gone).
- **Attribute Change Markers**: Lifecycle changes (hostname/MAC/vendor/model changes) shown as magenta diamonds (◆) on timeline.
- **Positioned Markers**: Diamonds appear at exact timestamp of each attribute change.
- **Hover Tooltips**: Each diamond shows which field changed and when.
- **Date Scale**: Timeline now shows start and end dates above the bar for temporal context.
- **Cleaner Legend**: Separate sections for connection states (bars) and attribute changes (diamonds).
- **Better Semantics**: Connection state history (the important stuff) is the main visualization, attribute changes are markers.
- **SVG Diamonds**: Magenta diamonds with white outline for visibility on any background.
- Example: Green bar for "online" with magenta diamond where hostname changed.

## 1.6.2 - Model Hints & OS Column
- **Model Hints Extraction**: Wireshark update now extracts model information from extended MAC entries.
- **oui_models Table**: New table in oui.db stores model hints separately (linked by OUI).
- **OS Column Added**: Operating System now available as sortable/hideable column in inventory table.
- **OS Display**: Shows OS name + version (e.g., "Ubuntu Linux 20.04") if detected.
- **Column Config**: OS checkbox added to column configuration modal (visible by default).
- **Auto-Migration**: Daemon adds discovered_manufacturer, discovered_model, discovered_os, os_version columns.
- **Enhanced Wireshark**: Now reports both vendor count AND model hint count during download.
- Model hints available for daemon to populate discovered_model field.

## 1.6.1 - Port Scan Fix
- **CRITICAL FIX**: Fixed port scan failing with "bindValue() on false" error.
- **Root Cause**: exhaustive_ports columns didn't exist in database when scan attempted.
- **Fix**: ScanController now checks for columns and adds them if missing before scan.
- **Auto-Migration**: netdiscoverd.py now auto-adds v1.6.0 columns on startup.
- Port scan button now works correctly!

## 1.6.0 - Override vs Discovered, OS Detection & Port Scanning

### On-Demand Exhaustive Port Scanning:
- **"Port Scan" Button**: Added to device detail modal for on-demand exhaustive port scans.
- **Scan Range**: Default 1-1000 ports (configurable via API).
- **Dual Scanner**: Uses nmap if available, falls back to Python threaded scanner.
- **Progress Display**: Real-time feedback during 30-60 second scan.
- **Results Storage**: Stores exhaustive_ports separate from quick-scan open_ports.
- **Persistent Results**: Scan results remembered until next automatic scan cycle.
- **Timestamp**: Shows when last exhaustive scan was performed.
- **API Endpoint**: `/api/netdiscover/scan/ports` - POST with {ip, range}.
- **Warning Dialog**: Confirms user wants to scan (IDS/IPS may detect).
- Fallback scanner: `port_scanner.py` uses ThreadPoolExecutor for parallel scanning.

### Override vs Discovered Display:
- **Separate Fields**: discovered_manufacturer, discovered_model, discovered_os in schema.
- **Detail Modal Enhancement**: Shows BOTH user override and discovered values.
- **Visual Distinction**:
  - User override: **Bold** with [Override] badge
  - Discovered: Grey text below override ("Discovered: ...")
- **Table Display**: Shows user override if set, otherwise discovered value.
- **Clear Attribution**: User always knows which values they set vs auto-discovered.

### Operating System Detection:
- **OS Name & Version**: New fields os, os_version in schema.
- **Multiple Sources**:
  - SSH banners: `OpenSSH_8.2p1 Ubuntu-4ubuntu0.1` → Ubuntu 20.04
  - HTTP Server headers: `Apache/2.4.41 (Ubuntu)` → Ubuntu
  - SNMP sysDescr: Full OS strings
  - Hostname patterns: `debian-server` → Debian
- **OS Override**: User can override OS in edit modal.
- **Detail Modal**: Shows OS name + version with discovered vs override distinction.

### Enhanced Detail Modal:
**Manufacturer Display:**
```
Manufacturer:
  HP Inc. [Override]
  Discovered: Hewlett-Packard
```

**Model Display:**
```
Model:
  LaserJet Pro M428 [Override]
  Discovered: M428fdw
```

**Open Ports:**
```
Open Ports:                    [Port Scan]
  Exhaustive Scan: 22, 80, 443, 515, 631, 9100
  Scanned: 12/26/2025, 9:30 PM
```

**Operating System:**
```
Operating System:
  Debian Linux 10.2
```

### Schema Updates:
- `discovered_manufacturer` TEXT
- `discovered_model` TEXT  
- `discovered_os` TEXT
- `os_version` TEXT
- `exhaustive_ports` TEXT (JSON array)
- `exhaustive_ports_time` INTEGER
- `os` override in device_overrides table

### API Endpoints:
- `/api/netdiscover/scan/ports` - Exhaustive port scan

### Files Created:
- `ScanController.php` - Port scanning API
- `port_scanner.py` - Python fallback scanner

## 1.5.1 - DHCP Type Detection & Widget Deduplication
- **DHCP Type Column**: New column next to IP showing static/reserved/dynamic with colored indicator.
  - 🔵 Cyan = "static" (outside DHCP range)
  - 🟡 Yellow/Orange = "reserved" (MAC-based DHCP reservation)
  - 🟢 Green = "dynamic" (regular DHCP lease)
  - ⚫ Gray = "unknown" (could not determine)
- **DHCP Analyzer**: New `dhcp_analyzer.py` parses dnsmasq config and leases to determine IP assignment type.
- **Batch Analysis**: Analyzes all devices at once (efficient) before each database write.
- **Auto-Detection**: Automatically determines DHCP type from:
  - dnsmasq DHCP ranges (dhcp-range directives)
  - dnsmasq MAC reservations (dhcp-host directives)
  - Active DHCP leases file (/var/db/dhcpd.leases)
- **Widget Deduplication**: Dashboard widget now shows only most recent event per device (eliminates duplicate entries).
- **UI**: DHCP column always visible (not configurable), hover tooltip explains each type.
- **Schema**: Added `dhcp_type` column with index.
- **Auto-Migration**: Existing databases get dhcp_type column added automatically.
- **Legend Updated**: Status Legend modal now includes DHCP type color explanations.
- Use case: Quickly identify which devices have static IPs vs DHCP leases vs reservations.

## 1.5.0 - Dual-State Status Architecture (MAJOR)

### Revolutionary Two-Dimensional Status System:

**Devices now have TWO independent properties:**

#### 1. Connection State (Required):
- **online** 🟢 - Currently reachable
- **offline** 🟡 - Not seen for 2+ scan cycles
- **missing** 🟠 - Not seen for 30 days
- **gone** 🔴 - Not seen for 60 days

#### 2. Lifecycle Flags (Optional, Can Combine):
- **new** 🔶 - First discovered (24h or until reviewed)
- **changed** 🔷 - Attributes changed (24h or until reviewed)
- **back** 🔵 - Just returned online (24h or until reviewed)

### Key Insight:
**Something can be BOTH "new" AND "offline"** or "changed" AND "online" simultaneously!

**Examples:**
- `new, online` - Just discovered and reachable
- `new, offline` - Just discovered but not responding
- `changed, online` - Hostname changed on active device
- `back, online` - Just came back from being offline
- `online` - Normal device (no special flags)
- `missing` - Been offline for 30 days

### Display Changes:

**Status Column Now Shows:**
```
🟠 [new] 🟢 online      ← Badge for flag, dot for connection
🔷 [changed] 🟢 online  ← Can combine!
🟡 offline               ← Just connection state
🟠 missing               ← Long-term offline
🔴 gone                  ← Permanently offline
```

### Filter System Redesigned:

**Two Filter Groups:**
```
Lifecycle: [All] [New] [Changed] [Back]
     |
Connection: [All] [Online] [Offline] [Missing] [Gone]
```

**Can filter by either dimension:**
- Show all "new" devices (regardless if online/offline)
- Show all "offline" devices (regardless of flags)
- Combine: Show "new" AND "offline" devices

### Timing Changes:

| Threshold | v1.4.x | v1.5.0 | Reason |
|-----------|--------|---------|--------|
| Offline | 30 min fixed | **2 × scan_interval** | Adaptive |
| Missing | N/A | **30 days** | New state |
| Gone | 14 days | **60 days** (30+30) | More grace period |
| New flag | 48h | **24h or reviewed** | Shorter, user-driven |
| Changed flag | 24h | **24h or reviewed** | Consistent |
| Back flag | Auto | **24h or reviewed** | User-controlled |
| Auto-prune | 30 days | **NEVER** | No auto-deletion |

### Database Schema:

**New Columns:**
- `connection_state` TEXT - online/offline/missing/gone
- `lifecycle_flags` TEXT - Comma-separated flags
- `flag_set_time` INTEGER - When flags were set
- `flag_acknowledged` INTEGER - User viewed device

**Removed:**
- `new_acknowledged` (replaced by `flag_acknowledged`)

**Indexes:**
- idx_devices_connection_state
- idx_devices_lifecycle_flags

### Auto-Migration:

Daemon automatically migrates old status values:
```sql
Old "new" → connection_state="online", flags="new"
Old "changed" → connection_state="online", flags="changed"
Old "gone" → connection_state="gone", flags=""
Old "offline" → connection_state="offline", flags=""
```

### No Auto-Prune:

**Important Change:** Devices are **NEVER automatically deleted**.
- Old behavior: Devices >30 days deleted from memory
- New behavior: Devices stay forever until manually deleted
- Rationale: User should control inventory, not time-based purge
- "gone" devices remain for historical record

### API Changes:

**Acknowledge endpoint updated:**
- Clears all lifecycle flags (new/changed/back)
- Sets flag_acknowledged = 1
- Recalculates status display string

**Inventory API returns:**
- `connection_state` field
- `lifecycle_flags` field  
- `status` (computed display string for compatibility)

### UI Changes:

**Two-Column Status Display:**
- **Flags Column** (🏴) - Shows lifecycle indicators (new/changed/back) as colored balls **ONLY**
  - 12px colored circles, no text
  - Multiple balls can appear side-by-side (e.g., new + changed)
  - Empty if no flags active
  - Hover tooltip on each ball: "New - First discovered", etc.
  - Column header: Flag icon with tooltip
- **Connection Column** (●) - Shows connection state (online/offline/missing/gone) as colored ball **ONLY**
  - 12px colored circle, no text
  - Single ball always present
  - Hover tooltip: "Online - Currently reachable", etc.
  - Column header: Circle icon with tooltip
- **Compact Display** - No text labels, just colored indicators
- **Tooltips Everywhere** - Headers and cells have explanatory tooltips

**Status Legend:**
- New "Legend" button in toolbar
- Modal explaining all color codes
- Lifecycle flags section
- Connection states section
- Example combinations

**Filter buttons:**
- Two separate button groups with visual separator (|)
- Lifecycle filters: All, New, Changed, Back
- Connection filters: All, Online, Offline, Missing, Gone
- Can combine filters from both groups

**Column Configuration:**
- Removed "Status" from config (now two always-visible columns)
- Flags and Connection columns always shown

### Benefits:

✅ **Much clearer semantics** - Two independent concepts  
✅ **More accurate** - Devices can be new AND offline  
✅ **Better filtering** - Filter by lifecycle OR connection OR both  
✅ **Richer information** - See both dimensions simultaneously  
✅ **No surprise deletions** - Devices stay until you delete them  
✅ **30-day grace period** - "missing" before "gone"  
✅ **User-driven acknowledgment** - Flags clear when you review  

## 1.4.1 - Status Filter Fixes & Threshold Updates
- **FIXED: Status Filters Now Work**: All/New/Changed/Gone buttons now properly filter inventory table.
- **New Filter Buttons**: Added "Online" (up status) and "Offline" buttons to toolbar.
- **Case-Insensitive Matching**: Filter comparison now case-insensitive for reliability.
- **Visual Feedback**: Active filter button highlights in blue (btn-primary).
- **Filter State Restoration**: Saved filter properly restored on page load.
- **Filter Order**: All, New, Online, Offline, Changed, Gone (logical progression).
- **Dynamic Offline Threshold**: Changed from fixed 30 minutes to **2 × scan_interval** (adaptive).
  - 5 min scan → offline after 10 min
  - 2 hour scan → offline after 4 hours
  - **Much smarter!** Adapts to your scan frequency
- **Extended New Timeframe**: "new" status now persists for **48 hours** (was 24h) or until reviewed.
- Root cause of filter bug: Comparison had case sensitivity issues.

## 1.4.0 - Major Status Redesign & Timeline Visualization

### Status System Redesign:

**New Status Definitions (Much Clearer):**
- 🟢 **"up"** - Device online and stable (default active state)
- 🔵 **"back"** - Device came back online after being offline (transient, becomes "up" on next scan)
- 🔷 **"changed"** - Device attribute changed (hostname/MAC/vendor/model - NOT just online)
- 🟡 **"offline"** - Device not seen for 30 minutes to 14 days
- 🔴 **"gone"** - Device not seen for 14+ days (truly gone)
- 🟠 **"new"** - First time discovered (persists until viewed or 24 hours)

**Key Changes from v1.3.x:**
- **"changed" meaning**: Was "came back online OR changed", now **ONLY attribute changes**
- **"gone" threshold**: Was "not seen in last scan" (~5 min), now **14 days offline**
- **"offline" status**: NEW - intermediate state (30min - 14 days)
- **"back" status**: NEW - explicitly marks device returning online
- **"up" status**: NEW - default healthy state (was implicit before)

### Status Transition Logic:

1. **"new"** → "up" after user views device OR 24 hours
2. **"up"** → "offline" if not seen for 30 minutes
3. **"offline"** → "back" when device reappears
4. **"back"** → "up" on next scan cycle (transient state)
5. **"offline"** → "gone" after 14 days
6. **"gone"** → "new" if rediscovered (was removed, now back)
7. **Any** → "changed" when hostname/MAC/vendor/manufacturer/model/interface changes
8. **"changed"** → previous state on next scan (transient)

### Timing Constants (v1.4.1):
- **OFFLINE_THRESHOLD**: Dynamic - **2 × scan_interval** (adaptive)
  - Example: 120s interval → offline after 240s (4 minutes)
  - Example: 300s interval → offline after 600s (10 minutes)
- **NEW_THRESHOLD**: **48 hours** (172,800s) - stay as "new" until viewed
- **GONE_THRESHOLD**: **14 days** (1,209,600s) - mark as gone
- **PRUNE_THRESHOLD**: 30 days (2,592,000s) - removed from memory

### Timeline Graph Visualization:

**New Visual Timeline in Device History:**
- **Horizontal bar graph** showing device status over time
- **Color-coded segments** matching status colors
- **Hover tooltips** showing status and duration
- **Percentage-based widths** for proportional representation
- **Legend** showing all status types
- **Period count** and duration summary

**Timeline Features:**
- **Two views**: Switch between Timeline (graph) and Table (list)
- **30-day window**: Shows last month of status history
- **Status segments**: Visual blocks for each status period
- **Smooth transitions**: Status changes marked at exact timestamps
- **API Endpoint**: `/api/netdiscover/history/timeline?ip=X&days=30`

**Example Timeline:**
```
████████████░░░░░████████████████████
└─── up ────┘     └───── up ────────┘
         (8h offline)

6 status period(s) over 30 days
```

### Visual Updates:

**Updated status colors everywhere:**
- Inventory table status column
- Recent Changes event type column
- Dashboard widget event list
- Device detail modal
- Timeline graph segments

**Color consistency:**
- 🟢 Green (#5cb85c) - up
- 🔵 Cyan (#5bc0de) - back
- 🔷 Light Blue (#428bca) - changed
- 🟡 Orange (#f0ad4e) - offline/new
- 🔴 Red (#d9534f) - gone
- ⚫ Gray (#999) - unknown/default

### API Endpoints Added:

1. **`/api/netdiscover/history/timeline`** - Get timeline segments for graph
   - Query params: `ip`, `days` (default 30)
   - Returns: segments array with status, duration, percent
   - Calculates periods from device_history status_change events

### Files Changed:

**Backend:**
- `netdiscoverd.py` - New status logic, timing constants, update_device_status()
- `HistoryController.php` - New timelineAction() endpoint

**Frontend:**
- `app.js` - Timeline graph rendering, split history views, updated colors
- `NetDiscoverWidget.js` - Updated event type colors

**Documentation:**
- `STATUS_REDESIGN.md` - Complete status system documentation

**Versioning:**
- `Makefile` - v1.4.0 (major release)
- `CHANGELOG.md` - Comprehensive changelog

### Migration Notes:

**Existing deployments:**
- Old statuses will gradually transition to new system
- Devices marked "gone" will transition based on actual offline duration
- "changed" devices will become "up" or "back" based on context
- No data loss, graceful migration

### Benefits:

✅ **Much clearer semantics** - "changed" means something changed, not just online  
✅ **Better monitoring** - Can distinguish offline (temp) vs gone (permanent)  
✅ **Visual timeline** - See device history at a glance  
✅ **14-day gone threshold** - Reduces noise from temporary offline devices  
✅ **Transient states** - "back" and "changed" transition automatically  
✅ **Consistent colors** - Same meaning across all views  

## 1.3.10 - Delete Device Feature
- **Delete Device Button**: Added red "Delete Device" button to edit modal.
- **Confirmation Modal**: Two-step delete process with dedicated confirmation dialog.
- **Warning Dialog**: Shows device IP and warns about permanent removal.
- **Complete Deletion**: Removes device from devices, device_history, device_overrides, and events tables.
- **JSON Cleanup**: Also removes from legacy JSON files (backwards compatibility).
- **API Endpoint**: `/api/netdiscover/inventory/delete` - POST with {"ip": "..."}.
- **Auto-Refresh**: Table reloads after deletion to reflect changes.
- **Use Case**: Remove unwanted devices, test devices, or incorrect entries from inventory.
- Note: Device will be rediscovered on next scan if still present on network.

## 1.3.9 - Numeric Sorting Fix
- **IP Address Sorting**: Fixed IP column sorting to use numeric comparison per octet instead of string comparison.
- **Correct Order**: Now sorts 192.168.1.2, 192.168.1.3, ..., 192.168.1.100 (not 192.168.1.100, 192.168.1.2).
- **Algorithm**: Converts IP to 32-bit number (octet1*16777216 + octet2*65536 + octet3*256 + octet4).
- **Applied To**: Both Inventory and Recent Changes tables.
- **Timestamp Sorting**: Also improved last_seen and event time sorting (numeric comparison).
- Helper function `ipToNumber()` for IPv4 address comparison.

## 1.3.8 - Deploy Script Update
- **Deploy Default Changed**: Now downloads Wireshark Extended database instead of IEEE OUI.
- **Fallback**: If Wireshark fails, automatically falls back to IEEE OUI.
- **UI Update**: Wireshark button now green (recommended), IEEE button default (alternative).
- **Help Text**: Clarified that sources are mutually exclusive (not additive).
- **Recommendation**: Wireshark Extended provides better detail (35K+ with model hints vs 30K manufacturer-only).

## 1.3.7 - CRITICAL FIX: Database Schema Auto-Migration
- **CRITICAL FIX**: Added automatic schema migration to add missing columns to existing databases.
- **Root Cause**: Databases created before v1.3.4 missing `new_acknowledged`, `device_type_source`, `os`, `banners` columns.
- **Error**: "no such column: new_acknowledged" prevented SQLite writes, daemon fell back to JSON only.
- **Fix**: init_sqlite_db() now checks existing columns and adds missing ones via ALTER TABLE.
- **Auto-Migration**: Runs on every daemon start, no manual database deletion needed.
- **Backwards Compatible**: Works with databases from any version.
- Devices now write successfully to SQLite with all columns present.

## 1.3.6 - CRITICAL FIX: Crash Loop Resolved
- **CRITICAL FIX**: Daemon was crash-looping due to rc.d script passing `--oui` argument that was removed in v1.2.4.
- **Root Cause**: argparse failed with unknown argument error, causing instant crash and restart loop.
- **Fix #1**: Re-added `--oui` argument to Python script as deprecated (backwards compatible).
- **Fix #2**: Removed `--oui` argument from rc.d script (clean going forward).
- **Result**: Daemon now starts successfully and stays running.
- Crash was happening at `ap.parse_args()` with unknown argument.

## 1.3.5 - Debug Crash Loop
- **DIAGNOSTIC**: Added extensive startup logging to pinpoint crash location.
- Logs each step: arg parsing, OUI loading, port parsing, DB dir creation, SQLite init.
- This version will show exactly where daemon is crashing in crash-loop scenario.

## 1.3.4 - Enhanced Diagnostics & "New" Status Persistence
- **"New" Status Persistence**: Devices stay marked as "new" until user views details OR 24 hours pass (whichever comes first).
- **Acknowledge API**: New endpoint `/api/netdiscover/acknowledge/device` marks device as viewed.
- **Auto-acknowledge**: Opening device detail modal automatically acknowledges the device.
- **Smart Status Transition**: "new" → "changed" only after acknowledgment or 24h, prevents premature status changes.
- **Enhanced Error Logging**: SQLite write operations now log success/failure with device/event counts.
- **Better Error Handling**: Individual device/event write failures don't abort entire batch.
- **Connection Timeouts**: SQLite connections now have 10-second timeout to prevent hangs.
- **Startup Logging**: Daemon logs PID and scan interval on successful start.
- **Sync Loop**: Each scan cycle syncs new_acknowledged flags from database.
- **Database Schema**: Added `new_acknowledged` column to devices table.
- **Diagnostic Script**: `check_status.sh` verifies daemon health and database status.
- Use case: New devices remain highlighted until you review them or they age out.

## 1.3.3
- **Dashboard Widget Enhancement**: Added colored status indicators (dots) to event type column in Recent Events table.
- **Visual Consistency**: Widget now matches main Recent Changes tab styling with color-coded dots.
- **Color Scheme**: 🟠 new, 🔷 changed, 🔴 gone, 🟢 back/up (8px dots with 6px margin).

## 1.3.2 - Bug Fixes
- **CRITICAL FIX**: Events now display correctly - fixed field name mapping (`event_type` → `type` in PHP controllers).
- **Dashboard Widget Fix**: Recent events now show type indicators correctly (was broken after SQLite migration).
- **Recent Changes Tab Fix**: Events table now populates properly from SQLite.
- **Field Mapping**: EventsController and DashboardController now both map `event_type` to `type` for JavaScript compatibility.
- **Diagnostic Script**: Added `check_status.sh` to quickly verify database and daemon status.
- Daemon restart recommended after deployment to populate events table.

## 1.3.1
- **Column Reordering**: Moved Status column to left of IP address for better at-a-glance visibility.
- **Visual Priority**: Status indicator (color-coded dot) now in second column for quick scanning.
- **Verified Column Alignment**: Ensured all data cells match their header columns in correct order.

## 1.3.0 - Advanced Device Fingerprinting

### Pattern-Based Device Identification (5 methods):

#### 1. Hostname Pattern Matching 🎯
- **100+ patterns** for common device hostnames
- **Mobile**: android-*, iPhone*, iPad*, Galaxy*
- **IoT**: ESP_*, raspberry*, tasmota*, shelly*
- **Printers**: *printer*, *laserjet*, HP*, Canon*, etc.
- **NAS**: *nas*, synology*, qnap*, diskstation*
- **Cameras**: *camera*, ipc*, *nvr*, *dvr*
- **Smart Home**: hue-*, nest-*, echo-*, google-home*
- **Network**: switch*, router*, ap-*, unifi*
- **Computers**: desktop-*, macbook*, imac*
- **Gaming**: playstation*, xbox*, nintendo*

#### 2. Port Signature Detection 🔍
- **Printers**: Ports 631+9100 → Network Printer
- **NAS**: Ports 139+445+5000 → Synology NAS
- **Cameras**: Port 554+8000 → IP Camera
- **Windows**: Ports 135+139+445+3389 → Windows Desktop/Server
- **Network Gear**: Ports 22+80+443+161 → Managed Switch/Router
- **Databases**: Ports 3306/5432/27017 → MySQL/PostgreSQL/MongoDB
- **VoIP**: Ports 5060/5061 → VoIP Device
- **Web Servers**: Various combinations
- **50+ port signature patterns**

#### 3. mDNS Service Combination Patterns 📡
- **_airplay._tcp + _raop._tcp** → Apple TV/HomePod
- **_airplay._tcp + _ssh._tcp** → macOS
- **_googlecast._tcp** → Chromecast/Google Home
- **_hap._tcp** → HomeKit Accessory
- **_ipp._tcp + _scanner._tcp** → Printer/Scanner MFP
- **_smb._tcp + _afpovertcp._tcp** → macOS/NAS
- **_hue._tcp** → Philips Hue Bridge
- **_sonos._tcp** → Sonos Speaker
- **_mqtt._tcp** → MQTT Device/Broker
- **20+ service combination patterns**

#### 4. Wireshark Extended Manufacturer Database 🌐
- **Alternative to IEEE OUI**: Use Wireshark's enhanced database
- **35,000+ entries** with model hints and short names
- **More detailed** than standard IEEE OUI
- **UI button**: Choose between IEEE or Wireshark source
- **Format**: Includes some device-specific identifiers
- **Script**: `update_wireshark_manuf.py`
- **API**: `/api/netdiscover/service/updatewireshark`

#### 5. Enhanced Banner Grabbing 🔖
- **Expanded ports**: SSH(22), HTTP(80/443/8080/8443), FTP(21), Telnet(23), SMTP(25)
- **Server headers**: Extract HTTP Server header for OS/software detection
- **SSH banners**: OpenSSH version + OS (Ubuntu/Debian/Raspbian)
- **FTP banners**: Synology/QNAP/vsftpd detection
- **Telnet banners**: DD-WRT/OpenWrt router detection
- **Banner analysis**: Auto-detect device type and OS from banners
- **Storage**: Banners stored in device record for historical analysis

### Integration:
- **Automatic application**: Pattern matching runs automatically during device discovery
- **Priority system**: User override > Pattern match > Discovered > OUI
- **No external dependencies**: All patterns are local (except Wireshark download)
- **Graceful fallback**: If pattern module missing, daemon still works
- **Device type source tracking**: Records whether device_type came from pattern_match vs discovery

### Performance:
- **Fast**: Pattern matching adds <1ms per device
- **Efficient**: Banner grabbing only on enabled ports (opt-in via tcp_probe_enable)
- **Memory**: Minimal impact (~100KB for pattern rules)

### Files Created:
- **device_patterns.py**: Pattern matching library (hostname/port/mDNS/banner analyzers)
- **update_wireshark_manuf.py**: Wireshark manuf database downloader
- **oui_schema.sql**: Separate OUI database schema
- **DEVICE_FINGERPRINTING.md**: Complete documentation of identification methods

## 1.2.5 - UI Consolidation
- **Merged Vendor/Manufacturer Display**: Consolidated redundant "Vendor" and "Manufacturer" columns into single "Mfr" column.
- **Smart Merging**: Shows manufacturer override, or SSDP/SNMP manufacturer, or OUI vendor (in that priority).
- **Edit Modal**: Single "Mfr (Manufacturer)" field overrides all sources.
- **Help Text**: Clarifies that custom mfr overrides both OUI vendor and discovered manufacturer.
- **Removed Redundancy**: No more separate "Manufacturer" column in table (was duplicate data).
- **Column Config**: Removed "Manufacturer" checkbox, kept single "Manufacturer" option for the merged column.
- **Backend**: Still discovers both (vendor from OUI, manufacturer from SSDP) but merges for display.

## 1.2.4 - Database Architecture Optimization
- **Separate OUI Database**: OUI data now in `/var/db/netdiscover/oui.db` (separate from device data).
- **Performance**: PHP controllers never open OUI database (30,000 rows they don't need).
- **Reduced Locking**: UI queries don't lock OUI data, daemon OUI loads don't lock device data.
- **Faster Page Loads**: Inventory/Events/Dashboard read smaller database (no OUI table).
- **Cleaner Schema**: `netdiscover.db` = devices/events/history/overrides, `oui.db` = vendors only.
- **Still Fast**: Python daemon loads OUI once at startup into memory (30K lookups/sec).
- **Created**: `oui_schema.sql` for separate OUI database schema.
- **Updated**: All scripts use correct database paths (OUI vs devices).

## 1.2.3
- **Location Field**: Added user-editable "Location" field with tooltip "Physical and or Logical".
- **Edit Modal**: Location field appears below Model in device edit form.
- **Device Detail View**: Location shown in current device info table.
- **Schema Update**: device_overrides table includes location column.
- **Bulk Operations**: Location preserved during bulk tag operations.
- **Use Cases**: Track physical location (Building/Rack/Room) and/or logical placement (VLAN/Subnet/Department).

## 1.2.2
- **Editable Manufacturer & Model**: Added Manufacturer and Model fields to device edit modal.
- **Override Support**: Custom manufacturer/model stored in device_overrides table.
- **Visual Indicators**: "Custom" badge shown in device detail view for overridden mfr/model.
- **Bulk Operation Preservation**: Bulk tag operations preserve custom manufacturer/model values.
- **Schema Update**: device_overrides table now includes manufacturer and model columns.
- Use case: Correct misidentified devices or add details for generic/unknown hardware.

## 1.2.1
- **Automatic Vendor Backfill**: When OUI database updates, automatically backfills vendor info for existing devices with missing vendors.
- **Device History Tracking**: Vendor updates logged to device_history table with timestamp.
- **UI Feedback**: Update button shows count of backfilled devices.
- **Inventory Auto-Reload**: Table refreshes after OUI update to show new vendor names.
- **CLI Backfill**: `python3 update_oui.py --backfill-only` to re-scan without downloading.
- **API Endpoint**: `/api/netdiscover/service/backfillvendors` for manual backfill trigger.

## 1.2.0 - IEEE OUI Database (SQLite) & Column Customization

### IEEE OUI Database in SQLite:
- **SQLite OUI Table**: MAC vendor data now stored in `oui` table (indexed, O(1) lookups).
- **Automatic Download**: New script (`update_oui.py`) downloads IEEE database directly to SQLite.
- **30,000+ Vendors**: Complete IEEE OUI registry with all registered MAC prefixes.
- **Simplified UI**: Removed file path config, just "Update OUI List from IEEE" button in Settings.
- **Auto-Update on Deploy**: Checks if data is >30 days old, updates automatically.
- **Status Feedback**: Real-time progress with spinner during download (30-60 seconds).
- **Indexed Lookups**: Sub-millisecond vendor resolution with SQL index.
- **Integrated Storage**: OUI data stored alongside device data in same database.
- **Manual CLI**: `python3 /usr/local/opnsense/scripts/NetDiscover/update_oui.py [--force|--check]`
- **Cron Support**: Can be scheduled for automatic monthly updates.
- **CSV Fallback**: Daemon still reads CSV if SQLite OUI table empty (backwards compatible).
- **Removed Fields**: `oui_file` config option removed (no longer needed).

### Column Customization:
- **Column Configuration**: "Columns" button to show/hide any column (except IP and Last Seen).
- **Column visibility saved** to localStorage and persists across sessions.
- **Default column set**: SNMP fields hidden by default, all others visible.
- **Reset to Defaults** button in column config modal.
- **Modal UI**: Checkboxes organized in 2 columns for easy selection.
- Column visibility applies instantly to both headers and data cells.

## 1.1.4
- **Resizable Columns**: Drag column borders to resize (saves width to localStorage per column).
- **Improved Header Styling**: Aligned sort arrows with flexbox layout, better visual hierarchy.
- **Column Labels Cleanup**: Full names (Interface instead of Iface, mDNS Services instead of mDNS).
- **Sort Arrow Alignment**: Icons properly positioned with 6px gap from label text.
- **Overflow Handling**: Table wrapper with horizontal scroll for wide content.
- **Fixed Column Widths**: Set sensible defaults with min-widths to prevent column collapse.
- Resize handles appear on hover (5px transparent zone at column edge).

## 1.1.3
- **UI Improvement**: Moved edit pencil button to right edge of inventory table for better ergonomics.
- Separated View (eye icon) and Edit (pencil icon) into distinct columns.

## 1.1.2
- **SQLite-Only Mode**: Daemon now writes exclusively to SQLite database.
- JSON files no longer regenerated on every scan (reduced disk I/O).
- Emergency fallback: Writes JSON only if SQLite fails.
- PHP controllers still read JSON as fallback if SQLite unavailable.
- Fixed PHP syntax error in HistoryController (triple-quote SQL string).

## 1.1.1
- **Code Cleanup**: Removed debug logging artifacts (startup.log, emergency.log).
- Simplified logging to errors only (no verbose "loop iteration" messages).
- Reduced log noise for production deployments.

## 1.1.0 - Major Backend Upgrade

### Backend Changes (SQLite Migration):
- **SQLite Database Backend**: Migrated from JSON to SQLite for better performance and scalability.
- **Historical Tracking**: Full device history with status changes, attribute changes, and timeline.
- **Database Schema**: Comprehensive schema with devices, device_history, events, device_overrides, scan_stats tables.
- **Auto-cleanup**: Old events (>1000) and old history (>90 days) automatically purged.
- **Hybrid Mode**: Writes to both SQLite and JSON during transition period (backwards compatible).
- **Migration Script**: `migrate_to_sqlite.py` converts existing JSON data to SQLite with backups.
- **Database Helper**: Python module (`db_helper.py`) for all database operations.
- **Performance**: Indexed queries for fast retrieval even with thousands of devices.

### Historical Tracking Features:
- **Device Timeline**: View complete history of every device (status changes, attribute changes, first discovered).
- **Status Change Tracking**: Track every time device goes up/down/new/changed/gone.
- **Attribute Change Tracking**: Track hostname, vendor, and other field changes over time.
- **Uptime Statistics**: Calculate device uptime percentage over configurable periods (7/30/90 days).
- **History API**: New `/api/netdiscover/history/*` endpoints for device history and uptime.

### UI Enhancements (v1.1.0):

#### Filter/Search Persistence:
- **localStorage Persistence**: Remembers status filter, search terms, and sort preferences across page refreshes.
- **Auto-restore**: All filters/search/sort restored when page loads.
- **Clear handling**: Properly clears localStorage when clear buttons clicked.

#### Bulk Actions:
- **Multi-select Checkboxes**: Select multiple devices with checkboxes on each row.
- **Select All**: Checkbox in header with indeterminate state support.
- **Bulk Tag Operation**: Add tags to multiple devices at once.
- **Bulk Clear Overrides**: Remove custom settings from multiple devices.
- **Selection Counter**: Shows "X selected" when devices are checked.
- **Smart Visibility**: Bulk action buttons only appear when devices selected.

#### Device Detail Modal (Read-Only View):
- **Multi-tab Modal**: Current / History / Uptime tabs.
- **Current Tab**: Complete device information in read-only table.
- **History Tab**: Chronological timeline of all device changes.
  - Status changes (up → gone, gone → back)
  - Attribute changes (hostname, vendor, etc.)
  - First discovered event
- **Uptime Tab**: Uptime statistics with large percentage display.
  - Status change count
  - Total downtime duration
  - Uptime percentage over last 30 days
- **Quick Edit Button**: Switch from view to edit mode.
- **Row Clicking**: Click any inventory row to open detail modal.
- **Eye Icon**: Click eye icon for quick detail view.

### Visual Improvements:
- **Color-coded Status Indicators**: Circular dots on each row (🟠 new, 🔷 changed, 🔴 gone, 🟢 up/back).
- **Status dots match dashboard widget colors** for consistency.

## 1.0.1
- **Filter/Search Persistence**: Remembers status filter, search terms, and sort preferences across page refreshes (localStorage).
- **Bulk Actions**: Multi-select devices with checkboxes, bulk tag or clear overrides.
- **Select All checkbox** in table header with indeterminate state support.
- **Bulk action buttons** appear when devices are selected (Tag Selected, Clear Overrides).
- **Selection count indicator** shows "X selected".
- **Device Detail Modal**: Click any row or eye icon to view full device details in read-only modal.
- **Quick Edit button** in detail modal to switch to edit mode.
- **Row click**: Entire row clickable to view details (except checkbox/button areas).
- **Color-coded status dots** on Inventory and Recent Changes rows matching widget colors.

## 1.0.0
- **Major Release**: Dashboard widget fully functional with color-coded status badges.
- Added search boxes to Inventory and Recent Changes tabs with live filtering.
- Added column sorting (click headers) for all major columns in both tabs.
- Sort indicators (▲/▼) show current sort column and direction.
- Hover effects on sortable column headers.
- Combined filter count display shows "X of Y devices" when filters active.
- Default sorts: Inventory by IP ascending, Events by Time descending.
- **Auto-refresh**: Inventory and Events tabs auto-refresh every 30 seconds when visible.
- Manual refresh buttons with loading spinner animation.
- Last updated timestamps displayed on each tab.
- Auto-refresh stops when switching away from tab (performance optimization).
- **Color-coded status indicators**: Circular dots on each row (🟠 new, 🔷 changed, 🔴 gone, 🟢 up/back).

## 0.9.13
- Completely rewrote widget to use ES6 class extending BaseTableWidget (correct OPNsense pattern).
- Used export default syntax and proper async/await patterns.
- Implemented getGridOptions(), getMarkup(), onWidgetTick(), displayError() methods.

## 0.9.12
- Wrapped widget registration in IIFE with OPNsense availability check.
- Changed widget identifier to lowercase 'netdiscover' to match metadata.

## 0.9.11
- Fixed widget metadata XML to use correct OPNsense <metadata> format with filename/endpoints/translations.

## 0.9.10
- Fixed widget to use correct OPNsense.widget() registration pattern.
- Corrected widget paths to /usr/local/opnsense/www/js/widgets/.
- Simplified XML metadata to proper OPNsense format.

## 0.9.9
- Rewrote widget to use OPNsense standard widget pattern (removed ES6 modules/imports).

## 0.9.8
- Fixed widget installation path (/usr/local/www/widgets/ instead of /usr/local/opnsense/www/js/widgets/).

## 0.9.7
- Enhanced Dashboard Widget with color-coded status badges and link to full inventory.
- Created ROADMAP.md with future enhancements.

## 0.9.6
- Add proper padding to Settings tab content (15px).

## 0.9.5
- Replace form object rendering with manual HTML form fields for Settings tab.

## 0.9.4
- Fix Settings tab Volt template syntax error (removed |raw filter causing cache issues).

## 0.9.3
- Fix CSV export causing TypeError crash (Response object return issue).

## 0.9.2
- Fix Settings tab displaying inventory content instead of configuration form.
- Fix Inventory tab appearing blank on first load (now populates immediately).
- Version number now auto-populated by deploy.sh from Makefile.

## 0.6.2
- Fix packaging: install rc script to `/usr/local/etc/rc.d/netdiscoverd` so `service netdiscoverd ...` works.
- Fix default `oui_file` path in the model.

## 0.6.1
- UI/layout fixes (see prior notes).
