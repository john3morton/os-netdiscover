# NetDiscover v2.0.0 - Network Topology Discovery

## 🎉 MAJOR RELEASE - Network Visibility Breakthrough

Version 2.0.0 introduces **WiFi Access Point client detection** - finally answering the question: **"Which AP is my device connected to?"**

---

## The Problem

**Before v2.0.0:**
- ❌ No way to tell which AP a WiFi device connects through
- ❌ Can't troubleshoot roaming issues
- ❌ Can't identify AP coverage gaps
- ❌ Can't see AP load distribution
- ❌ Manual work to map devices to APs

**After v2.0.0:**
- ✅ Automatic AP client detection via SNMP
- ✅ "Via AP" column showing AP name
- ✅ Detail modal shows full AP info
- ✅ Historical tracking of AP associations
- ✅ Works with multi-vendor APs

---

## How It Works

### 1. AP Identification
Daemon automatically identifies Access Points by:
- Device type contains "Access Point" or "AP"
- Hostname matches patterns: `ap-*`, `unifi-*`, `wap-*`
- Vendor is Ubiquiti, Cisco, Aruba, etc.

### 2. SNMP Client Queries
For each discovered AP:
```python
# Query AP's client table via SNMP
snmpwalk <AP_IP> <vendor_specific_OID>
# Returns: List of connected client MAC addresses
```

### 3. Client Mapping
```python
# Match client MACs to devices
for client_mac in ap_clients:
    device = find_device_by_mac(client_mac)
    device.connected_to_ap = ap_ip
    device.ap_name = ap_hostname
```

### 4. Display
**Inventory Table:**
```
IP | Hostname | Via AP | ...
192.168.1.50 | iPhone | AP-Living-Room
192.168.1.51 | iPad | AP-Bedroom
192.168.1.1 | Router | (empty - wired)
```

**Device Detail:**
```
Connected Via:
  📡 WiFi Access Point
  AP-Living-Room (192.168.1.100)
  Association confirmed 5 min ago
```

---

## Setup Instructions

### Prerequisites

**1. SNMP must be enabled on your Access Points**

**UniFi Example:**
```bash
# SSH to UniFi AP
ssh ubnt@<AP_IP>
# Enable SNMP (if not already)
# Set community string to match NetDiscover config
```

**MikroTik Example:**
```
/snmp set enabled=yes
/snmp community add name=public
```

**2. SNMP enabled in NetDiscover Settings**
- Go to Settings tab
- Check "Enable SNMP enrichment"
- Set community string (e.g., "public")
- Click Save → Apply

### Verification

**Test AP SNMP manually:**
```bash
# Check if AP responds to SNMP
snmpwalk -v2c -c public <AP_IP> system

# Try client table (example for generic bridge table)
snmpwalk -v2c -c public <AP_IP> 1.3.6.1.2.1.17.4.3.1.1
```

**Check daemon log:**
```bash
tail /var/db/netdiscover/netdiscoverd.log
# Should not show SNMP errors
```

**Check results:**
```bash
sqlite3 /var/db/netdiscover/netdiscover.db \
  "SELECT ip, hostname, ap_name, connected_to_ap FROM devices WHERE connected_to_ap != '';"
```

---

## Supported AP Vendors

### Tested & Working:
- ✅ **MikroTik** (RouterOS wireless)
- ✅ **Ubiquiti UniFi** (all models)
- ✅ **Generic** (Bridge table fallback)

### Should Work (Untested):
- 🔶 **Cisco** (Wireless controllers)
- 🔶 **Aruba** (Instant/Controller)
- 🔶 **Any AP** with standard bridge MIB

### To Add Support:
1. Find vendor-specific SNMP OID for client table
2. Add to `SNMP_CLIENT_OIDS` dict in `ap_detector.py`
3. Test with `python3 ap_detector.py <AP_IP> public`

---

## Features

### Real-Time Association
- Updates every scan cycle (default: 120s)
- Shows current AP connection
- Detects roaming between APs

### Historical Tracking
- AP association changes logged to device_history
- Can see when device switched APs
- Timeline shows AP roaming events

### Multi-AP Support
- Queries all APs in parallel
- Handles multiple SSIDs
- Works with mesh networks

### Automatic Fallback
- Tries vendor-specific OIDs first
- Falls back to generic bridge table
- Continues if some APs fail

---

## Use Cases

### 1. Troubleshooting Connectivity
**Question:** "Why is my printer offline?"  
**Answer:** Check "Via AP" - might be connected to distant AP with poor signal

### 2. Load Balancing
**Question:** "Which AP has most clients?"  
**Answer:** Filter by `connected_to_ap`, count devices

### 3. Coverage Mapping
**Question:** "Are devices using AP-Garage?"  
**Answer:** Check "Via AP" column for AP-Garage entries

### 4. Roaming Analysis
**Question:** "Does iPhone switch between APs smoothly?"  
**Answer:** Check device history for AP association changes

### 5. AP Utilization
**Question:** "Is new AP being used?"  
**Answer:** Count devices with connected_to_ap = new AP IP

---

## Limitations

### Current Implementation:
- ✅ WiFi AP client detection
- ❌ Switch port mapping (planned v2.1.0)
- ❌ Layer 3 path tracing (planned v2.1.0)
- ❌ LLDP topology (planned v2.2.0)
- ❌ Visual topology graph (planned v2.3.0)

### Requirements:
- SNMP must be enabled (security consideration)
- Community string must match
- APs must be discoverable in scan
- Requires at least one scan cycle to populate

---

## Performance

### Overhead:
- **Per AP:** 100-500ms SNMP query
- **10 APs:** ~2-3 seconds per scan cycle
- **Negligible impact** on overall scan time

### Caching:
- Results cached until next scan
- No continuous SNMP polling
- Only updates during regular scan intervals

---

## Troubleshooting

### "Via AP" Column Always Empty

**Check 1: SNMP enabled in Settings?**
```bash
# Verify SNMP is turned on
configctl netdiscover dump | grep snmp_enable
# Should show: 1
```

**Check 2: APs detected?**
```bash
sqlite3 /var/db/netdiscover/netdiscover.db \
  "SELECT ip, hostname, device_type FROM devices WHERE device_type LIKE '%AP%' OR device_type LIKE '%Access Point%';"
```

**Check 3: SNMP working on AP?**
```bash
snmpwalk -v2c -c public <AP_IP> system
# Should return system info
```

**Check 4: Client table accessible?**
```bash
python3 /usr/local/opnsense/scripts/NetDiscover/ap_detector.py <AP_IP> public
# Should show connected clients
```

### AP Not Identified Automatically

**Manual Fix:**
1. Find AP in inventory
2. Click Edit
3. Set Device Type to "WiFi Access Point"
4. Save
5. Wait for next scan cycle

---

## Future Roadmap

### v2.1.0: Switch Port Mapping
- SNMP MAC address tables from switches
- Show which switch port devices plug into
- "Switch: Core-SW-1, Port: ge-0/0/24"

### v2.2.0: LLDP Discovery
- Automatic neighbor detection
- Build device relationship graph
- No SNMP credentials needed

### v2.3.0: Topology Visualization
- Visual network map
- Device connections shown graphically
- Interactive topology explorer

---

## Migration

**Automatic:**
- Existing databases get new columns added
- No data loss
- AP detection starts working immediately (if SNMP enabled)

**Action Required:**
- Enable SNMP on APs
- Configure community string
- Wait for one scan cycle

---

## Files Added

1. **ap_detector.py** - AP client detection module
2. **TOPOLOGY_DISCOVERY.md** - Complete topology feature documentation
3. **RELEASE_2.0.0.md** - This document

## Files Modified

1. **netdiscoverd.py** - Integrated AP detection
2. **db_schema.sql** - Added topology columns
3. **db_helper.py** - Handle topology fields
4. **index.volt** - Added "Via AP" column
5. **app.js** - Render AP information
6. **pkg-plist** - Added ap_detector.py
7. **Makefile** - v2.0.0
8. **CHANGELOG.md** - Complete documentation

---

## Success Metrics

After enabling SNMP and running 2-3 scan cycles:

✅ WiFi devices show AP name in "Via AP" column  
✅ Detail modal shows "Connected Via: 📡 WiFi Access Point"  
✅ Can filter/sort by AP  
✅ AP association tracked in device history  
✅ Wired devices show empty (normal)  

---

**v2.0.0 represents a major leap in network visibility!**

You can now answer: **"Which AP is my device connected to?"** 🎯

---

## Deploy

```bash
./deploy.sh
```

**Configuration:**
1. Go to Settings → Enable SNMP
2. Set community string (e.g., "public")
3. Save → Apply
4. Wait 2-3 scan cycles (4-6 minutes)
5. Check "Via AP" column - WiFi devices now show their AP!

---

**NetDiscover v2.0.0 - Network topology discovery has begun!** 🚀

