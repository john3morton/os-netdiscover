<?php
namespace OPNsense\NetDiscover\Api;

use OPNsense\Base\ApiControllerBase;

class AcknowledgeController extends ApiControllerBase
{
    /**
     * Mark a device as acknowledged (user viewed details)
     * v1.5.0: Clears lifecycle flags (new/changed/back)
     * POST /api/netdiscover/acknowledge/device
     * Payload: {"ip": "192.168.1.1"}
     */
    public function deviceAction()
    {
        $payload = $this->request->getJsonRawBody(true);
        if (!is_array($payload)) {
            $payload = $this->request->getPost();
        }
        
        $ip = isset($payload['ip']) ? trim($payload['ip']) : '';
        if (empty($ip)) {
            return ["result" => "failed", "error" => "IP required"];
        }
        
        $dbPath = "/var/db/netdiscover/netdiscover.db";
        if (!file_exists($dbPath)) {
            return ["result" => "failed", "error" => "Database not found"];
        }
        
        try {
            $db = new \SQLite3($dbPath, SQLITE3_OPEN_READWRITE);
            $db->busyTimeout(5000);
            
            // Clear lifecycle flags and set acknowledged
            $stmt = $db->prepare('
                UPDATE devices 
                SET flag_acknowledged = 1,
                    lifecycle_flags = "",
                    status = connection_state
                WHERE ip = :ip
            ');
            $stmt->bindValue(':ip', $ip, SQLITE3_TEXT);
            $stmt->execute();
            
            $db->close();
            
            return ["result" => "success", "ip" => $ip];
        } catch (\Exception $e) {
            error_log("Acknowledge device error: " . $e->getMessage());
            return ["result" => "failed", "error" => $e->getMessage()];
        }
    }
}

