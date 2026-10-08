# NetDiscover OPNsense Plugin — Cursor migration notes (v0.6.2)

This repo is an OPNsense MVC plugin (Phalcon/Volt) plus a Python discovery agent and a dashboard widget.

## What changed vs 0.6.1 (important)
- **Fix:** rc script is now packaged to **/usr/local/etc/rc.d/netdiscoverd** (so `service netdiscoverd ...` works).
- **Fix:** `oui_file` default path is now the full path:
  `/usr/local/opnsense/scripts/NetDiscover/oui_sample.csv`

If you were seeing:
- `service netdiscoverd status` → “does not exist…”
- template reloads but no daemon control

…this is why.

## Repo map (high level)
- `src/opnsense/mvc/app/models/OPNsense/NetDiscover/*`  
  Model, Menu, ACL, forms
- `src/opnsense/mvc/app/controllers/OPNsense/NetDiscover/*`  
  MVC + API controllers
- `src/opnsense/mvc/app/views/OPNsense/NetDiscover/index.volt`  
  UI page
- `src/opnsense/scripts/NetDiscover/netdiscoverd.py`  
  Discovery agent
- `src/opnsense/service/templates/OPNsense/NetDiscover/*`  
  Template generating `/etc/rc.conf.d/netdiscoverd`
- `src/opnsense/service/conf/actions.d/actions_netdiscover.conf`  
  configd actions for UI ↔ system ops
- `src/opnsense/www/js/netdiscover/app.js`  
  UI JS
- `src/opnsense/www/js/widgets/*`  
  Dashboard widget
- `src/etc/rc.d/netdiscoverd`  
  rc script (service control)

## Build & package (on an OPNsense box)
From the repo root:
```sh
cd /usr/local/src/plugins/net-mgmt/os-netdiscover
make package
```

Resulting package:
```sh
ls -la work/pkg/*.pkg
```

Install / reinstall:
```sh
pkg add -f ./work/pkg/opnsensenetdiscover-devel-0.6.2.pkg
```

## Post-install checklist
```sh
# 1) Verify rc script location (this was the main bug)
ls -la /usr/local/etc/rc.d/netdiscoverd

# 2) Ensure template renders and file is generated
configctl template reload OPNsense/NetDiscover
ls -la /etc/rc.conf.d/netdiscoverd
sed -n '1,200p' /etc/rc.conf.d/netdiscoverd

# 3) Start the service
service netdiscoverd onestart
service netdiscoverd status
```

## Where to look when something says “ERR”
- configd logs: `/var/log/configd/latest.log`
- system logs: `/var/log/system/latest.log`

Useful greps:
```sh
grep -nEi 'NetDiscover|netdiscover|template|traceback|error' /var/log/configd/latest.log | tail -n 200
grep -nEi 'NetDiscover|netdiscover|rc\.conf|error' /var/log/system/latest.log  | tail -n 200
```

## Cursor / GPT CodeX agent tips
Good tasks for the agent:
- Validate Volt UI page loads and JS bundle is referenced correctly.
- Ensure menu entry points to the correct controller route.
- Confirm API endpoints used by the UI match the controllers.
- Confirm template fields align with `NetDiscover.xml` model tree (any mismatch can break template rendering).

