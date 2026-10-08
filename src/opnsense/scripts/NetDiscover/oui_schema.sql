-- OUI (MAC Vendor) Database Schema
-- Separate database for OUI lookups (only used by Python daemon)
-- Version 1.2.4+

-- OUI (MAC vendor) mappings
CREATE TABLE IF NOT EXISTS oui (
    oui TEXT PRIMARY KEY,
    vendor TEXT NOT NULL,
    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_oui_vendor ON oui(vendor);

-- Metadata about OUI database
CREATE TABLE IF NOT EXISTS oui_metadata (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
);

-- Store download timestamp, entry count, source URL
INSERT OR REPLACE INTO oui_metadata (key, value) VALUES 
    ('schema_version', '1.2.4'),
    ('description', 'IEEE OUI (MAC Vendor) Database');

