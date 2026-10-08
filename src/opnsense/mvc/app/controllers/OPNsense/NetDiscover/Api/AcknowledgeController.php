<?php
namespace OPNsense\NetDiscover\Api;

use OPNsense\Base\ApiControllerBase;

class AcknowledgeController extends ApiControllerBase
{
    /**
     * Mark a device as acknowledged (user viewed details)
     * POST /api/netdiscover/acknowledge/device
     * Payload: {"mac":"aa:bb:..."} or {"ip":"..."}
     */
    public function deviceAction()
    {
        $payload = $this->request->getJsonRawBody(true);
        if (!is_array($payload)) {
            $payload = $this->request->getPost();
        }

        $mac = DeviceIdentity::keyFromPayload(is_array($payload) ? $payload : []);
        $ip = isset($payload['ip']) ? trim($payload['ip']) : '';
        if ($mac === '') {
            return ["result" => "failed", "error" => "MAC or IP required"];
        }

        $dbPath = "/var/db/netdiscover/netdiscover.db";
        if (!file_exists($dbPath)) {
            return ["result" => "failed", "error" => "Database not found"];
        }

        try {
            $db = new \SQLite3($dbPath, SQLITE3_OPEN_READWRITE);
            $db->busyTimeout(5000);

            $stmt = $db->prepare('
                UPDATE devices
                SET flag_acknowledged = 1,
                    lifecycle_flags = "",
                    status = connection_state
                WHERE mac = :mac OR (:ip != "" AND ip = :ip)
            ');
            $stmt->bindValue(':mac', $mac, SQLITE3_TEXT);
            $stmt->bindValue(':ip', $ip, SQLITE3_TEXT);
            $stmt->execute();

            $db->close();

            return ["result" => "success", "mac" => $mac, "ip" => $ip];
        } catch (\Exception $e) {
            error_log("Acknowledge device error: " . $e->getMessage());
            return ["result" => "failed", "error" => $e->getMessage()];
        }
    }
}
