# Network Topology Discovery (v2.0.0 Planned)

## Goal

Discover the network path and connection points for each device:
1. **Which AP** a WiFi device is connected to
2. **Which switch port** a wired device is on
3. **Network path** from device to router
4. **Layer 2 topology** (switching path)

---

## Approach 1: WiFi AP Client Detection

### Method 1: SNMP on Access Points
**Works with:** Most enterprise APs (UniFi, Cisco, Aruba, etc.)

**Query:**
```
# Get client table from AP
snmpwalk -v2c -c public <AP_IP> 1.3.6.1.4.1.14988.1.1.1.2.1.1
# Returns: List of connected clients with MAC addresses
```

**Implementation:**
1. Identify APs in network (device_type = "WiFi Access Point")
2. For each AP, query client table via SNMP
3. Match client MACs to devices in inventory
4. Store: device.connected_to_ap = "192.168.1.100" (AP IP)
5. Display: "Connected via: AP-Living-Room (192.168.1.100)"

**Pros:** ✅ Works with most APs, ✅ Real-time data  
**Cons:** ❌ Requires SNMP enabled on APs, ❌ Vendor-specific OIDs

---

### Method 2: Controller API Integration
**Works with:** UniFi, Cisco WLC, Meraki, etc.

**UniFi Example:**
```bash
# Query UniFi controller API
curl -k https://controller:8443/api/s/default/stat/sta
# Returns: All connected clients with AP info
```

**Implementation:**
1. Detect controller (UniFi/Cisco WLC/etc.)
2. API authentication
3. Query client associations
4. Map to inventory devices
5. Store AP association

**Pros:** ✅ Rich data (signal strength, bandwidth, etc.), ✅ Centralized  
**Cons:** ❌ Requires controller credentials, ❌ Vendor-specific APIs

---

### Method 3: Wireless Interface Scanning
**Works with:** OPNsense with WiFi interfaces

**Command:**
```bash
# On OPNsense with WiFi interface
ifconfig wlan0 list sta
# Shows: Associated stations
```

**Implementation:**
1. Check if OPNsense has WiFi interfaces
2. Query associated stations
3. Match to devices
4. Only works if OPNsense is the AP

**Pros:** ✅ No external queries, ✅ Built-in  
**Cons:** ❌ Only if OPNsense is AP, ❌ Limited use case

---

## Approach 2: Switch Port Mapping

### Method 1: SNMP MAC Table Queries
**Works with:** Managed switches with SNMP

**Query:**
```bash
# Get MAC address table from switch
snmpwalk -v2c -c public <SWITCH_IP> 1.3.6.1.2.1.17.7.1.2.2.1.2
# Returns: MAC → Port mapping
```

**Implementation:**
1. Identify switches in network
2. Query MAC address table via SNMP
3. Match device MACs to switch ports
4. Store: device.switch_port = "switch1:ge-0/0/24"
5. Display: "Connected to: Core-Switch port 24"

**Pros:** ✅ Standard MIB, ✅ Most switches support  
**Cons:** ❌ Requires SNMP on switches, ❌ Complex port indexing

---

### Method 2: LLDP/CDP Discovery
**Works with:** Network devices advertising LLDP/CDP

**What LLDP Provides:**
- Neighbor device name
- Neighbor port
- Neighbor IP
- System capabilities

**Implementation:**
1. Listen for LLDP/CDP packets (multicast)
2. Build neighbor adjacency map
3. Infer topology from neighbor relationships
4. Display: "Path: device → switch1:port5 → switch2:port10 → router"

**Pros:** ✅ Automatic discovery, ✅ No credentials needed  
**Cons:** ❌ Only network gear, ❌ Doesn't show end devices

---

## Approach 3: ARP Table Analysis

### Method: Bridge/Router ARP Tables
**Works with:** Any router with ARP visibility

**Query:**
```bash
# Get ARP table from router with interface info
arp -an | grep bridge0
# Shows: IP, MAC, and interface
```

**Implementation:**
1. Parse router ARP table
2. Extract interface per device
3. If interface is an AP or switch, that's the connection point
4. Store: device.via_interface = "ixl1.vlan10"

**Pros:** ✅ Simple, ✅ Works on OPNsense  
**Cons:** ❌ Only shows immediate interface, ❌ Not detailed

---

## Approach 4: Traceroute-Based Path Discovery

### Method: Layer 3 Path Tracing
**Works with:** Any IP device

**Command:**
```bash
traceroute -n 192.168.1.50
# Shows: IP hops from router to device
```

**Implementation:**
1. Run traceroute from OPNsense to device
2. Record intermediate hops
3. Map hops to known devices in inventory
4. Display: "Path: router → 192.168.1.1 (Core Switch) → 192.168.1.10 (AP)"

**Pros:** ✅ Shows layer 3 path, ✅ Built-in command  
**Cons:** ❌ Requires ICMP, ❌ Slow, ❌ Layer 3 only (not layer 2 switching)

---

## Recommended Implementation (v2.0.0)

### Phase 1: Basic AP Detection
1. **SNMP AP Client Tables** (if SNMP enabled)
2. **Interface-based** (from ARP table)
3. **Display:** "Connected via: [interface or AP name]"

### Phase 2: Switch Port Mapping
1. **SNMP MAC tables** from switches
2. **Store:** switch_name, port_number
3. **Display:** "Switch: Core-SW-1, Port: 24"

### Phase 3: Full Topology
1. **LLDP discovery** for device relationships
2. **Build topology graph**
3. **Visualize:** Device → Switch → Router path

---

## Data Schema (v2.0.0)

```sql
-- Add to devices table
via_interface TEXT,      -- OPNsense interface (e.g., "ixl1.vlan10")
connected_to_ap TEXT,    -- AP IP address
ap_name TEXT,            -- Friendly AP name
switch_name TEXT,        -- Switch hostname
switch_port TEXT,        -- Port number/name
network_path TEXT        -- JSON: [{device, port}, ...]
```

---

## UI Mockup

### Inventory Table:
```
IP | MAC | Hostname | Via | ...
192.168.1.50 | aa:bb... | iPhone | 📡 AP-Living → Port Ethernet
```

### Device Detail:
```
Network Connection:
  Via Interface: vlan0.33 (Guest Network)
  Access Point: AP-Living-Room (192.168.1.100)
    Signal: -65 dBm
    Channel: 36 (5GHz)
  Switch: Core-SW-1 (192.168.1.1)
    Port: ge-0/0/24
  Path: device → AP → Switch:24 → Router
```

---

## Implementation Effort

| Feature | Difficulty | Time | Prerequisites |
|---------|-----------|------|---------------|
| ARP interface detection | Easy | 2h | None |
| SNMP AP clients | Medium | 4h | SNMP on APs |
| SNMP switch MAC tables | Medium | 6h | SNMP on switches |
| LLDP discovery | Hard | 8h | Raw packet capture |
| Full topology graph | Hard | 12h | All above |

**Total:** ~32 hours for complete topology discovery

---

## Quick Win: Interface Detection (Can Do Now)

**What we CAN do easily:**
- Parse OPNsense ARP table
- Extract interface per device
- Show: "Via: ixl1.vlan10 (Guest Network)"

**Pros:** 
- ✅ No external dependencies
- ✅ Works immediately
- ✅ Shows which VLAN/interface
- ✅ 1-2 hours work

**Cons:**
- ❌ Doesn't show specific AP
- ❌ Doesn't show switch port
- ❌ Just immediate interface

---

## Current Workarounds

**For WiFi AP detection:**
1. Check hostname patterns (`unifi-ap-*`, `AP-*`)
2. Look at vendor (Ubiquiti, Cisco Meraki, etc.)
3. Check for `_airplay._tcp` mDNS services
4. Manually tag APs in inventory

**For connection inference:**
1. Subnet/VLAN tells you network segment
2. Interface field shows OPNsense interface
3. SNMP sysName on switches shows hostname

---

## Would You Like Me To:

**A)** Implement quick win (interface detection from ARP) - 1-2 hours  
**B)** Plan full v2.0.0 topology feature - document and roadmap  
**C)** Deploy v1.7.2 now and revisit topology in next session  

**Recommend:** Deploy v1.7.2 now (stable, feature-complete), plan topology for v2.0.0 as major feature.

Current session is at 57% token usage (~574K) - we can do option A if you want!

