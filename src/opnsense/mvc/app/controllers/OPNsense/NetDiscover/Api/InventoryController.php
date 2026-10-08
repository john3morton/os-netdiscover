<?php
namespace OPNsense\NetDiscover\Api;

use OPNsense\Base\ApiControllerBase;

class InventoryController extends ApiControllerBase
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
                // Parse JSON fields (v1.7.0: added banners, lifecycle_flags)
                $row['tags'] = json_decode($row['tags'] ?? '[]', true) ?: [];
                $row['mdns_services'] = json_decode($row['mdns_services'] ?? '[]', true) ?: [];
                $row['open_ports'] = json_decode($row['open_ports'] ?? '[]', true) ?: [];
                $row['exhaustive_ports'] = json_decode($row['exhaustive_ports'] ?? '[]', true) ?: [];
                $row['banners'] = json_decode($row['banners'] ?? '{}', true) ?: [];
                $row['hostname_override'] = (bool)($row['hostname_override'] ?? 0);
                // Preserve stable id; hide synthetic ip: keys from MAC column
                $rawMac = $row['mac'] ?? '';
                $row['id'] = $rawMac;
                $row['mac'] = DeviceIdentity::displayMac($rawMac);
                $devices[] = $row;
            }
            
            $db->close();
            
            return ["generated_at" => time(), "devices" => $devices, "events" => []];
        } catch (\Exception $e) {
            error_log("SQLite read error: " . $e->getMessage());
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
            return ["generated_at" => 0, "devices" => [], "events" => []];
        }
        $raw = file_get_contents($path);
        $data = json_decode($raw, true);
        if (!is_array($data) || !isset($data["devices"])) {
            return ["generated_at" => 0, "devices" => [], "events" => []];
        }
        return $data;
    }

    private function loadOverrides()
    {
        $path = "/var/db/netdiscover/overrides.json";
        if (!file_exists($path)) {
            return [];
        }
        $raw = file_get_contents($path);
        $overrides = json_decode($raw, true);
        return is_array($overrides) ? $overrides : [];
    }

    private function mergeOverrides($devices)
    {
        $overrides = $this->loadOverrides();
        if (empty($overrides)) {
            return $devices;
        }

        foreach ($devices as &$device) {
            $mac = strtolower($device['mac'] ?? '');
            $ip = $device['ip'] ?? '';
            // Prefer MAC-keyed overrides; fall back to legacy IP keys
            $override = null;
            if ($mac !== '' && isset($overrides[$mac])) {
                $override = $overrides[$mac];
            } elseif ($ip !== '' && isset($overrides[$ip])) {
                $override = $overrides[$ip];
            }
            if ($override === null) {
                continue;
            }
            if (isset($override['hostname']) && !empty($override['hostname'])) {
                $device['hostname'] = $override['hostname'];
                $device['hostname_override'] = true;
            }
            if (isset($override['device_type']) && !empty($override['device_type'])) {
                $device['device_type'] = $override['device_type'];
            }
            if (isset($override['manufacturer']) && !empty($override['manufacturer'])) {
                $device['manufacturer'] = $override['manufacturer'];
            }
            if (isset($override['model']) && !empty($override['model'])) {
                $device['model'] = $override['model'];
            }
            if (isset($override['os']) && !empty($override['os'])) {
                $device['os'] = $override['os'];
            }
            if (isset($override['location']) && !empty($override['location'])) {
                $device['location'] = $override['location'];
            }
            if (isset($override['tags']) && is_array($override['tags'])) {
                $device['tags'] = $override['tags'];
            }
            if (isset($override['notes']) && !empty($override['notes'])) {
                $device['notes'] = $override['notes'];
            }
        }
        return $devices;
    }

    public function searchAction()
    {
        try {
            $inv = $this->loadInventory();
            $devices = $this->mergeOverrides($inv["devices"]);

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
            $statusFilter = isset($payload["status"]) ? strtolower(trim($payload["status"])) : "";
            $sort = isset($payload["sort"]) && is_array($payload["sort"]) ? $payload["sort"] : [];

        if ($statusFilter !== "") {
            $devices = array_values(array_filter($devices, function($d) use ($statusFilter) {
                return strtolower(($d["status"] ?? "")) === $statusFilter;
            }));
        }

        if ($searchPhrase !== "") {
            $devices = array_values(array_filter($devices, function($d) use ($searchPhrase) {
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
                return strpos($hay, $searchPhrase) !== false;
            }));
        }

        foreach ($sort as $k => $dir) {
            usort($devices, function($a, $b) use ($k, $dir) {
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

        $total = count($devices);
        if ($rowCount > 0) {
            $start = max(0, ($current - 1) * $rowCount);
            $devices = array_slice($devices, $start, $rowCount);
        }

            return [
                "current" => $current,
                "rowCount" => $rowCount,
                "rows" => $devices,
                "total" => $total,
                "generated_at" => $inv["generated_at"] ?? 0
            ];
        } catch (\Exception $e) {
            error_log("NetDiscover inventory search error: " . $e->getMessage());
            return [
                "current" => 1,
                "rowCount" => 50,
                "rows" => [],
                "total" => 0,
                "error" => $e->getMessage()
            ];
        }
    }
    
    /**
     * Delete a device from inventory
     * POST /api/netdiscover/inventory/delete
     * Payload: {"mac": "aa:bb:...", "ip": "192.168.1.1"}  (mac preferred)
     */
    public function deleteAction()
    {
        try {
            $payload = $this->request->getJsonRawBody(true);
            if (!is_array($payload)) {
                $payload = $this->request->getPost();
            }
            
            $mac = isset($payload['mac']) ? strtolower(trim($payload['mac'])) : '';
            $ip = isset($payload['ip']) ? trim($payload['ip']) : '';
            if ($mac === '' && $ip === '') {
                return ["result" => "failed", "error" => "MAC or IP required"];
            }
            if ($mac !== '' && str_starts_with($mac, 'ip:')) {
                // synthetic key from MAC-less hosts
            } elseif ($mac === '' && $ip !== '') {
                $mac = 'ip:' . $ip;
            }
            
            // Delete from SQLite
            $dbPath = "/var/db/netdiscover/netdiscover.db";
            if (file_exists($dbPath)) {
                $db = new \SQLite3($dbPath, SQLITE3_OPEN_READWRITE);
                $db->busyTimeout(5000);
                
                // Delete by MAC identity only (avoid deleting a different device that reused the IP)
                if ($mac !== '') {
                    $stmt = $db->prepare('DELETE FROM devices WHERE mac = :mac');
                    $stmt->bindValue(':mac', $mac, SQLITE3_TEXT);
                    $stmt->execute();

                    $stmt = $db->prepare('DELETE FROM device_history WHERE mac = :mac');
                    $stmt->bindValue(':mac', $mac, SQLITE3_TEXT);
                    $stmt->execute();

                    $stmt = $db->prepare('DELETE FROM device_overrides WHERE mac = :mac');
                    $stmt->bindValue(':mac', $mac, SQLITE3_TEXT);
                    $stmt->execute();

                    $stmt = $db->prepare('DELETE FROM events WHERE mac = :mac');
                    $stmt->bindValue(':mac', $mac, SQLITE3_TEXT);
                    $stmt->execute();
                } elseif ($ip !== '') {
                    $stmt = $db->prepare('DELETE FROM devices WHERE ip = :ip');
                    $stmt->bindValue(':ip', $ip, SQLITE3_TEXT);
                    $stmt->execute();
                }
                
                $db->close();
            }
            
            // Also delete from JSON (backwards compatibility)
            $jsonPath = "/var/db/netdiscover/devices.json";
            if (file_exists($jsonPath)) {
                $data = json_decode(file_get_contents($jsonPath), true);
                if (is_array($data) && isset($data['devices'])) {
                    $data['devices'] = array_values(array_filter($data['devices'], function($d) use ($mac, $ip) {
                        $dmac = strtolower($d['mac'] ?? '');
                        $dip = $d['ip'] ?? '';
                        if ($mac !== '' && ($dmac === $mac || $dmac === '')) {
                            if ($dmac === $mac) {
                                return false;
                            }
                        }
                        return $dip !== $ip;
                    }));
                    file_put_contents($jsonPath, json_encode($data, JSON_PRETTY_PRINT));
                }
            }
            
            return ["result" => "deleted", "mac" => $mac, "ip" => $ip];
        } catch (\Exception $e) {
            error_log("Device delete error: " . $e->getMessage());
            return ["result" => "failed", "error" => $e->getMessage()];
        }
    }
}
