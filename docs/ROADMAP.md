# NetDiscover Plugin Roadmap

Current Version: **v2.0.6** (Dec 2025)

## ✅ Completed Features (v0.9 - v2.0)

### ✅ Dashboard Widget (Completed v0.9.7)
- [x] Add a summary widget showing device counts (new/changed/gone/total)
- [x] Color-coded status badges for quick visual scanning
- [x] Recent events table (last 10 events)
- [x] Quick link to full inventory page
- [x] Auto-refresh every 15 seconds

### ✅ Search, Sort & Filter (Completed v1.0.0)
- [x] Search boxes on Inventory and Recent Changes tabs
- [x] Column sorting (click headers) for all major columns
- [x] Sort indicators (▲/▼) showing active column and direction
- [x] Hover effects on sortable columns
- [x] Combined status + search filtering
- [x] Client-side filtering/sorting (instant, no page reload)
- [x] Filter count display ("X of Y devices")
- [x] Auto-refresh every 30 seconds when tab is active
- [x] Manual refresh buttons with loading animation
- [x] Last updated timestamps

### ✅ Search/Filter Persistence (Completed v1.1.0)
- [x] Remember filter selections across page refreshes
- [x] Store filter state in browser localStorage
- [x] Persists: status filter, search term, sort column, sort direction

### ✅ Bulk Actions (Completed v1.1.0)
- [x] Select multiple devices for batch tagging or export
- [x] Checkbox selection in inventory table
- [x] Bulk tag operations
- [x] Bulk clear overrides
- [x] Select All checkbox with indeterminate state
- [x] Selection count indicator

### ✅ Device Detail Modal (Completed v1.1.0)
- [x] Click on a device row to see full details without editing
- [x] Read-only view with all discovered attributes
- [x] Quick edit button to switch to edit mode
- [x] Eye icon button for quick detail view

### ✅ v2.0+ Features
- [x] WiFi AP topology detection via syslog parsing (v2.0.2)
- [x] Exhaustive port scan results in inventory table (v2.0.4)
- [x] Recent Changes filter (latest per device) (v2.0.6)
- [x] Clickable event rows to open device details (v2.0.6)

---

## 🎯 High Priority (Next Up)

### Alert/Notification System
- [ ] Configurable alerts for new/gone devices
- [ ] Email/webhook notifications
- [ ] Alert rules based on device properties

### Device Grouping
- [ ] Organize devices by type, subnet, or custom groups
- [ ] Collapsible group view in inventory
- [ ] Group-based filtering

### ✅ Historical Tracking (Completed v1.1.0)
- [x] Show device history timeline (when first/last seen, status changes)
- [x] Status change log per device
- [x] Attribute change tracking (hostname, vendor, etc.)
- [x] Historical data retention (auto-cleanup after 90 days)
- [x] Uptime statistics and percentage calculation
- [x] Multi-tab device detail modal (Current/History/Uptime)
- [x] Interactive timeline with clickable segments (v1.6.6)

---

## 🔧 Medium Priority (Future Features)

### API Documentation
- [ ] Auto-generated API docs for integration
- [ ] OpenAPI/Swagger specification
- [ ] Example integration scripts

### Port Scanning Enhancements
- [ ] Configurable port ranges via UI (API supports it, UI needed)
- [ ] Service name detection per port
- [ ] Enhanced banner grabbing on all ports
- [ ] Port scan history timeline per device

### Import/Export Overrides
- [ ] Bulk import/export device custom settings
- [ ] CSV/JSON format support
- [ ] Template-based import

### Advanced Filtering
- [ ] Filter by multiple criteria (vendor + subnet, etc.)
- [ ] Complex filter expressions
- [ ] Saved filter presets

### Auto-tagging Rules
- [ ] Automatically tag devices based on patterns
- [ ] Rule engine for device classification
- [ ] Regular expression matching

### Network Diagram
- [ ] Visual map of discovered devices
- [ ] Subnet-based topology view
- [ ] Interactive device selection

---

## 💡 Low Priority (Nice-to-Have)

### Pagination
- [ ] Handle large inventories better (currently loads all 999)
- [ ] Server-side pagination in API
- [ ] Configurable page size

### ✅ Database Backend (Completed v1.1.0)
- [x] SQLite instead of JSON for large deployments
- [x] Migration path from JSON to SQLite (migrate_to_sqlite.py)
- [x] Hybrid mode (writes both formats during transition)
- [x] Automatic database initialization
- [x] Indexed queries for performance
- [x] Database schema with foreign keys and constraints

### Performance Metrics
- [ ] Add scan duration/stats to dashboard
- [ ] Discovery method effectiveness metrics
- [ ] System resource usage tracking

### Enhanced Wireshark Integration
- [ ] Extract device categories from OUI database
- [ ] Parse vendor short names for better display
- [ ] Model disambiguation when multiple models match

---

## 📊 Feature Summary by Version

### Core Platform (v0.9 - v1.1)
- ✅ Dashboard widget with color-coded status badges (v0.9.7)
- ✅ CSV export for inventory
- ✅ Status filters (new/changed/gone/all)
- ✅ Device edit/override functionality
- ✅ Settings tab with full configuration
- ✅ Search boxes on Inventory and Recent Changes tabs (v1.0.0)
- ✅ Column sorting with visual indicators (v1.0.0)
- ✅ Auto-refresh every 30 seconds (v1.0.0)
- ✅ Manual refresh buttons with loading animation (v1.0.0)
- ✅ Color-coded status indicators on table rows (v1.0.0)
- ✅ Search/filter persistence with localStorage (v1.1.0)
- ✅ Bulk selection and operations (v1.1.0)
- ✅ Device detail modal with quick edit (v1.1.0)
- ✅ SQLite database backend with historical tracking (v1.1.0)
- ✅ Device history timeline and uptime statistics (v1.1.0)
- ✅ Migration script from JSON to SQLite (v1.1.0)

### Advanced Features (v1.2 - v1.6)
- ✅ Dual-state architecture (lifecycle flags + connection state) (v1.5.0)
- ✅ DHCP type detection (static/reserved/dynamic) (v1.5.1)
- ✅ Column resizing and visibility controls (v1.5.x)
- ✅ Interactive timeline with clickable segments (v1.6.6)
- ✅ Exhaustive port scanning (1-65535 ports) (v1.6.0)
- ✅ Override vs discovered field tracking (v1.6.0)
- ✅ Operating system detection (v1.6.0-v1.6.2)
- ✅ Wireshark model hints extraction (v1.6.2)

### Topology & Recent Enhancements (v2.0+)
- ✅ WiFi AP topology detection via syslog parsing (v2.0.2)
- ✅ Multi-vendor AP support (UniFi, Omada, OpenWrt, etc.) (v2.0.2)
- ✅ Exhaustive port results in inventory table (v2.0.4)
- ✅ Recent Changes filter (latest per device) (v2.0.6)
- ✅ Clickable event rows to view device details (v2.0.6)

---

## 🚀 Next Release Planning (v2.1+)

**Candidates for v2.1:**
1. Alert/notification system (email/webhook for new/gone devices)
2. Port range configuration in UI
3. API documentation (OpenAPI/Swagger)

**Candidates for v2.2:**
1. Device grouping and organization
2. Advanced multi-criteria filtering
3. Import/export device overrides

**Long-term (v2.3+):**
1. Network topology diagram
2. Auto-tagging rules engine
3. Performance metrics dashboard

