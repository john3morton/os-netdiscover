# NetDiscover for OPNsense

**Version:** 2.0.14  
**Professional network device discovery and inventory management**

## Overview

NetDiscover is a comprehensive network device discovery and inventory system for OPNsense featuring:

- **Multi-protocol discovery** - dnsmasq, SSDP, mDNS, LLMNR, NetBIOS, TCP probes, SNMP
- **Dual-state status** - Separate connection state and lifecycle flags
- **Timeline visualization** - Visual device history with clickable segments
- **SQLite backend** - Fast, indexed queries with historical tracking
- **38,000+ vendor database** - IEEE OUI or Wireshark Extended
- **Advanced fingerprinting** - 5 methods for device type identification
- **On-demand port scanning** - Exhaustive 1-1000 port scans
- **DHCP type detection** - Static, reserved, or dynamic IP classification
- **Real-time updates** - Auto-refresh, live search, instant filtering

## Quick Start

See **[docs/INSTALL_OPNSENSE.md](docs/INSTALL_OPNSENSE.md)** for installation on OPNsense 26.7+.

Package name after build: `os-netdiscover-2.0.14.pkg`

## Documentation

Complete documentation available in **[docs/](docs/)** folder:

- **[docs/INDEX.md](docs/INDEX.md)** - Documentation index
- **[CHANGELOG.md](CHANGELOG.md)** - Version history (root)
- **[docs/ROADMAP.md](docs/ROADMAP.md)** - Future enhancements

### Key Documents
- [Installation Guide](docs/INSTALL_OPNSENSE.md)
- [Database Architecture](docs/DATABASE_ARCHITECTURE.md)
- [Status System](docs/DUAL_STATE_DESIGN.md)
- [Device Fingerprinting](docs/DEVICE_FINGERPRINTING.md)
- [OUI Database](docs/OUI_DATABASE.md)

## Features

### Discovery Methods
- **8 protocols:** dnsmasq DHCP, SSDP/UPnP, mDNS, LLMNR, NetBIOS, TCP probes, SNMP, Pattern matching
- **Multiple networks:** Scan across VLANs/subnets simultaneously
- **Adaptive intervals:** Configurable scan frequency (default: 120s)

### Device Identification
- **38,632 manufacturers:** Wireshark Extended or IEEE OUI database
- **Pattern matching:** 100+ hostname patterns, 50+ port signatures, 20+ mDNS patterns
- **Banner analysis:** SSH, HTTP, FTP, Telnet banners
- **DHCP classification:** Static, reserved, or dynamic IP detection
- **OS detection:** From banners, SNMP, hostname patterns

### Status System
- **Dual-state architecture:**
  - Connection: online, offline (2 cycles), missing (30d), gone (60d)
  - Lifecycle: new (48h), changed, back (24h or reviewed)
- **Visual indicators:** Colored balls for flags + connection state
- **Interactive timeline:** Click segments for details

### User Interface
- **Dashboard widget** with color-coded stats
- **Resizable columns** with show/hide
- **Dual filters:** Lifecycle + Connection state
- **Live search** across all fields
- **Numeric IP sorting**
- **Device detail modal** with 3 tabs (Current/History/Uptime)
- **Timeline graph** with clickable segments
- **Bulk operations** (multi-select, tag, delete)
- **On-demand port scanning**

### Data Management
- **SQLite backend** (2 databases for performance)
- **Historical tracking** (90-day retention)
- **Uptime statistics**
- **CSV export**
- **No auto-prune** (manual control)
- **Override vs discovered** values

## Performance

- **4x faster** page loads (split databases)
- **100x faster** OUI lookups (indexed)
- **Sub-millisecond** device queries
- **~15ms** inventory page load (100 devices)

## Requirements

- OPNsense 26.7+
- Python 3.13+ (system `python3` link)
- SQLite3
- Disk space: ~10-50MB (depending on device count)

## License

MIT License — see [LICENSE](LICENSE).

## Support

For issues, feature requests, or questions, open a GitHub issue or see the documentation in the `docs/` folder.
