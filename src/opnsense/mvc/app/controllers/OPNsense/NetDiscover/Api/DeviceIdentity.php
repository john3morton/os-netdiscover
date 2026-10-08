<?php
namespace OPNsense\NetDiscover\Api;

/**
 * Shared device identity helpers (v2.1.0) — MAC is canonical key.
 */
class DeviceIdentity
{
    public static function normalizeMac($mac)
    {
        if ($mac === null || $mac === '') {
            return '';
        }
        $m = strtolower(trim(str_replace('-', ':', (string)$mac)));
        if (str_starts_with($m, 'ip:')) {
            return $m;
        }
        $parts = array_values(array_filter(explode(':', $m), function ($p) {
            return $p !== '';
        }));
        if (count($parts) !== 6) {
            return '';
        }
        $out = [];
        foreach ($parts as $p) {
            if (!ctype_xdigit($p) || strlen($p) > 2) {
                return '';
            }
            $out[] = sprintf('%02x', hexdec($p));
        }
        return implode(':', $out);
    }

    /**
     * Resolve device key from request payload (mac preferred, else ip:ADDR).
     */
    public static function keyFromPayload(array $payload)
    {
        $mac = self::normalizeMac($payload['mac'] ?? '');
        $ip = trim((string)($payload['ip'] ?? ''));
        if ($mac !== '') {
            return $mac;
        }
        if ($ip !== '') {
            return 'ip:' . $ip;
        }
        return '';
    }

    public static function displayMac($mac)
    {
        $m = (string)$mac;
        if ($m === '' || str_starts_with($m, 'ip:')) {
            return '';
        }
        return $m;
    }

    public static function esc($value)
    {
        return htmlspecialchars((string)$value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
    }
}
