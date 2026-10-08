-- NetDiscover SQLite Schema with Historical Tracking
-- Version 1.1.0

-- Current device inventory (latest state for each device)
CREATE TABLE IF NOT EXISTS devices (
    ip TEXT PRIMARY KEY,
    mac TEXT,
    hostname TEXT,
    hostname_override INTEGER DEFAULT 0,
    vendor TEXT,
    -- Dual-state system (v1.5.0)
    connection_state TEXT DEFAULT 'online', -- online|offline|missing|gone
    lifecycle_flags TEXT, -- Comma-separated: new,changed,back (or empty)
    status TEXT, -- Computed display string for compatibility
    dhcp_type TEXT, -- static|reserved|dynamic|unknown (v1.5.1)
    device_type TEXT,
    device_type_source TEXT, -- 'pattern_match', 'ssdp', 'snmp', 'mdns', etc.
    tags TEXT, -- JSON array
    -- v1.6.0: Separate discovered vs override values
    discovered_manufacturer TEXT, -- From OUI/SSDP/SNMP
    discovered_model TEXT, -- From OUI hints/SSDP/SNMP
    discovered_os TEXT, -- From banners/SNMP
    manufacturer TEXT, -- User override or discovered
    model TEXT, -- User override or discovered
    os TEXT, -- User override or discovered
    os_version TEXT, -- Operating system version
    exhaustive_ports TEXT, -- JSON array from on-demand port scan
    exhaustive_ports_time INTEGER, -- When exhaustive scan was run
    mdns_services TEXT, -- JSON array
    open_ports TEXT, -- JSON array
    banners TEXT, -- JSON object {port: banner_text}
    snmp_sysname TEXT,
    snmp_sysdescr TEXT,
    interface TEXT,
    subnet TEXT,
    first_seen INTEGER,
    last_seen INTEGER,
    flag_set_time INTEGER, -- When lifecycle flags were last set
    flag_acknowledged INTEGER DEFAULT 0, -- 0=not viewed, 1=user viewed (clears flags)
    -- Network topology (v2.0.0)
    connected_to_ap TEXT, -- AP IP address this device connects through
    ap_name TEXT, -- Friendly name of AP (hostname)
    ap_last_seen INTEGER, -- When AP association was last confirmed
    notes TEXT,
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_devices_connected_to_ap ON devices(connected_to_ap);

CREATE INDEX IF NOT EXISTS idx_devices_dhcp_type ON devices(dhcp_type);

CREATE INDEX IF NOT EXISTS idx_devices_connection_state ON devices(connection_state);
CREATE INDEX IF NOT EXISTS idx_devices_lifecycle_flags ON devices(lifecycle_flags);

CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);
CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON devices(last_seen);
CREATE INDEX IF NOT EXISTS idx_devices_mac ON devices(mac);

-- Device history - tracks all changes to devices over time
CREATE TABLE IF NOT EXISTS device_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    event_type TEXT NOT NULL, -- 'discovered', 'status_change', 'attribute_change', 'removed'
    field_name TEXT, -- Which field changed (hostname, status, etc.)
    old_value TEXT,
    new_value TEXT,
    details TEXT, -- JSON with additional context
    created_at INTEGER DEFAULT (strftime('%s', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_history_ip ON device_history(ip, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_history_timestamp ON device_history(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_history_event_type ON device_history(event_type);

-- Events (ring buffer replacement) - recent network events
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,
    event_type TEXT NOT NULL, -- 'new', 'back', 'changed', 'gone'
    ip TEXT NOT NULL,
    mac TEXT,
    hostname TEXT,
    details TEXT, -- JSON
    created_at INTEGER DEFAULT (strftime('%s', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_ip ON events(ip);

-- User overrides (custom settings per device) - v1.6.0: added os
CREATE TABLE IF NOT EXISTS device_overrides (
    ip TEXT PRIMARY KEY,
    hostname TEXT,
    device_type TEXT,
    manufacturer TEXT,
    model TEXT,
    os TEXT, -- Operating system override
    location TEXT,
    tags TEXT, -- JSON array
    notes TEXT,
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
);

-- Scan statistics (performance metrics)
CREATE TABLE IF NOT EXISTS scan_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,
    duration_seconds REAL,
    devices_discovered INTEGER,
    devices_changed INTEGER,
    devices_gone INTEGER,
    interfaces_scanned TEXT,
    created_at INTEGER DEFAULT (strftime('%s', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_scan_stats_timestamp ON scan_stats(timestamp DESC);

-- View for joining devices with overrides
CREATE VIEW IF NOT EXISTS devices_with_overrides AS
SELECT 
    d.*,
    o.hostname AS override_hostname,
    o.device_type AS override_device_type,
    o.tags AS override_tags,
    o.notes AS override_notes,
    CASE WHEN o.ip IS NOT NULL THEN 1 ELSE 0 END AS has_override
FROM devices d
LEFT JOIN device_overrides o ON d.ip = o.ip;

-- Auto-cleanup trigger for old events (keep last 1000)
CREATE TRIGGER IF NOT EXISTS cleanup_old_events
AFTER INSERT ON events
BEGIN
    DELETE FROM events WHERE id IN (
        SELECT id FROM events ORDER BY timestamp DESC LIMIT -1 OFFSET 1000
    );
END;

-- Auto-cleanup trigger for old history (keep last 90 days)
CREATE TRIGGER IF NOT EXISTS cleanup_old_history
AFTER INSERT ON device_history
BEGIN
    DELETE FROM device_history 
    WHERE timestamp < strftime('%s', 'now', '-90 days');
END;

