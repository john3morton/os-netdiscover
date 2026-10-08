<?php
namespace OPNsense\NetDiscover\Api;

use OPNsense\Base\ApiControllerBase;

class OverridesController extends ApiControllerBase
{
    private $overridesFile = "/var/db/netdiscover/overrides.json";

    private function loadOverrides()
    {
        if (!file_exists($this->overridesFile)) {
            return [];
        }
        $raw = file_get_contents($this->overridesFile);
        $data = json_decode($raw, true);
        return is_array($data) ? $data : [];
    }

    private function saveOverrides($overrides)
    {
        $dir = dirname($this->overridesFile);
        if (!is_dir($dir)) {
            mkdir($dir, 0755, true);
        }
        file_put_contents($this->overridesFile, json_encode($overrides, JSON_PRETTY_PRINT));
    }

    public function getAction()
    {
        return ["overrides" => $this->loadOverrides()];
    }

    public function setAction()
    {
        try {
            $payload = $this->request->getJsonRawBody(true);
            if (!is_array($payload)) {
                $payload = $this->request->getPost();
            }
            if (!is_array($payload)) {
                return ["result" => "failed", "error" => "Invalid payload"];
            }

            $ip = isset($payload['ip']) ? trim($payload['ip']) : '';
            if (empty($ip)) {
                return ["result" => "failed", "error" => "IP required"];
            }

            $hostname = isset($payload['hostname']) ? trim($payload['hostname']) : '';
            $deviceType = isset($payload['device_type']) ? trim($payload['device_type']) : '';
            $manufacturer = isset($payload['manufacturer']) ? trim($payload['manufacturer']) : '';
            $model = isset($payload['model']) ? trim($payload['model']) : '';
            $os = isset($payload['os']) ? trim($payload['os']) : '';
            $location = isset($payload['location']) ? trim($payload['location']) : '';
            $tags = isset($payload['tags']) ? array_values(array_filter(array_map('trim', explode(',', $payload['tags'])))) : [];
            $notes = isset($payload['notes']) ? trim($payload['notes']) : '';
            
            // Save to SQLite first (v2.0.2 - with column checking)
            $dbPath = "/var/db/netdiscover/netdiscover.db";
            if (file_exists($dbPath)) {
                try {
                    $db = new \SQLite3($dbPath, SQLITE3_OPEN_READWRITE);
                    $db->busyTimeout(5000);
                    
                    // Check if os column exists in device_overrides, add if missing
                    $result = $db->query("PRAGMA table_info(device_overrides)");
                    $columns = [];
                    while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
                        $columns[] = $row['name'];
                    }
                    
                    if (!in_array('os', $columns)) {
                        $db->exec('ALTER TABLE device_overrides ADD COLUMN os TEXT');
                    }
                    
                    $stmt = $db->prepare('
                        INSERT INTO device_overrides (ip, hostname, device_type, manufacturer, model, os, location, tags, notes, updated_at)
                        VALUES (:ip, :hostname, :device_type, :manufacturer, :model, :os, :location, :tags, :notes, :updated_at)
                        ON CONFLICT(ip) DO UPDATE SET
                            hostname=excluded.hostname,
                            device_type=excluded.device_type,
                            manufacturer=excluded.manufacturer,
                            model=excluded.model,
                            os=excluded.os,
                            location=excluded.location,
                            tags=excluded.tags,
                            notes=excluded.notes,
                            updated_at=excluded.updated_at
                    ');
                    
                    if ($stmt) {
                        $stmt->bindValue(':ip', $ip, SQLITE3_TEXT);
                        $stmt->bindValue(':hostname', $hostname, SQLITE3_TEXT);
                        $stmt->bindValue(':device_type', $deviceType, SQLITE3_TEXT);
                        $stmt->bindValue(':manufacturer', $manufacturer, SQLITE3_TEXT);
                        $stmt->bindValue(':model', $model, SQLITE3_TEXT);
                        $stmt->bindValue(':os', $os, SQLITE3_TEXT);
                        $stmt->bindValue(':location', $location, SQLITE3_TEXT);
                        $stmt->bindValue(':tags', json_encode($tags), SQLITE3_TEXT);
                        $stmt->bindValue(':notes', $notes, SQLITE3_TEXT);
                        $stmt->bindValue(':updated_at', time(), SQLITE3_INTEGER);
                        $stmt->execute();
                    }
                    
                    $db->close();
                } catch (\Exception $e) {
                    error_log("SQLite override save error: " . $e->getMessage());
                    // Don't fail - continue to JSON fallback
                }
            }
            
            // Also save to JSON (backwards compatibility)
            $overrides = $this->loadOverrides();
            $overrides[$ip] = [
                "hostname" => $hostname ?: null,
                "device_type" => $deviceType ?: null,
                "manufacturer" => $manufacturer ?: null,
                "model" => $model ?: null,
                "os" => $os ?: null,
                "location" => $location ?: null,
                "tags" => $tags,
                "notes" => $notes ?: null
            ];

            // Remove null/empty values
            $overrides[$ip] = array_filter($overrides[$ip], function($v) {
                return $v !== null && $v !== '' && (!is_array($v) || count($v) > 0);
            });

            if (empty($overrides[$ip])) {
                unset($overrides[$ip]);
            }

            $this->saveOverrides($overrides);
            return ["result" => "saved"];
        } catch (\Exception $e) {
            error_log("NetDiscover overrides set error: " . $e->getMessage());
            return ["result" => "failed", "error" => $e->getMessage()];
        }
    }

    public function deleteAction()
    {
        try {
            $payload = $this->request->getJsonRawBody(true);
            if (!is_array($payload)) {
                $payload = $this->request->getPost();
            }

            $ip = isset($payload['ip']) ? trim($payload['ip']) : '';
            if (empty($ip)) {
                return ["result" => "failed", "error" => "IP required"];
            }

            $overrides = $this->loadOverrides();
            unset($overrides[$ip]);
            $this->saveOverrides($overrides);
            return ["result" => "deleted"];
        } catch (\Exception $e) {
            error_log("NetDiscover overrides delete error: " . $e->getMessage());
            return ["result" => "failed", "error" => $e->getMessage()];
        }
    }
}


