---
name: k3-openwrt-ha
description: "Run an old Home Assistant (2024.3.3) directly on a Phicomm K3 router with OpenWrt 23.05, 32-bit ARM (armv7l), musl libc, 512MB RAM and no compiler. Covers CFE unbricking, flashing OpenWrt, USB extroot, offline HA installation, pure-Python shims replacing compiled wheels (orjson, lru, aiohttp_zlib_ng, fnv_hash_fast, numpy), source patches for aiohttp mismatch, OOM tuning, network keepalive, and the hard compatibility ceiling: HA 2024.4 and later, Python 3.12, HACS, Xiaomi Home and Midea Auto Cloud cannot be installed. Use when installing or troubleshooting Home Assistant on a resource-constrained OpenWrt router, especially Phicomm K3, or when asked whether a given HA integration or version can run there."
agent_created: true
---

# Home Assistant on Phicomm K3 / OpenWrt (32-bit ARM, offline)

Turn a Phicomm K3 (BCM4709C0, armv7l, 512MB RAM, 128MB Flash) flashed with
OpenWrt 23.05.6 into a machine that runs Home Assistant 2024.3.3 locally.
This is a **hard-won, verified procedure** — every step below was executed on
real hardware. Treat the "Compatibility ceiling" section as the most important
part: it prevents repeating days of failed work.

## When to use this skill

- Installing Home Assistant directly on a router running OpenWrt (not on a PC/NAS/Docker).
- Unbricking or flashing a Phicomm K3 (CFE, official -> tbvv custom -> OpenWrt).
- A Python package fails to install on musl/armv7 because no compiler or no
  compatible wheel exists, and a pure-Python shim is an acceptable substitute.
- Diagnosing HA that shows a listening port but no working HTTP response, a blank
  frontend, an endless "Loading data", or crashes after a reboot.
- Deciding whether a specific HA version, HACS, or a custom integration can run on
  this class of hardware.

## Start here: the compatibility ceiling (read first)

The single most valuable thing to know before attempting anything:

- **HA 2024.3.3 + Python 3.11.7 is the ceiling.** OpenWrt 23.05.6 ships only
  Python 3.11.7; there is no 3.12 package in opkg and no cross-compiler on the box.
- **HA >= 2024.4 requires Python >= 3.12** (`requires-python = ">=3.12.0"`,
  `REQUIRED_PYTHON_VER = (3, 12, 0)`). It cannot be installed by faking the version
  or with `--skip-pip`: the code uses 3.12 syntax/APIs and the whole dependency set
  is pinned to newer compiled extensions.
- **Therefore HACS, the official Xiaomi Home integration, and Midea Auto Cloud
  cannot be installed.** HACS needs HA >= 2024.4.1; Xiaomi Home needs >= 2024.4.4
  (newer: 2024.11.0); Midea Auto Cloud needs 2024.11.0 plus `lupa` (a C extension).
- **Rule of thumb:** any integration whose `manifest.json` requires a compiled C
  extension (orjson, numpy, lupa, cryptography, Pillow, ciso8601, SQLAlchemy, ...)
  or requires HA >= 2024.4 will not work. Only pure-Python, version-agnostic
  lightweight integrations are viable, installed manually into `custom_components/`.

Read `references/05-compatibility.md` for the full evidence and version matrix
before promising anyone that an add-on can be installed.

## Workflow

1. **Assess the goal against the ceiling.** If the user wants a modern integration
   or a newer HA, say so plainly and recommend a real machine (x86 mini PC, old
   laptop, NAS, or Docker). Do not start patching a doomed setup.
2. **Hardware/firmware prep** — CFE unbrick, flash OpenWrt, USB extroot.
   See `references/01-flash-extroot.md`.
3. **Offline HA install** — everything must be downloaded on a host machine and
   transferred; the router has no reliable direct access to PyPI/GitHub.
   See `references/02-ha-install.md`.
4. **Shims and patches** — the core reusable asset. Five pure-Python shims plus
   three source patches. See `references/03-shims-patches.md` and the ready-to-use
   files under `scripts/`.
5. **Operations & troubleshooting** — OOM tuning, network keepalive, reboot
   resilience, and a symptom -> cause -> fix table. See `references/04-operations.md`.
6. **Verify** — check process, port, HTTP status codes, and the real log file
   `/etc/homeassistant/home-assistant.log` (not `/var/log`).

## Critical environment facts

- Platform: `armv7l`, `cpython-311-arm-linux-musleabi` (musl, soft-float).
  piwheels' armv7 wheels are glibc/gnueabihf and are **ABI-incompatible** — never
  use them. PyPI wheels for these packages are also glibc-based.
- No `gcc`, `make`, or C headers on the device. Compiled wheels cannot be built.
- 32-bit ARM `ZONE_NORMAL` low memory is tiny. `dmesg` shows
  `Normal free < min` and the OOM killer fires. Always set
  `echo 8192 > /proc/sys/vm/min_free_kbytes` before starting HA (baked into the
  init script). For large tar extraction, temporarily lower it to 2048.
- The USB extroot must be mounted `async`; `sync` mount causes D-state deadlocks
  with thousands of small files. Use `mount -o remount,async /overlay`.
- Real HA log: `/etc/homeassistant/home-assistant.log`.
- HA must run with `--skip-pip` (place it after `hass`, before `--config`), otherwise
  it loops trying to pip-install missing modules and eventually wedges the box.
- Every shim needs a fake `<name>-<ver>.dist-info/METADATA` so HA/packaging
  believes the requirement is satisfied.

## Bundled resources

- `scripts/shims/` — the five pure-Python shims, exactly as deployed (orjson, lru,
  aiohttp_zlib_ng, fnv_hash_fast, numpy). Copy into `site-packages/`, add dist-info.
- `scripts/homeassistant.initd` — procd init script with OOM tuning built in.
- `scripts/keep_net.sh` — cron-driven guard for the LAN alias, default route and DNS.
- `scripts/configuration.yaml.example` — minimal known-good HA config.
- `references/` — detailed, load-on-demand documentation for each phase.

## Style of execution

Prefer giving the user exact commands to run rather than long explanations, and
verify each result over SSH before moving on. When transferring large files, use
`split -b 8m` + `cat part | ssh ... "cat >> file"` + MD5 check; a single large
stdin transfer crashes the SSH session and can corrupt files.
