<?php
namespace OPNsense\NetDiscover\Api;

use OPNsense\Base\ApiControllerBase;

class DashboardController extends ApiControllerBase
{
    private function loadFromSQLite()
    {
        $dbPath = "/var/db/netdiscover/netdiscover.db";
        if (!file_exists($dbPath)) {
            return null;
        }

        try {
            $db = new \SQLite3($dbPath, SQLITE3_OPEN_READONLY);
            $db->busyTimeout(5000);

            $result = $db->query('SELECT COUNT(*) as cnt FROM devices');
            $total = $result->fetchArray(SQLITE3_ASSOC)['cnt'];

            $now = time();
            $stmt = $db->prepare('SELECT COUNT(*) as cnt FROM devices WHERE connection_state = :cs OR last_seen > :ls');
            $stmt->bindValue(':cs', 'online', SQLITE3_TEXT);
            $stmt->bindValue(':ls', $now - 600, SQLITE3_INTEGER);
            $up = $stmt->execute()->fetchArray(SQLITE3_ASSOC)['cnt'];

            // Prefer lifecycle_flags; fall back to composite status for older rows
            $stmt = $db->prepare(
                'SELECT COUNT(*) as cnt FROM devices
                 WHERE last_seen > :cutoff
                 AND (lifecycle_flags LIKE :flag OR status LIKE :status)'
            );
            $stmt->bindValue(':cutoff', $now - 86400, SQLITE3_INTEGER);
            $stmt->bindValue(':flag', '%new%', SQLITE3_TEXT);
            $stmt->bindValue(':status', '%new%', SQLITE3_TEXT);
            $new = $stmt->execute()->fetchArray(SQLITE3_ASSOC)['cnt'];

            $stmt->bindValue(':cutoff', $now - 86400, SQLITE3_INTEGER);
            $stmt->bindValue(':flag', '%changed%', SQLITE3_TEXT);
            $stmt->bindValue(':status', '%changed%', SQLITE3_TEXT);
            $changed = $stmt->execute()->fetchArray(SQLITE3_ASSOC)['cnt'];

            $stmt = $db->prepare(
                'SELECT COUNT(*) as cnt FROM devices
                 WHERE last_seen > :cutoff
                 AND (connection_state = :gone OR status LIKE :status)'
            );
            $stmt->bindValue(':cutoff', $now - 86400, SQLITE3_INTEGER);
            $stmt->bindValue(':gone', 'gone', SQLITE3_TEXT);
            $stmt->bindValue(':status', '%gone%', SQLITE3_TEXT);
            $gone = $stmt->execute()->fetchArray(SQLITE3_ASSOC)['cnt'];

            $result = $db->query('SELECT * FROM events ORDER BY timestamp DESC LIMIT 10');
            $events = [];
            while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
                $row['time'] = $row['timestamp'];
                $row['type'] = $row['event_type'];
                $row['details'] = json_decode($row['details'] ?? '{}', true) ?: [];
                $events[] = $row;
            }

            $db->close();

            return [
                'total' => $total,
                'up_10m' => $up,
                'new_24h' => $new,
                'changed_24h' => $changed,
                'gone_24h' => $gone,
                'recent_events' => $events
            ];
        } catch (\Exception $e) {
            error_log("SQLite dashboard read error: " . $e->getMessage());
            return null;
        }
    }

    public function summaryAction()
    {
        $sqliteData = $this->loadFromSQLite();
        if ($sqliteData !== null) {
            return $sqliteData;
        }

        return [
            "generated_at" => 0,
            "total" => 0,
            "up_10m" => 0,
            "new_24h" => 0,
            "changed_24h" => 0,
            "gone_24h" => 0,
            "recent_events" => []
        ];
    }
}
