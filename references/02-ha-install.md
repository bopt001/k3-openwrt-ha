# Phase 2 — Offline installation of HA 2024.3.3

The router cannot reliably reach PyPI or GitHub (DNS returns IPv6 with no route).
Everything is downloaded on a host machine and transferred over SSH.

## 2.1 Host-side offline bundle

Keep a directory (e.g. `ha_offline/`) containing:

| File | Purpose |
|---|---|
| `homeassistant-2024.3.3.tar.gz` | HA source tarball (PyPI sdist) |
| `home_assistant_frontend-20240307.0.whl` | frontend (~51MB) |
| `hass-nabucasa-0.78.0.tar.gz` | imported by helpers even without cloud |
| `requirements.txt` / `requirements_all.txt` / `package_constraints.txt` | pinned deps |
| `ha_install_offline.sh`, `ha_install_final.sh` | install drivers |

Use a PyPI mirror on the host where needed. GitHub raw downloads must be fixed up
on the host (`raw.githubusercontent.com` DNS/hosts) before fetching anything.

## 2.2 Transfer rules (learned the hard way)

- `scp` fails because the OpenWrt dropbear has no sftp subsystem. Use
  `cat file | ssh root@<ip> "cat > path"` instead.
- A single 51MB stdin transfer crashes the SSH session and corrupts the file.
  Use `split -b 8m`, append each chunk, then **verify MD5 on both sides** before
  extracting. Never skip the MD5 check.
- Large tar extraction on the device triggers the OOM killer (exit 137 / SIGTERM)
  because of the 32-bit `ZONE_NORMAL` watermark — even when `free` shows 200MB.
  Before extracting: stop HA and `echo 2048 > /proc/sys/vm/min_free_kbytes`,
  then restore `8192` afterwards. Note the files are often fully extracted even
  when the process is killed — count them instead of re-transferring.

## 2.3 Install steps

1. `opkg update`; install ~73 `python3-*` packages and `pip3` (23.2.1).
2. Install HA **without pip build**: copy the `homeassistant/` source tree straight
   into `/usr/lib/python3.11/site-packages/`. Re-add any root-level files lost to
   interrupted transfers (`config.py`, `core.py`, `requirements.py`, ...) and the
   missing components from a whitelist (39 of them in this run).
3. Verify `hass --skip-pip --version` returns `2024.3.3`.
4. Create `/etc/homeassistant/configuration.yaml` (see
   `scripts/configuration.yaml.example` — keep it minimal: `frontend:`, `http:`
   with `server_port: 8123`, `api:`).
5. Install `/etc/init.d/homeassistant` from `scripts/homeassistant.initd`, enable it.
6. Install the five shims from `scripts/shims/` with fake dist-info (phase 3).
7. Apply the three source patches (phase 3).
8. Start HA and wait 30-60 s (startup is slow on this CPU).

## 2.4 Verified end state

- `hass --skip-pip --version` = `2024.3.3`
- `/etc/init.d/homeassistant status` = running; enabled at boot
- Web root `http://<router>:8123/` -> 302 to onboarding;
  `/onboarding.html` -> 200; `/manifest.json` -> 200
- Web UI reachable from the LAN alias (e.g. `http://192.168.31.200:8123`)
- A local user account created via the onboarding wizard (do this in the browser;
  the API/token flow misbehaves on aiohttp 3.8.5).

## 2.5 Failure signatures during install

| Symptom | Cause | Fix |
|---|---|---|
| `hass` loops re-installing packages | missing `dist-info` metadata | add fake `<name>-<ver>.dist-info/METADATA` for every shim |
| Zombie / D-state `python3` eating RAM | timed-out `check_config` / pip | `killall -9 hass python3`; D-state needs a power cycle |
| Port 8123 LISTEN but empty HTTP reply | aiohttp 3.9 API on 3.8.5 | patch `components/http/__init__.py` |
| `ModuleNotFoundError` for a compiled lib | no wheel for musl/armv7 | pure-Python shim (phase 3) |
| OOM killer in `dmesg` | low `ZONE_NORMAL` | `min_free_kbytes=8192` + drop_caches before start |
| First boot extremely slow | USB extroot small-file IO | `mount -o remount,async /overlay` |

## 2.6 Credentials and hygiene

All credentials in the original runbook were removed from this public package.
Use your own passwords; never commit real tokens, account names, or LAN topology.
The LAN addresses here (`192.168.1.1`, `192.168.31.200`, `192.168.31.1`) are
illustrative examples of a common home-network layout, not secrets.
