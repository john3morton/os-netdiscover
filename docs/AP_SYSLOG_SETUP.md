# WiFi AP Detection via Syslog - Quick Start Guide

## Overview

v2.0.2 adds **syslog-based AP detection** - works with **consumer APs without SNMP!**

**Works with:**
- Ubiquiti UniFi
- TP-Link Omada
- OpenWrt / DD-WRT
- MikroTik
- AsusWRT / Merlin
- Any AP using hostapd

**No SNMP configuration needed!** 📡

---

## How It Works

### 1. APs Send Logs to OPNsense
Your APs are probably already logging WiFi events:
```
Dec 27 10:15:30 hostapd: STA aa:bb:cc:dd:ee:ff associated
Dec 27 10:20:45 hostapd: STA aa:bb:cc:dd:ee:ff disassociated
```

### 2. NetDiscover Parses Logs
Every scan cycle, daemon:
- Reads `/var/log/messages` and rotated logs
- Extracts client MAC addresses
- Finds which AP they connected to
- Updates inventory

### 3. "Via AP" Column Populates
- Shows AP name for WiFi clients
- Empty for wired devices
- Updates as clients roam

---

## Verification Steps

### Step 1: Check if Syslog Has WiFi Events
```bash
# Look for WiFi association messages
grep -i "associated\|STA\|Client.*connected" /var/log/messages | tail -20

# If you see lines with MAC addresses, syslog detection will work!
```

**Example good output:**
```
Dec 27 10:15:30 AP-Living hostapd[1234]: STA aa:bb:cc:dd:ee:ff IEEE 802.11: associated
Dec 27 10:20:30 AP-Bedroom hostapd[5678]: STA 11:22:33:44:55:66 IEEE 802.11: associated
```

**If empty:** APs might not be sending logs to OPNsense (see Configuration below)

---

### Step 2: Test Syslog Parser
```bash
# Run parser manually to see what it finds
python3 /usr/local/opnsense/scripts/NetDiscover/ap_syslog_parser.py

# Should show:
# Found X client associations from syslog:
#   AA:BB:CC:DD:EE:FF → AP-Living (at 2025-12-27 10:15:30)
#   11:22:33:44:55:66 → AP-Bedroom (at 2025-12-27 10:20:30)
```

---

### Step 3: Wait for Next Scan
```bash
# Daemon runs every 120 seconds (default)
# Wait 2-3 minutes after deploy, then check:

sqlite3 /var/db/netdiscover/netdiscover.db \
  "SELECT ip, hostname, ap_name, connected_to_ap FROM devices WHERE connected_to_ap != '';"

# Should show devices with AP associations!
```

---

### Step 4: Check in UI
1. Go to Inventory tab
2. Look at "Via AP" column
3. WiFi devices should show AP name!

---

## Configuration (Optional)

### If APs Don't Log to OPNsense

#### Option 1: Configure AP Syslog
Most APs have syslog settings:

**UniFi Controller:**
1. Settings → System → Remote Logging
2. Enable Remote Logging
3. Host: <OPNsense IP>
4. Port: 514

**OpenWrt:**
```
uci set system.@system[0].log_ip='<OPNsense_IP>'
uci commit system
/etc/init.d/log restart
```

**AsusWRT/Merlin:**
1. Administration → System
2. Enable Syslog
3. Server: <OPNsense IP>

#### Option 2: Check OPNsense Syslog
```bash
# Make sure OPNsense is receiving logs
tail -f /var/log/messages | grep -i "hostapd\|STA\|associated"
```

---

## Troubleshooting

### "Via AP" Still Empty After 10 Minutes

**Check 1: Are APs identified?**
```bash
sqlite3 /var/db/netdiscover/netdiscover.db \
  "SELECT ip, hostname, device_type FROM devices WHERE device_type LIKE '%AP%';"
```

**Check 2: Do syslogs have WiFi events?**
```bash
grep -c "associated\|STA.*IEEE" /var/log/messages
# Should return non-zero count
```

**Check 3: Can parser find associations?**
```bash
python3 /usr/local/opnsense/scripts/NetDiscover/ap_syslog_parser.py
# Should list client MACs and APs
```

**Check 4: Is daemon running?**
```bash
service netdiscoverd status
tail -5 /var/db/netdiscover/startup.log
```

---

## Advantages vs SNMP

| Feature | Syslog | SNMP |
|---------|--------|------|
| **Configuration** | None (if logging) | SNMP on each AP |
| **Security** | Read-only logs | SNMP community string |
| **Consumer APs** | ✅ Works | ❌ Often not supported |
| **Performance** | Fast (local file) | Network queries |
| **Historical** | ✅ Can parse old logs | ❌ Current state only |
| **Reliability** | Depends on logging | Depends on SNMP |

---

## Supported Log Formats

### UniFi / Ubiquiti
```
hostapd: ath0: STA aa:bb:cc:dd:ee:ff IEEE 802.11: associated
```

### TP-Link Omada
```
Client aa:bb:cc:dd:ee:ff connected to AP-Office
```

### OpenWrt / hostapd
```
hostapd: AP-Living STA aa:bb:cc:dd:ee:ff IEEE 802.11: associated
```

### MikroTik
```
wireless,info wlan1 connected, AA:BB:CC:DD:EE:FF
```

### AsusWRT
```
WLAN access accepted: aa:bb:cc:dd:ee:ff
```

### Generic
```
STA aa:bb:cc:dd:ee:ff associated
```

---

## Testing

### Manual Test
```bash
# 1. Check what syslog parser finds
python3 /usr/local/opnsense/scripts/NetDiscover/ap_syslog_parser.py

# 2. Manually inject test log entry
logger "hostapd: STA AA:BB:CC:DD:EE:FF IEEE 802.11: associated"

# 3. Run parser again - should see new entry
python3 /usr/local/opnsense/scripts/NetDiscover/ap_syslog_parser.py | grep AA:BB:CC

# 4. Wait for next scan cycle
# 5. Check database for that MAC
```

---

## Expected Results

**Within 5 minutes of deployment:**
- ✅ Parser finds client associations in logs
- ✅ Daemon applies associations on next scan
- ✅ "Via AP" column shows AP names
- ✅ Detail modal shows "Connected Via: 📡 AP-Living-Room"

**No SNMP configuration needed!** 🎉

---

## Fallback Behavior

**Priority:**
1. **Try syslog** (works with all APs if logging)
2. **Fall back to SNMP** (if explicitly enabled and APs support it)

**Result:** Best of both worlds! Works with consumer gear, enhanced by SNMP if available.

---

## Need Help?

If "Via AP" column stays empty:
1. Check syslog for WiFi events
2. Run parser manually
3. Check daemon startup log
4. Share results for troubleshooting

**Most likely:** Just need to wait 2-3 scan cycles (4-6 minutes) after deployment!

