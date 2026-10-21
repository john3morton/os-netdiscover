# NetDiscover OPNsense Plugin — Overview & Usage

## What it does
- Discovers hosts across local subnets/VLANs using passive sources (ARP, dnsmasq leases) and multicast listeners (SSDP/UPnP, mDNS/Bonjour, LLMNR, NBNS).
- Optional active enrichment: ping sweep, TCP port probe, SNMP sysName/sysDescr, UPnP XML fetch.
- Maintains an inventory with change tracking (new/changed/gone) and recent events.
- UI provides filtering, search, CSV export, and a dashboard widget with recent events.

## State (current)
- SQLite databases under `/var/db/netdiscover/` (inventory + OUI; see [DATABASE_ARCHITECTURE.md](DATABASE_ARCHITECTURE.md))
- Daemon PID: `/var/run/netdiscoverd.pid`

## Build / install
See [INSTALL_OPNSENSE.md](INSTALL_OPNSENSE.md) for the supported OPNsense 26.7+ workflow (`make package` → `pkg add` → template reload).

Package name example: `os-netdiscover-2.1.2.pkg` (version follows `Makefile` `PLUGIN_VERSION`).

## Enable & service control
1. In UI: **Services → NetDiscover** → enable, adjust settings, **Save**, then **Apply**.
2. Service commands:

```sh
service netdiscoverd restart
service netdiscoverd status
```

## Configuration
UI settings render into `/etc/rc.conf.d/netdiscoverd` via OPNsense templates. Optional runtime files:

- Webhook alerts: `/var/db/netdiscover/alerts.json` — [ALERTS_AND_TAGS.md](ALERTS_AND_TAGS.md)
- Auto-tags: `/var/db/netdiscover/auto_tags.json` — same doc

## Related
- [CONTRIBUTING.md](../CONTRIBUTING.md) — local tests and PR expectations
- [CHANGELOG.md](../CHANGELOG.md) — version history
