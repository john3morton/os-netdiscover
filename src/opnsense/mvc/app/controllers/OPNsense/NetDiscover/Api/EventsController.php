<?php
namespace OPNsense\NetDiscover\Api;

use OPNsense\Base\ApiControllerBase;

class EventsController extends ApiControllerBase
{
    private function loadEventsFromSQLite()
    {
        $dbPath = "/var/db/netdiscover/netdiscover.db";
        if (!file_exists($dbPath)) {
            return null;
        }
        
        try {
            $db = new \SQLite3($dbPath, SQLITE3_OPEN_READONLY);
            $db->busyTimeout(5000);
            
            $result = $db->query('SELECT * FROM events ORDER BY timestamp DESC LIMIT 1000');
            $events = [];
            
            while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
                $row['time'] = $row['timestamp']; // Compatibility mapping
                $row['type'] = $row['event_type']; // Map event_type to type for JS compatibility
                $row['details'] = json_decode($row['details'] ?? '{}', true) ?: [];
                $events[] = $row;
            }
            
            $db->close();
            return $events;
        } catch (\Exception $e) {
            error_log("SQLite events read error: " . $e->getMessage());
            return null;
        }
    }
    
    private function loadEvents()
    {
        // Try SQLite first
        $events = $this->loadEventsFromSQLite();
        if ($events !== null) {
            return $events;
        }
        
        // Fallback to JSON
        $path = "/var/db/netdiscover/devices.json";
        if (!file_exists($path)) {
            return [];
        }
        $raw = file_get_contents($path);
        $data = json_decode($raw, true);
        if (!is_array($data) || !isset($data["events"]) || !is_array($data["events"])) {
            return [];
        }
        return $data["events"];
    }

    public function searchAction()
    {
        try {
            $events = $this->loadEvents();

            // Handle both JSON and form-encoded requests
            $payload = $this->request->getJsonRawBody(true);
            if (!is_array($payload)) {
                $payload = $this->request->getPost();
            }
            if (!is_array($payload)) {
                $payload = [];
            }
            
            $current = isset($payload["current"]) ? (int)$payload["current"] : 1;
            $rowCount = isset($payload["rowCount"]) ? (int)$payload["rowCount"] : 50;
            $searchPhrase = isset($payload["searchPhrase"]) ? strtolower(trim($payload["searchPhrase"])) : "";
            $sort = isset($payload["sort"]) && is_array($payload["sort"]) ? $payload["sort"] : [];

        if ($searchPhrase !== "") {
            $events = array_values(array_filter($events, function($e) use ($searchPhrase) {
                $hay = strtolower(
                    ($e["type"] ?? "") . " " .
                    ($e["ip"] ?? "") . " " .
                    ($e["mac"] ?? "") . " " .
                    ($e["hostname"] ?? "") . " " .
                    json_encode($e["details"] ?? [])
                );
                return strpos($hay, $searchPhrase) !== false;
            }));
        }

        foreach ($sort as $k => $dir) {
            usort($events, function($a, $b) use ($k, $dir) {
                $av = $a[$k] ?? "";
                $bv = $b[$k] ?? "";
                if (is_numeric($av) && is_numeric($bv)) {
                    $cmp = (int)$av <=> (int)$bv;
                } else {
                    $cmp = strcmp((string)$av, (string)$bv);
                }
                return ($dir === "desc") ? -$cmp : $cmp;
            });
            break;
        }

        $total = count($events);
        if ($rowCount > 0) {
            $start = max(0, ($current - 1) * $rowCount);
            $events = array_slice($events, $start, $rowCount);
        }

            return [
                "current" => $current,
                "rowCount" => $rowCount,
                "rows" => $events,
                "total" => $total
            ];
        } catch (\Exception $e) {
            error_log("NetDiscover events search error: " . $e->getMessage());
            return [
                "current" => 1,
                "rowCount" => 50,
                "rows" => [],
                "total" => 0,
                "error" => $e->getMessage()
            ];
        }
    }
}
