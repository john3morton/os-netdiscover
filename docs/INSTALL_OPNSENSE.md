# Installing NetDiscover on OPNsense 26.7+

Build requires the official [opnsense/plugins](https://github.com/opnsense/plugins) tree so `../../Mk/plugins.mk` resolves. Place this plugin at `net-mgmt/netdiscover` under that checkout.

## Option A — Clone from GitHub on the firewall

```sh
# Clone official plugins (if you do not already have them)
cd /usr
git clone --depth 1 -b stable/26.7 https://github.com/opnsense/plugins.git

# Clone NetDiscover into the expected path
mkdir -p /usr/plugins/net-mgmt
cd /usr/plugins/net-mgmt
git clone https://github.com/john3morton/os-netdiscover.git netdiscover

cd /usr/plugins/net-mgmt/netdiscover
make package
pkg add -f ./work/pkg/os-netdiscover-2.1.2.pkg
chmod 755 /usr/local/etc/rc.d/netdiscoverd /usr/local/opnsense/scripts/NetDiscover/*.py
```

After `make package`, confirm the exact filename with:

```sh
ls -la ./work/pkg/os-netdiscover-*.pkg
```

## Option B — Sync from a development machine

Copy the plugin tree into the plugins checkout on the firewall (adjust host and paths):

```sh
# Example: from your workstation
scp -r ./os-netdiscover/* root@<firewall-host>:/usr/plugins/net-mgmt/netdiscover/

ssh root@<firewall-host> "cd /usr/plugins/net-mgmt/netdiscover && make package"
```

Then on the firewall:

```sh
pkg add -f ./work/pkg/os-netdiscover-2.1.2.pkg
chmod 755 /usr/local/etc/rc.d/netdiscoverd /usr/local/opnsense/scripts/NetDiscover/*.py
```

### Alternate layout used by `deploy.sh`

Some hosts keep plugins under `/usr/local/src/plugins/net-mgmt/os-netdiscover`. If you use [`deploy.sh`](../deploy.sh), set or match its `REPO_DIR` to that location; the packaging steps (`make package`, `pkg add`) are the same.

## Reload templates and restart GUI

```sh
configctl template reload OPNsense/NetDiscover
configctl webgui restart
```

## Enable and start the daemon

In the OPNsense UI: **Services → NetDiscover** (or the menu path shown after install), enable the plugin, then **Apply**.

```sh
service netdiscoverd restart
service netdiscoverd status
```

## Verify generated rc.conf.d

```sh
ls -la /etc/rc.conf.d/netdiscoverd
sed -n '1,200p' /etc/rc.conf.d/netdiscoverd
```

## Troubleshooting

- If `service netdiscoverd` says it “does not exist”, verify:
  `ls -la /usr/local/etc/rc.d/netdiscoverd`
- For template render errors:
  `grep -nEi 'NetDiscover|template|traceback|error' /var/log/configd/latest.log | tail -n 200`
- Confirm package name after build:
  `ls -la ./work/pkg/os-netdiscover-*.pkg`
