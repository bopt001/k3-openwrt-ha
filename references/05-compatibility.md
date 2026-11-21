# Phase 5 — Compatibility ceiling (the most useful section)

Everything below was verified against upstream sources on 2026-11-21. Apply this
*before* attempting to install anything on this device.

## 5.1 Device / software inventory

| Item | Value |
|---|---|
| Router | Phicomm K3, BCM4709C0 |
| CPU / ABI | `armv7l`, 32-bit, musl, soft-float (`cpython-311-arm-linux-musleabi`) |
| RAM / Flash | 512MB / 128MB (plus 27GB USB extroot) |
| OS | OpenWrt 23.05.6 (`bcm53xx/generic`, `arm_cortex-a9`) |
| Python | 3.11.7 (the only version in opkg) |
| aiohttp | 3.8.5 (opkg) |
| Home Assistant | 2024.3.3 (max achievable here) |
| Compiler | none (`gcc`, `make`, C headers all absent) |

## 5.2 Can HA be upgraded to 2024.11? No.

- HA 2024.11.0 declares `requires-python = ">=3.12.0"` in `pyproject.toml`,
  `REQUIRED_PYTHON_VER = (3, 12, 0)` in `const.py`, and PyPI lists
  "Requires: Python >=3.12.0". This is a hard install-time gate, not a warning.
- OpenWrt 23.05.6 has only `python3 3.11.7-1`; `opkg` contains no 3.12 package.
  Cross-compiling 3.12 for musl/armv7 without a toolchain is impractical.
- Even with 3.12, the dependency set is dominated by compiled C extensions:
  `orjson 3.10.7`, `cryptography 43.0.1`, `Pillow 10.4.0`, `ciso8601`,
  `lru-dict`, `fnv-hash-fast`, `aiohttp 3.10.x`, `SQLAlchemy 2.0.31`, `PyYAML`,
  `psutil`, `bcrypt`, `propcache`, `uv`. Shimming a handful was already painful;
  shimming all of them is not realistic.
- 512MB RAM barely runs 2024.3.3 with `min_free_kbytes=8192` and cache drops.
  Newer HA is heavier.
- `--skip-pip` or hand-editing the version cannot bypass the Python requirement:
  the 2024.11 code uses 3.12 syntax/APIs and newer library versions.

**Conclusion:** 2024.3.3 is the ceiling, and even that runs only because of five
shims plus three source patches. Changing the HA version means rebuilding the
entire stack.

## 5.3 HACS — cannot be installed

HACS prerequisites (official docs) require **HA >= 2024.4.1**, a supported
installation type, a GitHub account for device activation, and stable outbound
access to GitHub and Cloudflare. This device fails all of those: version too old,
network maintained by a per-minute cron guard, no reliable GitHub/Cloudflare path.

Install custom integrations manually into `custom_components/` instead.

Note: from HA 2026.11 onwards HACS is built in as "Marketplace" — irrelevant here
since the device cannot reach 2024.4, let alone 2026.11.

## 5.4 Common integrations — verdicts

| Integration | Requirement | Verdict |
|---|---|---|
| Xiaomi Home (official, `XiaoMi/ha_xiaomi_home`) | HA Core >= 2024.4.4 (newer docs: 2024.11.0), OS >= 13.0 | Not installable — uses 2024.4+ internal APIs |
| Midea Auto Cloud (`sususweet`, v0.2.4 included) | `homeassistant: 2024.11.0`, `requirements: ["lupa>=2.0"]` | Not installable — `lupa` is a C extension (Python<->Lua51) used for all device codec work in `core/lua_runtime.py`; no wheel, no compiler |
| HACS | HA >= 2024.4.1 | Not installable |
| Any integration with a compiled C extension in `manifest.json` | compiler or compatible wheel | Not installable |

`lupa` deserves emphasis: it is not an optional helper. `build_query`,
`build_control`, `decode_status` all call `lupa.lua51.LuaRuntime()` to execute
Midea's downloaded lua protocol files. There is no shim path. piwheels has no
lupa armv7 wheel, PyPI wheels are glibc/x86/aarch64 — both the compile path and
the prebuilt path are closed.

## 5.5 Decision rule

> If `manifest.json` contains a compiled C extension, or `hacs.json` /
> docs require HA >= 2024.4, it will not run on this device.
> Only pure-Python, version-agnostic, lightweight integrations are candidates,
> installed by copying a directory into `custom_components/` and restarting HA.

## 5.6 If modern integrations are actually required

Move HA to a real machine (x86 mini PC, retired laptop, NAS, or Docker) running a
current HA. Keep the K3 as a pure router / AP. Legacy LAN-side integrations
(e.g. token-based `msmart`/`xiaomi_miio` style) may still work on the old HA, but
they cover fewer devices and need per-device tokens.

This is a hardware ceiling, not a configuration mistake. Say so plainly rather
than starting another round of patching.
