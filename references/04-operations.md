# Phase 4 — Operations, symptom -> fix table, and hardening

## 4.1 Daily commands

```sh
tail -f /etc/homeassistant/home-assistant.log   # the REAL log (not /var/log)
/etc/init.d/homeassistant restart
/etc/init.d/homeassistant status
logread | grep -iE "hass|oom|killed"           # kernel/OOM and procd messages
netstat -lnt | grep 8123
```

If HA wedges again: `killall -9 hass python3`, then start (the init script resets
the OOM watermark).

## 4.2 Symptom -> root cause -> fix

| # | Symptom | Root cause | Fix |
|---|---|---|---|
| 1 | Port LISTEN, HTTP empty reply | HA 2024.3.3 uses aiohttp 3.9 APIs, device has 3.8.5 | Patch A (drop `handler_cancellation`/`shutdown_timeout`) |
| 2 | After reboot: status=running but no process/port | `orjson.Fragment` wrote an object repr into `.storage/core.restore_state` | Fix orjson shim, reset that file's `data` to `[]`, clear pyc |
| 3 | Browser white screen, only the HA logo | Frontend transfer kept only `.js.gz`; static server looks for `.js` -> 404 | Re-transfer the full whl: `frontend_latest` + `static`; verify MD5 |
| 4 | Endless "Loading data" | `import numpy` fails during selector validation | numpy shim |
| 5 | LuCI: `Unhandled exception ... __entries__ (a nil value)` | `luci-theme-material_mod` incompatible with 23.05.6 | `uci set luci.main.mediaurlbase=/luci-static/bootstrap; uci commit luci; rm -rf /tmp/luci-modulecache /tmp/luci-indexcache*` |
| 6 | LuCI stuck in English after installing the Chinese pack | Old browser session cached the English assets | Log out + hard refresh (`Cmd+Shift+R`); server side is `lang="zh-CN"` |
| 7 | "Support for Python 3.11 is deprecated" repair warning | HA 2024.3.3 is the last 3.11 release | Harmless here — the version is frozen. Click "ignore" |
| 8 | `tar` killed with 137 / SIGTERM mid-extract | `ZONE_NORMAL` OOM killer, even with 200MB free | Stop HA, `min_free_kbytes=2048` during extraction, restore 8192 |
| 9 | opkg stuck in D state | extroot mounted `sync` | `mount -o remount,async /overlay` |
| 10 | SSH suddenly asks for a password | clearing `/tmp/luci-*` removed the authorized-key state | put the pubkey in both `/root/.ssh/authorized_keys` and `/etc/dropbear/authorized_keys`, `chmod 600`, restart dropbear |
| 11 | DNS / default route disappear | upstream re-DHCP on boot | `keep_net.sh` + cron every minute |

## 4.3 Frontend package completeness check

After transferring the frontend whl, confirm counts against the local whl:

```
frontend_latest : 719 *.js, 719 *.js.gz, 717 *.map
static/icons    : 23 files
static/images   : 50 files
```

The whl unpacks to ~152MB: `frontend_es5` (~55MB, legacy-browser fallback, can be
dropped), `frontend_latest` (~43MB) and `static` (~54MB) are required.

## 4.4 LuCI language (Chinese)

```sh
opkg update
opkg install luci-i18n-base-zh-cn       # required core pack
opkg install luci-i18n-adblock-zh-cn    # optional, for the adblock plugin
uci set luci.main.lang=zh_CN
uci commit luci
rm -rf /tmp/luci-modulecache /tmp/luci-indexcache*
```

Verify the server renders `<html lang="zh-CN">` and that
`/cgi-bin/luci/admin/translations/zh-CN` is referenced; translation catalogs
live in `/usr/lib/lua/luci/i18n/*.zh-cn.lmo`. A quick sanity check:

```sh
lua -e 'package.path="/usr/lib/lua/luci/?.lua;"..package.path; local i=require"luci.i18n"; i.setlanguage("zh_CN"); print(i.translate("System"))'
```

## 4.5 Boot resilience checklist

- `/etc/init.d/homeassistant` enabled, with OOM tuning inside `start_service()`.
- `/etc/rc.local`: LAN alias + default route + DNS + `min_free_kbytes=8192`.
- cron: `* * * * * /root/keep_net.sh`.
- All shims + dist-info + source patches live on the extroot, so they survive
  reboots (but **not** a firmware reflash).
- Do not rely on Wi-Fi during troubleshooting; the wired LAN alias is the
  dependable path.

## 4.6 SSH automation note

`expect` is usable for password login, but its `send` interprets `[a-z]` and `:,`
as Tcl syntax. Prefer restoring key-based auth and using plain `ssh -o BatchMode=yes`
for anything but trivial commands.
