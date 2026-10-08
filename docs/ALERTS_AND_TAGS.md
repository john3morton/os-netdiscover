# Alerts and Auto-Tags (v2.1.0)

Optional features — disabled until you create config files on the firewall.

## Webhook alerts

Create `/var/db/netdiscover/alerts.json`:

```json
{
  "enabled": true,
  "webhook_url": "https://hooks.example.com/netdiscover",
  "events": ["new", "gone", "back", "changed"]
}
```

On each scan cycle, matching events are POSTed as JSON:

```json
{
  "source": "os-netdiscover",
  "event": "new",
  "ip": "192.168.3.50",
  "mac": "aa:bb:cc:dd:ee:ff",
  "hostname": "sensor-1",
  "time": 1710000000,
  "details": {}
}
```

## Auto-tag rules

Create `/var/db/netdiscover/auto_tags.json`:

```json
{
  "enabled": true,
  "rules": [
    {"match": {"vendor_contains": "Apple"}, "add_tags": ["apple"]},
    {"match": {"hostname_regex": "^iot-"}, "add_tags": ["iot"]},
    {"match": {"subnet_prefix": "192.168.10."}, "add_tags": ["vlan10"]},
    {"match": {"device_type": "Printer"}, "add_tags": ["print"]}
  ]
}
```

Rules only **add** tags; they do not remove user tags.

Restart the daemon after editing either file:

```sh
service netdiscoverd restart
```
