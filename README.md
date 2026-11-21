# Home Assistant on a Phicomm K3 / OpenWrt 23.05

A verified, end-to-end record of getting **Home Assistant 2024.3.3** running
*natively* on a Phicomm K3 router — a 32-bit ARM (armv7l), musl-libc, 512MB RAM,
128MB Flash box with **no compiler**. Also a WorkBuddy Skill: the repo root is a
valid skill (`SKILL.md`), so cloning it into `~/.workbuddy/skills/` makes the
procedure available to an agent.

> This is a record of what worked on real hardware, including the dead ends.
> It is not a general recommendation: running modern HA on a router is a bad
> idea on most days. See the compatibility ceiling below.

## TL;DR — the ceiling

- **HA 2024.3.3 / Python 3.11.7 is the maximum** on OpenWrt 23.05.6.
- **HA >= 2024.4 requires Python >= 3.12** (hard gate), which this device cannot
  provide. So it **cannot** be upgraded to 2024.11.
- **HACS, the official Xiaomi Home integration, and Midea Auto Cloud cannot be
  installed** — version requirements and/or compiled C extensions (`lupa`,
  `numpy`, `orjson`, ...).
- Anything requiring a compiled C extension or HA >= 2024.4 is out. Only
  pure-Python, version-agnostic lightweight integrations work, installed
  manually into `custom_components/`.

If those integrations are the actual goal, run a current HA on a real machine
(x86 mini PC / old laptop / NAS / Docker) and keep the K3 as a router.

## What's inside

```
SKILL.md                       Skill entry point (start here)
references/
  01-flash-extroot.md          CFE unbrick -> OpenWrt -> USB extroot -> network
  02-ha-install.md             Offline install of HA 2024.3.3
  03-shims-patches.md          The core: 5 pure-Python shims + 3 source patches
  04-operations.md             Symptom -> cause -> fix table, boot hardening, LuCI
  05-compatibility.md          Version matrix and "what cannot be installed"
scripts/
  shims/                       The 5 shims, exactly as deployed
  install_shims.sh             Idempotent on-device shim installer
  homeassistant.initd          procd init script with OOM tuning
  keep_net.sh                  cron network/DNS keepalive
  configuration.yaml.example   Minimal known-good HA config
```

## The interesting part

A musl/armv7 device cannot build or install Rust/C-extension wheels. Rather than
giving up, five compiled dependencies were replaced by small pure-Python shims
with fake `dist-info` metadata so HA stops trying to reinstall them:

`orjson`, `lru`, `aiohttp_zlib_ng`, `fnv_hash_fast`, `numpy`.

Two non-obvious bugs are documented with fixes:

1. **`orjson.Fragment`** — a naive shim serializes a `Fragment` into an object
   repr string, silently corrupting HA's `.storage/` files. The crash only
   appears after the next reboot. The shipped shim unwraps Fragments correctly.
2. **aiohttp 3.9 API on 3.8.5** — 8123 listens but returns an empty reply until
   `AppRunner(self.app, handler_cancellation=True, shutdown_timeout=10)` is
   reduced to `AppRunner(self.app)`.

Plus the 32-bit ARM `ZONE_NORMAL` OOM problem (`min_free_kbytes=8192` before
every HA start), the `sync`-mount extroot deadlock, and the frontend whl that
must be transferred in full (`.js`, not just `.js.gz`).

## Verified end state

- `hass --skip-pip --version` -> `2024.3.3`
- Web root -> 302 to onboarding; `/onboarding.html` and `/manifest.json` -> 200
- HA enabled at boot, guarded by OOM tuning and a per-minute network keepalive
- LuCI reachable, English/Chinese switchable, `bootstrap` theme

## Privacy

No credentials, tokens, real host paths or device identifiers are included.
LAN addresses shown are RFC1918 examples. Passwords and account names from the
original runbook were removed before publishing. Use your own credentials.

## Disclaimer

Flashing firmware and writing raw flash can permanently brick a device. Follow
the "never cut power mid-write" rule, verify MD5 on every transfer, and keep CFE
intact. This repo documents a specific device and a specific OpenWrt release;
other hardware will differ. No warranty.

## License

MIT — see [LICENSE](LICENSE).
