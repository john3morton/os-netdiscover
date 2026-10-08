<?php
namespace OPNsense\NetDiscover\Api;

use OPNsense\Base\ApiControllerBase;

class DashboardController extends ApiControllerBase
{
    private function loadFromSQLite()
    {
        $dbPath = "/var/db/netdiscover/netdiscover.db";
        if (!file_exists($dbPath)) {
            return null;
        }
        
        try {
            $db = new \SQLite3($dbPath, SQLITE3_OPEN_READONLY);
            $db->busyTimeout(5000);
            
            // Get device stats
            $result = $db->query('SELECT COUNT(*) as cnt FROM devices');
            $total = $result->fetchArray(SQLITE3_ASSOC)['cnt'];
            
            $now = time();
            $result = $db->query('SELECT COUNT(*) as cnt FROM devices WHERE last_seen > ' . ($now - 600));
            $up = $result->fetchArray(SQLITE3_ASSOC)['cnt'];
            
            $result = $db->query('SELECT COUNT(*) as cnt FROM devices WHERE status = "new" AND last_seen > ' . ($now - 86400));
            $new = $result->fetchArray(SQLITE3_ASSOC)['cnt'];
            
            $result = $db->query('SELECT COUNT(*) as cnt FROM devices WHERE status = "changed" AND last_seen > ' . ($now - 86400));
            $changed = $result->fetchArray(SQLITE3_ASSOC)['cnt'];
            
            $result = $db->query('SELECT COUNT(*) as cnt FROM devices WHERE status = "gone" AND last_seen > ' . ($now - 86400));
            $gone = $result->fetchArray(SQLITE3_ASSOC)['cnt'];
            
            // Get recent events
            $result = $db->query('SELECT * FROM events ORDER BY timestamp DESC LIMIT 10');
            $events = [];
            while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
                $row['time'] = $row['timestamp'];
                $row['type'] = $row['event_type']; // Map event_type to type for JS compatibility
                $row['details'] = json_decode($row['details'] ?? '{}', true) ?: [];
                $events[] = $row;
            }
            
            $db->close();
            
            return [
                'total' => $total,
                'up_10m' => $up,
                'new_24h' => $new,
                'changed_24h' => $changed,
                'gone_24h' => $gone,
                'recent_events' => $events
            ];
        } catch (\Exception $e) {
            error_log("SQLite dashboard read error: " . $e->getMessage());
            return null;
        }
    }
    
    private function loadInventory()
    {
        // Try SQLite first
        $data = $this->loadFromSQLite();
        if ($data !== null) {
            return ["generated_at" => time(), "devices" => [], "events" => [], "stats" => $data];
        }
        
        // Fallback to JSON
        $path = "/var/db/netdiscover/devices.json";
        if (!file_exists($path)) {
            return ["generated_at" => 0, "devices" => [], "events" => []];
        }
        $raw = file_get_contents($path);
        $data = json_decode($raw, true);
        if (!is_array($data) || !isset($data["devices"])) {
            return ["generated_at" => 0, "devices" => [], "events" => []];
        }
        if (!isset($data["events"]) || !is_array($data["events"])) {
            $data["events"] = [];
        }
        return $data;
    }

    public function summaryAction()
    {
        // Try SQLite (fast, pre-computed)
        $sqliteData = $this->loadFromSQLite();
        if ($sqliteData !== null) {
            return $sqliteData;
        }
        
        // Fallback to JSON
        $inv = $this->loadInventory();
        $devices = $inv["devices"];
        $events = $inv["events"];
        $now = time();

        $total = count($devices);
        $up = 0;
        $new24 = 0;
        $chg24 = 0;
        $gone24 = 0;

        foreach ($devices as $d) {
            $ls = isset($d["last_seen"]) ? (int)$d["last_seen"] : 0;
            if ($ls > $now - 600) { $up++; }
            $status = $d["status"] ?? "";
            if ($status === "new" && $ls > $now - 86400) { $new24++; }
            if ($status === "changed" && $ls > $now - 86400) { $chg24++; }
            if ($status === "gone" && $ls > $now - 86400) { $gone24++; }
        }

        $recent = array_slice($events, 0, 10);

        return [
            "generated_at" => $inv["generated_at"] ?? 0,
            "total" => $total,
            "up_10m" => $up,
            "new_24h" => $new24,
            "changed_24h" => $chg24,
            "gone_24h" => $gone24,
            "recent_events" => $recent
        ];
    }
}
