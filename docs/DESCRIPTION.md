# NetDiscover OPNsense Plugin — Overview & Usage

## What it does
- Discovers hosts across local subnets/VLANs using passive sources (ARP, dnsmasq leases) and multicast listeners (SSDP/UPnP, mDNS/Bonjour, LLMNR, NBNS).
- Optional active enrichment: ping sweep, TCP port probe, SNMP sysName/sysDescr, UPnP XML fetch.
- Maintains an inventory with change tracking (new/changed/gone) and recent events.
- UI provides filtering, search, CSV export, and a dashboard widget with recent events.

## Outputs / state
- Inventory JSON: `/var/db/netdiscover/devices.json`
- Persistent state (devices + event ring buffer): `/var/db/netdiscover/state.json`
- PID: `/var/run/netdiscoverd.pid`

## Build (developer workflow on the firewall)
```sh
scp -r "D:/workspace/personal/os-netdiscover-opnsense-plugin/*" root@192.168.3.1:/usr/local/src/plugins/net-mgmt/os-netdiscover/

ssh root@192.168.3.1

cd /usr/local/src/plugins/net-mgmt/os-netdiscover 

make package"
```

## Install / reinstall
```sh
pkg add -f ./work/pkg/opnsensenetdiscover-devel-[M.m.p].pkg
configctl template reload OPNsense/NetDiscover
configctl webgui restart   # optional, helps pick up UI assets
```

## Enable & service control
1) In UI: Services > NetDiscover > enable, adjust settings, Save, then Apply.  
2) Service commands:
```sh
service netdiscoverd restart
service netdiscoverd status
```

## Configuration (UI fields → rc.conf.d → daemon flags)
- `Enable`: turn on service (renders `/etc/rc.conf.d/netdiscoverd`).
- `Scan interval (seconds)`: main loop sleep; min 30.
- `Active scan (ping sweep)`: ICMP probe each host in subnets (capped by max hosts, rate-limit).
- `Reverse DNS enrichment`: PTR lookups for seen IPs without hostnames.
- `Interfaces`: comma-separated interface names (blank = all with IPv4).
- `Max hosts per subnet`: guardrail for active scan.
- `Ping rate limit (ms)`: delay between pings in active scan.
- SSDP: enable listener; optionally fetch UPnP XML with per-device rate limit.
- mDNS / LLMNR / NBNS: enable listeners for names/services.
- TCP probe: quick connect scan of `Probe ports` with per-connection timeout.
- SNMP: v2c `snmpget` of sysName/sysDescr for provided communities; per-device rate limit + timeout.
- `OUI vendor CSV file`: path to vendor mapping (default sample bundled).

## Web UI usage
- Path: Services → NetDiscover.
- Inventory tab:
  - Status filters: All/New/Changed/Gone.
  - Search across IP/MAC/hostname/vendor/type/ports/services/SNMP/interface/subnet/status.
  - CSV export honors current status filter and search.
- Recent Changes tab: event list with timestamps and details.
- Dashboard widget: shows totals (up/new/changed/gone) and latest events (enable via Dashboard add widget).

## Files of interest
- Service script: `/usr/local/opnsense/scripts/NetDiscover/netdiscoverd.py`
- rc.d wrapper: `/usr/local/etc/rc.d/netdiscoverd`
- Template output: `/etc/rc.conf.d/netdiscoverd`

## Troubleshooting quick hits
- If service is “not found”: `ls -la /usr/local/etc/rc.d/netdiscoverd`
- Template/render issues: `grep -nEi 'NetDiscover|template|traceback|error' /var/log/configd/latest.log | tail -n 200`
- Verify generated config: `sed -n '1,200p' /etc/rc.conf.d/netdiscoverd`

