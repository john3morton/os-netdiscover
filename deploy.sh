#!/bin/sh
set -euo pipefail

# Paths — alternate to /usr/plugins/net-mgmt/netdiscover (see docs/INSTALL_OPNSENSE.md).
# Override when needed: REPO_DIR=/path/to/checkout ./deploy.sh
REPO_DIR="${REPO_DIR:-/usr/local/src/plugins/net-mgmt/os-netdiscover}"
PKG_GLOB="work/pkg/os-netdiscover-*.pkg"

echo "==> Building package"
cd "${REPO_DIR}"

# sync version from Makefile into model and UI badge
VER=$(make -V PLUGIN_VERSION 2>/dev/null || grep -m1 PLUGIN_VERSION Makefile | awk -F'[= ]+' '{print $3}')
if [ -n "${VER}" ]; then
  /usr/bin/sed -i '' "s#<version>.*</version>#<version>${VER}</version>#g" src/opnsense/mvc/app/models/OPNsense/NetDiscover/NetDiscover.xml
  /usr/bin/sed -i '' "s#>v[0-9.]*<#>v${VER}<#g" src/opnsense/mvc/app/views/OPNsense/NetDiscover/index.volt
fi

make package

PKG_FILE=$(ls -t ${PKG_GLOB} | head -n 1)
if [ ! -f "${PKG_FILE}" ]; then
  echo "Package not found: ${PKG_GLOB}" >&2
  exit 1
fi

echo "==> Installing ${PKG_FILE}"
pkg add -f "${PKG_FILE}"

if [ -f /usr/local/etc/rc.d/netdiscoverd ]; then
  chmod 755 /usr/local/etc/rc.d/netdiscoverd || true
else
  echo "WARNING: /usr/local/etc/rc.d/netdiscoverd not found after install" >&2
fi

if [ -f /usr/local/opnsense/scripts/NetDiscover/netdiscoverd.py ]; then
  chmod 755 /usr/local/opnsense/scripts/NetDiscover/netdiscoverd.py || true
else
  echo "WARNING: /usr/local/opnsense/scripts/NetDiscover/netdiscoverd.py not found after install" >&2
fi

echo "==> Reloading templates"
configctl template reload OPNsense/NetDiscover

echo "==> Restarting web GUI"
configctl webgui restart

echo "==> Downloading Wireshark manufacturer database (enhanced with model hints)"
python3 /usr/local/opnsense/scripts/NetDiscover/update_wireshark_manuf.py || {
    echo "  Wireshark download failed, falling back to IEEE OUI..."
    python3 /usr/local/opnsense/scripts/NetDiscover/update_oui.py || echo "  Both downloads failed (not critical, will use existing data)"
}

echo "==> Restarting netdiscoverd"
service netdiscoverd restart
service netdiscoverd status

echo "==> Creating source archive"
ARCHIVE_DIR="${REPO_DIR}/archive"
mkdir -p "${ARCHIVE_DIR}"
ARCHIVE_FILE="${ARCHIVE_DIR}/os-netdiscover-devel-v${VER}.tar.gz"

# Create tar archive of source (exclude work directory and archives)
cd "${REPO_DIR}"
tar -czf "${ARCHIVE_FILE}" \
  --exclude='work' \
  --exclude='archive' \
  --exclude='.git' \
  --exclude='*.pkg' \
  .

if [ -f "${ARCHIVE_FILE}" ]; then
  echo "Source archived: ${ARCHIVE_FILE}"
  ls -lh "${ARCHIVE_FILE}"
else
  echo "WARNING: Archive creation failed"
fi

echo "Done."

