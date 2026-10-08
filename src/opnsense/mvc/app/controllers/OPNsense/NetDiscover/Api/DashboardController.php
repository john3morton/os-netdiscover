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

            $total = (int)$db->querySingle('SELECT COUNT(*) FROM devices');
            $now = time();

            // Online only (do not OR with last_seen — that inflated Up to Total)
            $stmt = $db->prepare('SELECT COUNT(*) FROM devices WHERE connection_state = :cs');
            $stmt->bindValue(':cs', 'online', SQLITE3_TEXT);
            $up = (int)$stmt->execute()->fetchArray(SQLITE3_NUM)[0];

            // Token-aware flag match: avoid status LIKE '%new%' matching stale display strings
            $flagCount = function ($token) use ($db, $now) {
                $stmt = $db->prepare(
                    "SELECT COUNT(*) FROM devices
                     WHERE last_seen > :cutoff
                       AND (
                         lifecycle_flags = :exact
                         OR lifecycle_flags LIKE :prefix
                         OR lifecycle_flags LIKE :mid
                         OR lifecycle_flags LIKE :suffix
                       )"
                );
                $stmt->bindValue(':cutoff', $now - 86400, SQLITE3_INTEGER);
                $stmt->bindValue(':exact', $token, SQLITE3_TEXT);
                $stmt->bindValue(':prefix', $token . ',%', SQLITE3_TEXT);
                $stmt->bindValue(':mid', '%,' . $token . ',%', SQLITE3_TEXT);
                $stmt->bindValue(':suffix', '%,' . $token, SQLITE3_TEXT);
                return (int)$stmt->execute()->fetchArray(SQLITE3_NUM)[0];
            };

            $new = $flagCount('new');
            $changed = $flagCount('changed');

            $stmt = $db->prepare(
                'SELECT COUNT(*) FROM devices
                 WHERE last_seen > :cutoff AND connection_state = :gone'
            );
            $stmt->bindValue(':cutoff', $now - 86400, SQLITE3_INTEGER);
            $stmt->bindValue(':gone', 'gone', SQLITE3_TEXT);
            $gone = (int)$stmt->execute()->fetchArray(SQLITE3_NUM)[0];

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
