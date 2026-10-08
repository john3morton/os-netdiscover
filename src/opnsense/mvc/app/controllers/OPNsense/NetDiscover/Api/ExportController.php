<?php
namespace OPNsense\NetDiscover\Api;

use OPNsense\Base\ApiControllerBase;

class ExportController extends ApiControllerBase
{
    private function loadInventoryFromSQLite()
    {
        $dbPath = "/var/db/netdiscover/netdiscover.db";
        if (!file_exists($dbPath)) {
            return null;
        }
        
        try {
            $db = new \SQLite3($dbPath, SQLITE3_OPEN_READONLY);
            $db->busyTimeout(5000);
            
            $result = $db->query('SELECT * FROM devices ORDER BY last_seen DESC');
            $devices = [];
            
            while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
                $row['tags'] = json_decode($row['tags'] ?? '[]', true) ?: [];
                $row['mdns_services'] = json_decode($row['mdns_services'] ?? '[]', true) ?: [];
                $row['open_ports'] = json_decode($row['open_ports'] ?? '[]', true) ?: [];
                $devices[] = $row;
            }
            
            $db->close();
            return ["devices" => $devices];
        } catch (\Exception $e) {
            error_log("SQLite export error: " . $e->getMessage());
            return null;
        }
    }
    
    private function loadInventory()
    {
        // Try SQLite first
        $data = $this->loadInventoryFromSQLite();
        if ($data !== null) {
            return $data;
        }
        
        // Fallback to JSON
        $path = "/var/db/netdiscover/devices.json";
        if (!file_exists($path)) {
            return ["devices" => []];
        }
        $raw = file_get_contents($path);
        $data = json_decode($raw, true);
        if (!is_array($data) || !isset($data["devices"])) {
            return ["devices" => []];
        }
        return $data;
    }

    private function csvEscape($v)
    {
        $v = (string)$v;
        $v = str_replace("\"", "\"\"", $v);
        return "\"" . $v . "\"";
    }

    public function inventoryAction()
    {
        $inv = $this->loadInventory();
        $devices = $inv["devices"];

        // Query params: status, search
        $status = strtolower(trim($this->request->getQuery("status", "string", "")));
        $search = strtolower(trim($this->request->getQuery("search", "string", "")));

        if ($status !== "") {
            $devices = array_values(array_filter($devices, function($d) use ($status) {
                return strtolower(($d["status"] ?? "")) === $status;
            }));
        }

        if ($search !== "") {
            $devices = array_values(array_filter($devices, function($d) use ($search) {
                $ports = "";
                if (isset($d["open_ports"]) && is_array($d["open_ports"])) {
                    $ports = implode(",", $d["open_ports"]);
                }
                $svc = "";
                if (isset($d["mdns_services"]) && is_array($d["mdns_services"])) {
                    $svc = implode(",", $d["mdns_services"]);
                }
                $hay = strtolower(
                    ($d["ip"] ?? "") . " " .
                    ($d["mac"] ?? "") . " " .
                    ($d["hostname"] ?? "") . " " .
                    ($d["vendor"] ?? "") . " " .
                    ($d["device_type"] ?? "") . " " .
                    ($d["manufacturer"] ?? "") . " " .
                    ($d["model"] ?? "") . " " .
                    ($d["snmp_sysname"] ?? "") . " " .
                    ($d["snmp_sysdescr"] ?? "") . " " .
                    $ports . " " .
                    $svc . " " .
                    ($d["subnet"] ?? "") . " " .
                    ($d["interface"] ?? "") . " " .
                    ($d["status"] ?? "")
                );
                return strpos($hay, $search) !== false;
            }));
        }

        $headers = [
            "ip","mac","hostname","vendor","status","device_type","manufacturer","model",
            "mdns_services","open_ports","snmp_sysname","snmp_sysdescr","interface","subnet",
            "first_seen","last_seen"
        ];

        $lines = [];
        $lines[] = implode(",", $headers);
        foreach ($devices as $d) {
            $row = [];
            foreach ($headers as $h) {
                $v = $d[$h] ?? "";
                if (is_array($v)) {
                    $v = implode(",", $v);
                }
                $row[] = $this->csvEscape($v);
            }
            $lines[] = implode(",", $row);
        }

        $csv = implode("\n", $lines) . "\n";

        $this->response->setHeader("Content-Type", "text/csv");
        $this->response->setHeader("Content-Disposition", "attachment; filename=netdiscover-inventory.csv");
        $this->response->setContent($csv);
        $this->response->send();
        return null;
    }
}
