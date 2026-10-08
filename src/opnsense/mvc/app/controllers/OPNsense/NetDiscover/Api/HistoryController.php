<?php
namespace OPNsense\NetDiscover\Api;

use OPNsense\Base\ApiControllerBase;

class HistoryController extends ApiControllerBase
{
    /**
     * Get history for a specific device
     * GET /api/netdiscover/history/device?ip=192.168.1.1
     */
    public function deviceAction()
    {
        $ip = $this->request->getQuery("ip", "string", "");
        if (empty($ip)) {
            return ["error" => "IP address required", "rows" => []];
        }
        
        $dbPath = "/var/db/netdiscover/netdiscover.db";
        if (!file_exists($dbPath)) {
            return ["error" => "Database not found", "rows" => []];
        }
        
        try {
            $db = new \SQLite3($dbPath, SQLITE3_OPEN_READONLY);
            $db->busyTimeout(5000);
            
            $stmt = $db->prepare('SELECT * FROM device_history WHERE ip = :ip ORDER BY timestamp DESC LIMIT 100');
            $stmt->bindValue(':ip', $ip, SQLITE3_TEXT);
            $result = $stmt->execute();
            
            $history = [];
            while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
                $row['details'] = json_decode($row['details'] ?? '{}', true) ?: [];
                $history[] = $row;
            }
            
            $db->close();
            
            return [
                "ip" => $ip,
                "rows" => $history,
                "total" => count($history)
            ];
        } catch (\Exception $e) {
            error_log("Device history error: " . $e->getMessage());
            return [
                "error" => $e->getMessage(),
                "rows" => []
            ];
        }
    }
    
    /**
     * Get device uptime statistics
     * GET /api/netdiscover/history/uptime?ip=192.168.1.1&days=30
     */
    public function uptimeAction()
    {
        $ip = $this->request->getQuery("ip", "string", "");
        $days = (int)$this->request->getQuery("days", "int", 30);
        
        if (empty($ip)) {
            return ["error" => "IP address required"];
        }
        
        $dbPath = "/var/db/netdiscover/netdiscover.db";
        if (!file_exists($dbPath)) {
            return ["error" => "Database not found"];
        }
        
        try {
            $db = new \SQLite3($dbPath, SQLITE3_OPEN_READONLY);
            $db->busyTimeout(5000);
            
            $cutoff = time() - ($days * 86400);
            
            // Get status changes
            $sql = 'SELECT timestamp, old_value, new_value ' .
                   'FROM device_history ' .
                   'WHERE ip = :ip AND event_type = "status_change" AND timestamp > :cutoff ' .
                   'ORDER BY timestamp ASC';
            $stmt = $db->prepare($sql);
            $stmt->bindValue(':ip', $ip, SQLITE3_TEXT);
            $stmt->bindValue(':cutoff', $cutoff, SQLITE3_INTEGER);
            $result = $stmt->execute();
            
            $changes = [];
            while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
                $changes[] = $row;
            }
            
            // Calculate uptime percentage
            $totalTime = time() - $cutoff;
            $downTime = 0;
            $lastDown = null;
            
            foreach ($changes as $change) {
                if ($change['new_value'] === 'gone') {
                    $lastDown = $change['timestamp'];
                } elseif ($lastDown && in_array($change['new_value'], ['back', 'up', 'active'])) {
                    $downTime += $change['timestamp'] - $lastDown;
                    $lastDown = null;
                }
            }
            
            // If currently down, add time until now
            if ($lastDown) {
                $downTime += time() - $lastDown;
            }
            
            $uptime = $totalTime > 0 ? (($totalTime - $downTime) / $totalTime) * 100 : 0;
            
            $db->close();
            
            return [
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
     * Get timeline data for visual graph
     * GET /api/netdiscover/history/timeline?ip=192.168.1.1&days=30
     */
    public function timelineAction()
    {
        $ip = $this->request->getQuery("ip", "string", "");
        $days = (int)$this->request->getQuery("days", "int", 30);
        
        if (empty($ip)) {
            return ["error" => "IP address required"];
        }
        
        $dbPath = "/var/db/netdiscover/netdiscover.db";
        if (!file_exists($dbPath)) {
            return ["error" => "Database not found"];
        }
        
        try {
            $db = new \SQLite3($dbPath, SQLITE3_OPEN_READONLY);
            $db->busyTimeout(5000);
            
            $cutoff = time() - ($days * 86400);
            
            // Get device info
            $stmt = $db->prepare('SELECT first_seen, last_seen, status FROM devices WHERE ip = :ip');
            $stmt->bindValue(':ip', $ip, SQLITE3_TEXT);
            $result = $stmt->execute();
            $device = $result->fetchArray(SQLITE3_ASSOC);
            
            if (!$device) {
                $db->close();
                return ["error" => "Device not found"];
            }
            
            // Get all status changes
            $sql = 'SELECT timestamp, event_type, old_value, new_value ' .
                   'FROM device_history ' .
                   'WHERE ip = :ip AND event_type = "status_change" AND timestamp > :cutoff ' .
                   'ORDER BY timestamp ASC';
            $stmt = $db->prepare($sql);
            $stmt->bindValue(':ip', $ip, SQLITE3_TEXT);
            $stmt->bindValue(':cutoff', $cutoff, SQLITE3_INTEGER);
            $result = $stmt->execute();
            
            $changes = [];
            while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
                $changes[] = [
                    'timestamp' => $row['timestamp'],
                    'from' => $row['old_value'],
                    'to' => $row['new_value']
                ];
            }
            
            // Build timeline segments
            $segments = [];
            $start_time = max($cutoff, $device['first_seen']);
            $end_time = time();
            $total_duration = $end_time - $start_time;
            
            if (count($changes) === 0) {
                // No status changes - single segment
                $status = $device['status'] ?: 'up';
                $segments[] = [
                    'status' => $status,
                    'start' => $start_time,
                    'end' => $end_time,
                    'duration' => $total_duration,
                    'percent' => 100.0
                ];
            } else {
                // Build segments from status changes
                $current_time = $start_time;
                $current_status = 'up'; // Assume up initially
                
                foreach ($changes as $change) {
                    // Add segment for current status
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
                
                // Final segment to now
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
                "ip" => $ip,
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

