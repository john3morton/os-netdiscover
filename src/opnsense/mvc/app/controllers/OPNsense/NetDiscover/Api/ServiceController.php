<?php
namespace OPNsense\NetDiscover\Api;

use OPNsense\Base\ApiMutableServiceControllerBase;

class ServiceController extends ApiMutableServiceControllerBase
{
    protected static $internalServiceClass = '\\OPNsense\\NetDiscover\\NetDiscover';
    protected static $internalServiceTemplate = 'OPNsense/NetDiscover';
    protected static $internalServiceEnabled = 'general.enabled';
    protected static $internalServiceName = 'netdiscover';

    protected function reconfigureForceRestart()
    {
        return 1;
    }
    
    /**
     * Update OUI (MAC vendor) database from IEEE
     * POST /api/netdiscover/service/updateoui
     */
    public function updateouiAction()
    {
        $scriptPath = "/usr/local/opnsense/scripts/NetDiscover/update_oui.py";
        $ouiDbPath = "/var/db/netdiscover/oui.db";
        
        if (!file_exists($scriptPath)) {
            return ["status" => "error", "message" => "Update script not found"];
        }
        
        try {
            // Run update script
            $output = [];
            $returnCode = 0;
            exec("python3 " . escapeshellarg($scriptPath) . " --force 2>&1", $output, $returnCode);
            
            $outputText = implode("\n", $output);
            
            if ($returnCode === 0) {
                // Count entries in OUI database
                $count = 0;
                try {
                    $db = new \SQLite3($ouiDbPath, SQLITE3_OPEN_READONLY);
                    $result = $db->query('SELECT COUNT(*) as cnt FROM oui');
                    $row = $result->fetchArray(SQLITE3_ASSOC);
                    $count = $row['cnt'];
                    $db->close();
                } catch (\Exception $e) {
                    // Ignore count error
                }
                
                return [
                    "status" => "success",
                    "message" => "OUI database updated successfully",
                    "entries" => $count,
                    "output" => $outputText
                ];
            } else {
                return [
                    "status" => "error",
                    "message" => "Update failed",
                    "output" => $outputText
                ];
            }
        } catch (\Exception $e) {
            return [
                "status" => "error",
                "message" => $e->getMessage()
            ];
        }
    }
    
    /**
     * Update OUI database using Wireshark extended manuf file
     * POST /api/netdiscover/service/updatewireshark
     */
    public function updatewiresharkAction()
    {
        $scriptPath = "/usr/local/opnsense/scripts/NetDiscover/update_wireshark_manuf.py";
        $ouiDbPath = "/var/db/netdiscover/oui.db";
        
        if (!file_exists($scriptPath)) {
            return ["status" => "error", "message" => "Wireshark update script not found"];
        }
        
        try {
            $output = [];
            $returnCode = 0;
            exec("python3 " . escapeshellarg($scriptPath) . " --force 2>&1", $output, $returnCode);
            
            $outputText = implode("\n", $output);
            
            if ($returnCode === 0) {
                // Count entries in OUI database
                $count = 0;
                try {
                    $db = new \SQLite3($ouiDbPath, SQLITE3_OPEN_READONLY);
                    $result = $db->query('SELECT COUNT(*) as cnt FROM oui');
                    $row = $result->fetchArray(SQLITE3_ASSOC);
                    $count = $row['cnt'];
                    $db->close();
                } catch (\Exception $e) {
                    // Ignore count error
                }
                
                return [
                    "status" => "success",
                    "message" => "Wireshark manufacturer database updated successfully",
                    "entries" => $count,
                    "output" => $outputText
                ];
            } else {
                return [
                    "status" => "error",
                    "message" => "Wireshark update failed",
                    "output" => $outputText
                ];
            }
        } catch (\Exception $e) {
            return [
                "status" => "error",
                "message" => $e->getMessage()
            ];
        }
    }
    
    /**
     * Backfill vendor information for existing devices
     * GET /api/netdiscover/service/backfillvendors
     */
    public function backfillvendorsAction()
    {
        $dbPath = "/var/db/netdiscover/netdiscover.db";
        
        if (!file_exists($dbPath)) {
            return ["status" => "error", "message" => "Database not found"];
        }
        
        try {
            $db = new \SQLite3($dbPath, SQLITE3_OPEN_READWRITE);
            $db->busyTimeout(5000);
            
            // Find devices with MAC but no vendor
            $result = $db->query("
                SELECT ip, mac, vendor FROM devices 
                WHERE mac IS NOT NULL AND mac != '' 
                AND (vendor IS NULL OR vendor = '')
            ");
            
            $updated = 0;
            $now = time();
            
            while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
                $mac = $row['mac'];
                $ip = $row['ip'];
                
                // Extract OUI (first 3 octets)
                $macParts = explode(':', str_replace('-', ':', strtoupper($mac)));
                if (count($macParts) < 3) continue;
                
                $oui = implode(':', array_slice($macParts, 0, 3));
                
                // Lookup in OUI table
                $stmt = $db->prepare('SELECT vendor FROM oui WHERE oui = :oui');
                $stmt->bindValue(':oui', $oui, SQLITE3_TEXT);
                $ouiResult = $stmt->execute();
                $ouiRow = $ouiResult->fetchArray(SQLITE3_ASSOC);
                
                if ($ouiRow) {
                    $vendor = $ouiRow['vendor'];
                    
                    // Update device
                    $updateStmt = $db->prepare('UPDATE devices SET vendor = :vendor WHERE ip = :ip');
                    $updateStmt->bindValue(':vendor', $vendor, SQLITE3_TEXT);
                    $updateStmt->bindValue(':ip', $ip, SQLITE3_TEXT);
                    $updateStmt->execute();
                    
                    // Log to history
                    $histStmt = $db->prepare('
                        INSERT INTO device_history (ip, timestamp, event_type, field_name, old_value, new_value)
                        VALUES (:ip, :ts, "attribute_change", "vendor", "", :vendor)
                    ');
                    $histStmt->bindValue(':ip', $ip, SQLITE3_TEXT);
                    $histStmt->bindValue(':ts', $now, SQLITE3_INTEGER);
                    $histStmt->bindValue(':vendor', $vendor, SQLITE3_TEXT);
                    $histStmt->execute();
                    
                    $updated++;
                }
            }
            
            $db->close();
            
            return [
                "status" => "success",
                "message" => "Vendor backfill complete",
                "updated" => $updated
            ];
        } catch (\Exception $e) {
            return [
                "status" => "error",
                "message" => $e->getMessage()
            ];
        }
    }
}
