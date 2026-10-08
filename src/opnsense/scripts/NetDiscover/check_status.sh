#!/bin/sh
# NetDiscover Status Checker
# Quick diagnostic script

echo "==> NetDiscover Status Check"
echo ""

echo "Service Status:"
service netdiscoverd status
echo ""

echo "Database Files:"
ls -lh /var/db/netdiscover/*.db 2>/dev/null || echo "No .db files found"
ls -lh /var/db/netdiscover/*.json 2>/dev/null || echo "No .json files found"
echo ""

echo "Device Count:"
if [ -f /var/db/netdiscover/netdiscover.db ]; then
  sqlite3 /var/db/netdiscover/netdiscover.db "SELECT COUNT(*) as devices FROM devices;" 2>/dev/null || echo "Error querying devices"
else
  echo "netdiscover.db not found"
fi
echo ""

echo "Events Count:"
if [ -f /var/db/netdiscover/netdiscover.db ]; then
  sqlite3 /var/db/netdiscover/netdiscover.db "SELECT COUNT(*) as events FROM events;" 2>/dev/null || echo "Error querying events"
  echo ""
  echo "Recent Events (last 5):"
  sqlite3 /var/db/netdiscover/netdiscover.db "SELECT datetime(timestamp, 'unixepoch') as time, event_type, ip, hostname FROM events ORDER BY timestamp DESC LIMIT 5;" 2>/dev/null || echo "Error querying events"
else
  echo "netdiscover.db not found"
fi
echo ""

echo "OUI Database:"
if [ -f /var/db/netdiscover/oui.db ]; then
  sqlite3 /var/db/netdiscover/oui.db "SELECT COUNT(*) as vendors FROM oui;" 2>/dev/null || echo "Error querying OUI"
else
  echo "oui.db not found - run update_oui.py to download"
fi
echo ""

echo "Startup Log (last 30 lines):"
if [ -f /var/db/netdiscover/startup.log ]; then
  tail -30 /var/db/netdiscover/startup.log
else
  echo "No startup log found"
fi
echo ""

echo "Error Log (last 10 lines):"
if [ -f /var/db/netdiscover/netdiscoverd.log ]; then
  tail -10 /var/db/netdiscover/netdiscoverd.log
else
  echo "No errors logged (or log file doesn't exist)"
fi

