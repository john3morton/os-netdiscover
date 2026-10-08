<?php
namespace OPNsense\NetDiscover\Api;

use OPNsense\Base\ApiControllerBase;

class ScanController extends ApiControllerBase
{
    /**
     * Perform exhaustive port scan on a device
     * POST /api/netdiscover/scan/ports
     * Payload: {"ip": "192.168.1.1", "range": "1-65535"} (range optional, default all ports)
     */
    public function portsAction()
    {
        $payload = $this->request->getJsonRawBody(true);
        if (!is_array($payload)) {
            $payload = $this->request->getPost();
        }
        
        $ip = isset($payload['ip']) ? trim($payload['ip']) : '';
        $range = isset($payload['range']) ? trim($payload['range']) : '1-1000';
        
        if (empty($ip)) {
            return ["status" => "error", "message" => "IP address required"];
        }
        
        // Validate IP
        if (!filter_var($ip, FILTER_VALIDATE_IP)) {
            return ["status" => "error", "message" => "Invalid IP address"];
        }
        
        // Check if device is reachable via ARP before scanning (v2.0.12)
        $arpCheck = @shell_exec('arp -an | grep -i ' . escapeshellarg($ip));
        if (empty($arpCheck)) {
            // Device not in ARP table - try ping to populate ARP
            $pingResult = @shell_exec('ping -c 1 -W 2 ' . escapeshellarg($ip) . ' 2>&1');
            
            // Check ARP again after ping
            $arpCheck = @shell_exec('arp -an | grep -i ' . escapeshellarg($ip));
            
            if (empty($arpCheck)) {
                // Device still not reachable - update status and return error
                $this->updateDeviceOfflineStatus($ip);
                
                return [
                    "status" => "error", 
                    "message" => "Device is not reachable (no ARP response). Device may be offline or blocking ICMP. Status updated to offline.",
                    "offline" => true
                ];
            }
        }
        
        // Parse range
        $parts = explode('-', $range);
        if (count($parts) != 2) {
            return ["status" => "error", "message" => "Invalid range format (use start-end)"];
        }
        
        $start_port = (int)$parts[0];
        $end_port = (int)$parts[1];
        
        if ($start_port < 1 || $end_port > 65535 || $start_port > $end_port) {
            return ["status" => "error", "message" => "Port range must be 1-65535"];
        }
        
        // Run nmap if available, otherwise use simple TCP connect scan
        $nmap = @shell_exec('command -v nmap');
        
        if ($nmap) {
            // Use nmap for faster, more reliable scanning (v1.7.2: optimized for 65K scan)
            $scan_size = $end_port - $start_port + 1;
            
            // Adjust timing based on scan size
            if ($scan_size > 10000) {
                // Full scan: aggressive timing, more parallel
                $timing = '-T5'; // Insane timing
                $max_retries = 0; // No retries for speed
            } else {
                $timing = '-T4'; // Aggressive
                $max_retries = 1;
            }
            
            $cmd = sprintf(
                'nmap -p %d-%d --open %s --max-retries %d --min-rate 1000 %s 2>&1',
                $start_port,
                $end_port,
                $timing,
                $max_retries,
                escapeshellarg($ip)
            );
            
            $output = shell_exec($cmd);
            
            // Parse nmap output
            $open_ports = [];
            if ($output) {
                preg_match_all('/^(\d+)\/tcp\s+open/m', $output, $matches);
                if (isset($matches[1])) {
                    $open_ports = array_map('intval', $matches[1]);
                }
            }
        } else {
            // Fallback to Python-based TCP connect scan
            $scriptPath = "/usr/local/opnsense/scripts/NetDiscover/port_scanner.py";
            if (file_exists($scriptPath)) {
                $cmd = sprintf(
                    'python3 %s %s %d %d 2>&1',
                    escapeshellarg($scriptPath),
                    escapeshellarg($ip),
                    $start_port,
                    $end_port
                );
                
                $output = shell_exec($cmd);
                $open_ports = json_decode($output, true) ?: [];
            } else {
                return ["status" => "error", "message" => "No port scanner available (nmap or port_scanner.py)"];
            }
        }
        
        // Store results in database
        if (count($open_ports) > 0) {
            $dbPath = "/var/db/netdiscover/netdiscover.db";
            if (file_exists($dbPath)) {
                try {
                    $db = new \SQLite3($dbPath, SQLITE3_OPEN_READWRITE);
                    $db->busyTimeout(5000);
                    
                    // Check if columns exist, add if missing
                    $result = $db->query("PRAGMA table_info(devices)");
                    $columns = [];
                    while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
                        $columns[] = $row['name'];
                    }
                    
                    if (!in_array('exhaustive_ports', $columns)) {
                        $db->exec('ALTER TABLE devices ADD COLUMN exhaustive_ports TEXT');
                    }
                    if (!in_array('exhaustive_ports_time', $columns)) {
                        $db->exec('ALTER TABLE devices ADD COLUMN exhaustive_ports_time INTEGER');
                    }
                    
                    $stmt = $db->prepare('
                        UPDATE devices 
                        SET exhaustive_ports = :ports,
                            exhaustive_ports_time = :time
                        WHERE ip = :ip
                    ');
                    
                    if ($stmt) {
                        $stmt->bindValue(':ports', json_encode($open_ports), SQLITE3_TEXT);
                        $stmt->bindValue(':time', time(), SQLITE3_INTEGER);
                        $stmt->bindValue(':ip', $ip, SQLITE3_TEXT);
                        $stmt->execute();
                    }
                    
                    $db->close();
                } catch (\Exception $e) {
                    error_log("Port scan database update error: " . $e->getMessage());
                    // Non-fatal - return results anyway
                }
            }
        }
        
        return [
            "status" => "success",
            "ip" => $ip,
            "range" => $range,
            "open_ports" => $open_ports,
            "count" => count($open_ports),
            "scanned" => ($end_port - $start_port + 1)
        ];
    }
    
    /**
     * Update device connection state to offline (v2.0.12)
     */
    private function updateDeviceOfflineStatus($ip)
    {
        $dbPath = "/var/db/netdiscover/netdiscover.db";
        if (!file_exists($dbPath)) {
            return;
        }
        
        try {
            $db = new \SQLite3($dbPath, SQLITE3_OPEN_READWRITE);
            $db->busyTimeout(5000);
            
            // Update connection state to offline
            $stmt = $db->prepare('
                UPDATE devices 
                SET connection_state = :state,
                    status = CASE 
                        WHEN lifecycle_flags != "" THEN lifecycle_flags || ", offline"
                        ELSE "offline"
                    END
                WHERE ip = :ip
            ');
            
            if ($stmt) {
                $stmt->bindValue(':state', 'offline', SQLITE3_TEXT);
                $stmt->bindValue(':ip', $ip, SQLITE3_TEXT);
                $stmt->execute();
            }
            
            $db->close();
        } catch (\Exception $e) {
            error_log("Failed to update device offline status: " . $e->getMessage());
        }
    }
}

