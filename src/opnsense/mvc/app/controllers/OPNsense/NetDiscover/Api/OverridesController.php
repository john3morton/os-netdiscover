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

            $mac = DeviceIdentity::keyFromPayload($payload);
            $ip = isset($payload['ip']) ? trim($payload['ip']) : '';
            if ($mac === '') {
                return ["result" => "failed", "error" => "MAC or IP required"];
            }

            $hostname = isset($payload['hostname']) ? trim($payload['hostname']) : '';
            $deviceType = isset($payload['device_type']) ? trim($payload['device_type']) : '';
            $manufacturer = isset($payload['manufacturer']) ? trim($payload['manufacturer']) : '';
            $model = isset($payload['model']) ? trim($payload['model']) : '';
            $os = isset($payload['os']) ? trim($payload['os']) : '';
            $location = isset($payload['location']) ? trim($payload['location']) : '';
            $tags = isset($payload['tags']) ? array_values(array_filter(array_map('trim', explode(',', $payload['tags'])))) : [];
            $notes = isset($payload['notes']) ? trim($payload['notes']) : '';

            $dbPath = "/var/db/netdiscover/netdiscover.db";
            if (file_exists($dbPath)) {
                try {
                    $db = new \SQLite3($dbPath, SQLITE3_OPEN_READWRITE);
                    $db->busyTimeout(5000);

                    $result = $db->query("PRAGMA table_info(device_overrides)");
                    $columns = [];
                    while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
                        $columns[] = $row['name'];
                    }
                    if (!in_array('os', $columns)) {
                        $db->exec('ALTER TABLE device_overrides ADD COLUMN os TEXT');
                    }
                    if (!in_array('mac', $columns)) {
                        // Pre-migration DB — fall through to JSON only
                        $db->close();
                        throw new \Exception("device_overrides missing mac column");
                    }

                    $stmt = $db->prepare('
                        INSERT INTO device_overrides (mac, ip, hostname, device_type, manufacturer, model, os, location, tags, notes, updated_at)
                        VALUES (:mac, :ip, :hostname, :device_type, :manufacturer, :model, :os, :location, :tags, :notes, :updated_at)
                        ON CONFLICT(mac) DO UPDATE SET
                            ip=excluded.ip,
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
                        $stmt->bindValue(':mac', $mac, SQLITE3_TEXT);
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
                }
            }

            $overrides = $this->loadOverrides();
            // Drop legacy IP key if present
            if ($ip !== '' && isset($overrides[$ip]) && $ip !== $mac) {
                unset($overrides[$ip]);
            }
            $overrides[$mac] = [
                "hostname" => $hostname ?: null,
                "device_type" => $deviceType ?: null,
                "manufacturer" => $manufacturer ?: null,
                "model" => $model ?: null,
                "os" => $os ?: null,
                "location" => $location ?: null,
                "tags" => $tags,
                "notes" => $notes ?: null,
                "ip" => $ip ?: null
            ];

            $overrides[$mac] = array_filter($overrides[$mac], function ($v) {
                return $v !== null && $v !== '' && (!is_array($v) || count($v) > 0);
            });

            if (empty($overrides[$mac])) {
                unset($overrides[$mac]);
            }

            $this->saveOverrides($overrides);
            return ["result" => "saved", "mac" => $mac];
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

            $mac = DeviceIdentity::keyFromPayload($payload);
            $ip = isset($payload['ip']) ? trim($payload['ip']) : '';
            if ($mac === '' && $ip === '') {
                return ["result" => "failed", "error" => "MAC or IP required"];
            }

            $dbPath = "/var/db/netdiscover/netdiscover.db";
            if (file_exists($dbPath)) {
                try {
                    $db = new \SQLite3($dbPath, SQLITE3_OPEN_READWRITE);
                    $db->busyTimeout(5000);
                    if ($mac !== '') {
                        $stmt = $db->prepare('DELETE FROM device_overrides WHERE mac = :mac');
                        $stmt->bindValue(':mac', $mac, SQLITE3_TEXT);
                        $stmt->execute();
                    }
                    if ($ip !== '') {
                        $stmt = $db->prepare('DELETE FROM device_overrides WHERE ip = :ip');
                        $stmt->bindValue(':ip', $ip, SQLITE3_TEXT);
                        $stmt->execute();
                    }
                    $db->close();
                } catch (\Exception $e) {
                    error_log("SQLite override delete error: " . $e->getMessage());
                }
            }

            $overrides = $this->loadOverrides();
            if ($mac !== '') {
                unset($overrides[$mac]);
            }
            if ($ip !== '') {
                unset($overrides[$ip]);
            }
            $this->saveOverrides($overrides);
            return ["result" => "deleted", "mac" => $mac];
        } catch (\Exception $e) {
            error_log("NetDiscover overrides delete error: " . $e->getMessage());
            return ["result" => "failed", "error" => $e->getMessage()];
        }
    }
}
