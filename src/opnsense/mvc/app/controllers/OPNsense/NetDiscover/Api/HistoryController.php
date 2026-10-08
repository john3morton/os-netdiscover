<?php
namespace OPNsense\NetDiscover\Api;

use OPNsense\Base\ApiControllerBase;

class HistoryController extends ApiControllerBase
{
    private function resolveKey()
    {
        $mac = DeviceIdentity::normalizeMac($this->request->getQuery("mac", "string", ""));
        $ip = trim($this->request->getQuery("ip", "string", ""));
        if ($mac === '' && $ip !== '') {
            $mac = 'ip:' . $ip;
        }
        return [$mac, $ip];
    }

    /**
     * GET /api/netdiscover/history/device?mac=...&ip=...
     */
    public function deviceAction()
    {
        list($mac, $ip) = $this->resolveKey();
        if ($mac === '' && $ip === '') {
            return ["error" => "MAC or IP required", "rows" => []];
        }

        $dbPath = "/var/db/netdiscover/netdiscover.db";
        if (!file_exists($dbPath)) {
            return ["error" => "Database not found", "rows" => []];
        }

        try {
            $db = new \SQLite3($dbPath, SQLITE3_OPEN_READONLY);
            $db->busyTimeout(5000);

            // Prefer MAC; also include rows still keyed only by historical IPs for this MAC
            if ($mac !== '') {
                $stmt = $db->prepare(
                    'SELECT * FROM device_history
                     WHERE mac = :mac OR (:ip != "" AND ip = :ip)
                     ORDER BY timestamp DESC LIMIT 200'
                );
                $stmt->bindValue(':mac', $mac, SQLITE3_TEXT);
                $stmt->bindValue(':ip', $ip, SQLITE3_TEXT);
            } else {
                $stmt = $db->prepare(
                    'SELECT * FROM device_history WHERE ip = :ip ORDER BY timestamp DESC LIMIT 200'
                );
                $stmt->bindValue(':ip', $ip, SQLITE3_TEXT);
            }
            $result = $stmt->execute();

            $history = [];
            $ipTrail = [];
            while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
                $row['details'] = json_decode($row['details'] ?? '{}', true) ?: [];
                $history[] = $row;
                if (($row['field_name'] ?? '') === 'ip') {
                    $ipTrail[] = [
                        'timestamp' => $row['timestamp'],
                        'old_ip' => $row['old_value'],
                        'new_ip' => $row['new_value']
                    ];
                }
            }

            // Current IP as head of trail
            $currentIp = $ip;
            if ($mac !== '') {
                $stmt = $db->prepare('SELECT ip FROM devices WHERE mac = :mac');
                $stmt->bindValue(':mac', $mac, SQLITE3_TEXT);
                $dev = $stmt->execute()->fetchArray(SQLITE3_ASSOC);
                if ($dev && !empty($dev['ip'])) {
                    $currentIp = $dev['ip'];
                }
            }

            $db->close();

            return [
                "mac" => $mac,
                "ip" => $currentIp,
                "rows" => $history,
                "ip_history" => $ipTrail,
                "total" => count($history)
            ];
        } catch (\Exception $e) {
            error_log("Device history error: " . $e->getMessage());
            return ["error" => $e->getMessage(), "rows" => []];
        }
    }

    /**
     * GET /api/netdiscover/history/uptime?mac=...&ip=...&days=30
     */
    public function uptimeAction()
    {
        list($mac, $ip) = $this->resolveKey();
        $days = (int)$this->request->getQuery("days", "int", 30);

        if ($mac === '' && $ip === '') {
            return ["error" => "MAC or IP required"];
        }

        $dbPath = "/var/db/netdiscover/netdiscover.db";
        if (!file_exists($dbPath)) {
            return ["error" => "Database not found"];
        }

        try {
            $db = new \SQLite3($dbPath, SQLITE3_OPEN_READONLY);
            $db->busyTimeout(5000);

            $cutoff = time() - ($days * 86400);

            $sql = 'SELECT timestamp, old_value, new_value, field_name
                    FROM device_history
                    WHERE timestamp > :cutoff
                      AND event_type = "status_change"
                      AND (mac = :mac OR (:ip != "" AND ip = :ip))
                    ORDER BY timestamp ASC';
            $stmt = $db->prepare($sql);
            $stmt->bindValue(':cutoff', $cutoff, SQLITE3_INTEGER);
            $stmt->bindValue(':mac', $mac, SQLITE3_TEXT);
            $stmt->bindValue(':ip', $ip, SQLITE3_TEXT);
            $result = $stmt->execute();

            $changes = [];
            while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
                $changes[] = $row;
            }

            $totalTime = time() - $cutoff;
            $downTime = 0;
            $lastDown = null;

            foreach ($changes as $change) {
                $new = strtolower($change['new_value'] ?? '');
                $isDown = (str_contains($new, 'offline') || str_contains($new, 'missing') || str_contains($new, 'gone'));
                $isUp = (str_contains($new, 'online') || $new === 'back' || $new === 'up' || $new === 'active');
                if ($isDown) {
                    $lastDown = $change['timestamp'];
                } elseif ($lastDown && $isUp) {
                    $downTime += $change['timestamp'] - $lastDown;
                    $lastDown = null;
                }
            }
            if ($lastDown) {
                $downTime += time() - $lastDown;
            }

            $uptime = $totalTime > 0 ? (($totalTime - $downTime) / $totalTime) * 100 : 0;
            $db->close();

            return [
                "mac" => $mac,
                "ip" => $ip,
                "days" => $days,
                "uptime_percent" => round($uptime, 2),
                "status_changes" => count($changes),
                "downtime_seconds" => $downTime
            ];
        } catch (\Exception $e) {
            error_log("Uptime calculation error: " . $e->getMessage());
            return ["error" => $e->getMessage()];
        }
    }

    /**
     * GET /api/netdiscover/history/timeline?mac=...&ip=...&days=30
     */
    public function timelineAction()
    {
        list($mac, $ip) = $this->resolveKey();
        $days = (int)$this->request->getQuery("days", "int", 30);

        if ($mac === '' && $ip === '') {
            return ["error" => "MAC or IP required"];
        }

        $dbPath = "/var/db/netdiscover/netdiscover.db";
        if (!file_exists($dbPath)) {
            return ["error" => "Database not found"];
        }

        try {
            $db = new \SQLite3($dbPath, SQLITE3_OPEN_READONLY);
            $db->busyTimeout(5000);

            $cutoff = time() - ($days * 86400);

            if ($mac !== '') {
                $stmt = $db->prepare('SELECT first_seen, last_seen, status, connection_state, ip FROM devices WHERE mac = :mac');
                $stmt->bindValue(':mac', $mac, SQLITE3_TEXT);
            } else {
                $stmt = $db->prepare('SELECT first_seen, last_seen, status, connection_state, ip FROM devices WHERE ip = :ip');
                $stmt->bindValue(':ip', $ip, SQLITE3_TEXT);
            }
            $device = $stmt->execute()->fetchArray(SQLITE3_ASSOC);

            if (!$device) {
                $db->close();
                return ["error" => "Device not found"];
            }

            $sql = 'SELECT timestamp, event_type, old_value, new_value
                    FROM device_history
                    WHERE event_type = "status_change" AND timestamp > :cutoff
                      AND (mac = :mac OR (:ip != "" AND ip = :ip))
                    ORDER BY timestamp ASC';
            $stmt = $db->prepare($sql);
            $stmt->bindValue(':cutoff', $cutoff, SQLITE3_INTEGER);
            $stmt->bindValue(':mac', $mac, SQLITE3_TEXT);
            $stmt->bindValue(':ip', $ip !== '' ? $ip : ($device['ip'] ?? ''), SQLITE3_TEXT);
            $result = $stmt->execute();

            $changes = [];
            while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
                $changes[] = [
                    'timestamp' => $row['timestamp'],
                    'from' => $row['old_value'],
                    'to' => $row['new_value']
                ];
            }

            $segments = [];
            $start_time = max($cutoff, (int)$device['first_seen']);
            $end_time = time();
            $total_duration = max(1, $end_time - $start_time);

            if (count($changes) === 0) {
                $status = $device['connection_state'] ?: ($device['status'] ?: 'online');
                $segments[] = [
                    'status' => $status,
                    'start' => $start_time,
                    'end' => $end_time,
                    'duration' => $total_duration,
                    'percent' => 100.0
                ];
            } else {
                $current_time = $start_time;
                $current_status = 'online';
                foreach ($changes as $change) {
                    if ($change['timestamp'] > $current_time) {
                        $duration = $change['timestamp'] - $current_time;
                        $segments[] = [
                            'status' => $current_status,
                            'start' => $current_time,
                            'end' => $change['timestamp'],
                            'duration' => $duration,
                            'percent' => ($duration / $total_duration) * 100.0
                        ];
                    }
                    $current_status = $change['to'];
                    $current_time = $change['timestamp'];
                }
                if ($current_time < $end_time) {
                    $duration = $end_time - $current_time;
                    $segments[] = [
                        'status' => $current_status,
                        'start' => $current_time,
                        'end' => $end_time,
                        'duration' => $duration,
                        'percent' => ($duration / $total_duration) * 100.0
                    ];
                }
            }

            $db->close();

            return [
                "mac" => $mac,
                "ip" => $device['ip'] ?? $ip,
                "days" => $days,
                "start_time" => $start_time,
                "end_time" => $end_time,
                "segments" => $segments,
                "status_changes" => count($changes)
            ];
        } catch (\Exception $e) {
            error_log("Timeline error: " . $e->getMessage());
            return ["error" => $e->getMessage()];
        }
    }
}
