# Contributing to NetDiscover

Thanks for helping improve this OPNsense plugin. Short contributions with a clear problem statement work best.

## Development setup

This plugin is built with the official [opnsense/plugins](https://github.com/opnsense/plugins) tree so `../../Mk/plugins.mk` resolves.

1. Clone OPNsense plugins (matching your firewall branch, e.g. `stable/26.7`):

   ```sh
   git clone --depth 1 -b stable/26.7 https://github.com/opnsense/plugins.git
   mkdir -p plugins/net-mgmt
   git clone https://github.com/john3morton/os-netdiscover.git plugins/net-mgmt/netdiscover
   ```

2. On an OPNsense build host (or compatible FreeBSD environment):

   ```sh
   cd plugins/net-mgmt/netdiscover
   make package
   pkg add -f ./work/pkg/os-netdiscover-*.pkg
   ```

   Or use `./deploy.sh` on the firewall after placing the repo where that script expects (see script header / `REPO_DIR`).

3. Full install steps: [docs/INSTALL_OPNSENSE.md](docs/INSTALL_OPNSENSE.md).

## Local checks (no FreeBSD required)

From the repo root on Linux/macOS:

```sh
python3 -m compileall -q src/opnsense/scripts/NetDiscover
python3 -m unittest discover -s tests -v
```

If PHP is installed:

```sh
find src -name '*.php' -print0 | xargs -0 -n1 php -l
```

GitHub Actions runs the same lint/tests on every push and pull request.

## Versioning

`Makefile` `PLUGIN_VERSION` is the source of truth. Keep these in sync when you bump a release:

- `README.md` version line and package example name
- `src/opnsense/mvc/app/models/OPNsense/NetDiscover/NetDiscover.xml` `<version>`
- `src/opnsense/mvc/app/views/OPNsense/NetDiscover/index.volt` UI badge (`vX.Y.Z`)
- `docs/INSTALL_OPNSENSE.md` example `.pkg` names
- Top entry in `CHANGELOG.md`

`deploy.sh` can rewrite the model/UI version from the Makefile during packaging; the tree should still match before you open a PR (`tests/test_version_consistency.py` enforces this).

## Pull requests

1. Branch from `main`.
2. Keep changes focused; do not mix unrelated refactors.
3. Add or update unit tests when you change Python helpers under `src/opnsense/scripts/NetDiscover/`.
4. Update `CHANGELOG.md` for user-visible changes.
5. Ensure CI is green.

## Reporting bugs / requesting features

Use the GitHub issue templates. Include OPNsense version, plugin version, and steps to reproduce when filing bugs.

## Code of conduct

Participation is governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
