# Device Fingerprinting & Identification Sources

## Currently Implemented (v1.2.x)

### ✅ IEEE OUI Database
- **Source:** https://standards-oui.ieee.org/oui/oui.txt
- **What:** First 3 octets of MAC → Manufacturer
- **Example:** `58:9C:FC` → "Apple, Inc."
- **Limitation:** Only identifies manufacturer, not specific product

### ✅ SSDP/UPnP Device Description
- **Already implemented** in NetDiscover
- **Source:** Device self-reports via UPnP XML
- **Fields:** friendlyName, manufacturer, modelName, modelNumber
- **Example:** Printer reports "HP LaserJet Pro MFP M428fdw"
- **Coverage:** Smart devices (printers, NAS, IoT, media players)

### ✅ mDNS/Bonjour Services
- **Already implemented** in NetDiscover  
- **Source:** Device advertises services
- **Example:** `_airplay._tcp` → Likely Apple TV/Mac
- **Pattern matching:** Can infer device type from service combinations

### ✅ SNMP sysName/sysDescr
- **Already implemented** in NetDiscover
- **Source:** SNMP v2c queries
- **Fields:** sysName, sysDescr, sysObjectID
- **Example:** "Cisco IOS Software, C2960 Software"
- **Coverage:** Network equipment, servers, managed devices

---

## Additional Free Sources (Can Integrate)

### 1. Wireshark Manufacturer Database (Extended)
**Source:** https://www.wireshark.org/download/automated/data/manuf

**What It Provides:**
- Extended OUI with some model hints
- More detailed than standard IEEE OUI
- Includes short manufacturer names
- Some entries have device type hints

**Format:**
```
58:9C:FC    Apple       Apple, Inc.
58:9C:FC:00:00:00/36    Apple   iPhone
```

**Integration Effort:** Easy - similar to OUI parsing
**Benefit:** More specific device identification for some vendors

---

### 2. MAC Address to Device Type Patterns
**Community-maintained lists on GitHub:**

- **FingerBank** (open source tier): https://fingerbank.org/
  - 100K+ device signatures
  - MAC + DHCP fingerprints
  - Free tier: 300 lookups/day API
  - Could batch lookup unknowns

- **Device detector patterns:**
  - Android devices: MAC patterns + hostname regex
  - iOS devices: Specific OUI ranges + mDNS patterns
  - IoT devices: Common hostname prefixes

**Example Patterns:**
```
MAC: DC:A6:32:* + hostname: android-* → Android Phone
MAC: 10:DD:B1:* + mDNS: _airplay → Apple TV
MAC: 68:C6:3A:* + hostname: ESP_* → ESP32 IoT Device
```

---

### 3. DHCP Fingerprinting
**Source:** Device DHCP requests

NetDiscover could capture from dnsmasq logs:
- **DHCP Option 60** (Vendor Class): `"MSFT 5.0"` → Windows
- **DHCP Option 55** (Parameter Request List): Unique per OS
- **DHCP hostname patterns**

**Example:**
```
Vendor Class: "dhcpcd-6.8.2:Linux" → Linux device
Vendor Class: "MSFT 5.0" → Windows
Hostname: "android-*" → Android
```

**Integration:** Parse `/var/log/dnsmasq.log` or hook into dnsmasq events

---

### 4. Hostname Pattern Matching
**Free - we already have hostnames!**

Common patterns we can detect:
```
Prefix Patterns:
  android-*          → Android device
  iPhone*            → iPhone
  iPad*              → iPad
  ESP_*              → ESP8266/ESP32 IoT
  HP*                → HP Printer
  DESKTOP-*          → Windows 10/11
  raspberrypi*       → Raspberry Pi
  
Service-based:
  *-nas              → NAS device
  *-printer          → Printer
  *-camera           → IP Camera
```

**Integration:** Simple regex matching, no external dependency

---

### 5. Open Port Signatures
**Free - we already scan ports!**

Port combinations reveal device types:
```
Ports: 80, 443, 631, 9100 → Printer
Ports: 139, 445, 5000, 5001 → NAS (SMB + DSM)
Ports: 22, 80, 443, 8080 → Linux server/IoT
Ports: 3389, 135, 139, 445 → Windows machine
Ports: 554, 8000, 8080 → IP Camera
Port: 9100 only → Network printer (raw/JetDirect)
```

**Integration:** Pattern matching on open_ports array

---

### 6. mDNS Service Combinations
**Free - we already collect services!**

Service patterns reveal specific devices:
```
_airplay._tcp + _raop._tcp → Apple TV/HomePod
_airplay._tcp + _ssh._tcp → macOS
_smb._tcp + _afpovertcp._tcp → macOS/Synology NAS
_hap._tcp → HomeKit device
_googlecast._tcp → Chromecast/Google Home
_http._tcp + _printer._tcp → Network printer
_ipp._tcp → Modern printer (AirPrint)
```

**Integration:** Pattern matching on mdns_services array

---

### 7. Banner Grabbing Enhancement
**Free - we already do TCP probes!**

Current: We probe ports but don't read banners  
Enhancement: Read first line of response

**Examples:**
```
Port 80 banner: "Server: Apache/2.4.41 (Ubuntu)" → Ubuntu Linux
Port 22 banner: "SSH-2.0-OpenSSH_8.2p1 Ubuntu-4" → Ubuntu
Port 23 banner: "DD-WRT v24" → DD-WRT router
FTP banner: "220 Synology FTP" → Synology NAS
```

**Integration:** Modify TCP probe to read first 512 bytes

---

### 8. Nmap OS Detection Fingerprints
**Source:** https://github.com/nmap/nmap/blob/master/nmap-os-db

**What It Provides:**
- OS fingerprints based on TCP/IP stack behavior
- ~3000 device signatures
- Very accurate for OS detection

**Integration Effort:** Complex (need to implement TCP/IP fingerprinting)
**Benefit:** Accurate OS identification

---

## Recommendation: Quick Wins

### Phase 1: Pattern Matching (Easy - No External Deps)

1. **Hostname Patterns** ✨ (30 minutes)
   ```python
   if hostname.startswith('android-'): device_type = 'Android Phone'
   if hostname.startswith('iPhone'): device_type = 'iPhone'
   if 'ESP_' in hostname: device_type = 'ESP32/IoT'
   ```

2. **Port Signatures** ✨ (1 hour)
   ```python
   if {631, 9100} <= set(open_ports): device_type = 'Printer'
   if {139, 445, 5000} <= set(open_ports): device_type = 'NAS'
   ```

3. **mDNS Service Patterns** ✨ (1 hour)
   ```python
   if '_airplay._tcp' in services and '_raop._tcp' in services:
       device_type = 'Apple TV'
   ```

### Phase 2: External Database (Medium)

4. **Wireshark Manuf** ✨ (2 hours)
   - Download https://www.wireshark.org/download/automated/data/manuf
   - Parse extended format (includes model hints)
   - Store in oui.db with model column

### Phase 3: Advanced (Complex)

5. **FingerBank API** (4 hours)
   - Free tier: 300 lookups/day
   - Batch unknown devices
   - Cache results

6. **Banner Grabbing** (2 hours)
   - Enhance TCP probe to read response
   - Store banner text
   - Pattern match common strings

---

## Implementation Priority

| Feature | Effort | Benefit | Dependencies |
|---------|--------|---------|--------------|
| **Hostname Patterns** | Low | High | None |
| **Port Signatures** | Low | High | None |
| **mDNS Service Patterns** | Low | Medium | None |
| **Wireshark Manuf** | Medium | Medium | Internet |
| **Banner Grabbing** | Medium | High | None |
| **FingerBank API** | Medium | Very High | API Key |
| **Nmap Fingerprints** | High | Very High | Complex |

---

## Example: Hostname Pattern Implementation

```python
def guess_device_type_from_hostname(hostname):
    """Infer device type from hostname patterns"""
    h = hostname.lower()
    
    # Mobile devices
    if h.startswith('android-'): return 'Android Phone'
    if h.startswith('iphone'): return 'iPhone'
    if h.startswith('ipad'): return 'iPad'
    
    # IoT/Embedded
    if 'esp_' in h or 'esp-' in h: return 'ESP32/ESP8266'
    if 'raspberry' in h: return 'Raspberry Pi'
    if 'tasmota' in h: return 'Tasmota Device'
    
    # Printers
    if any(x in h for x in ['hp', 'canon', 'epson', 'brother']):
        if 'laserjet' in h or 'inkjet' in h or 'printer' in h:
            return 'Printer'
    
    # NAS
    if 'nas' in h or 'synology' in h or 'qnap' in h:
        return 'NAS'
    
    # Cameras
    if 'camera' in h or 'ipc' in h or 'ipcam' in h:
        return 'IP Camera'
    
    # Networking
    if any(x in h for x in ['switch', 'router', 'ap-', 'wap']):
        return 'Network Device'
    
    return None
```

---

## Would You Like Me To Implement Any?

I can quickly add:
1. **Hostname pattern matching** (30 min - instant results)
2. **Port signature detection** (1 hour - great accuracy)
3. **mDNS service pattern matching** (1 hour - good for smart devices)

These are all **free, no external dependencies**, and would significantly improve device identification!

Should I proceed with implementing pattern-based detection?

