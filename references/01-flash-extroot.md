# Phase 1 — Unbrick, flash OpenWrt, USB extroot

Target hardware: Phicomm K3, BCM4709C0, armv7l, 512MB RAM, 128MB Flash.
Firmware chain: stock -> tbvv custom `K3_V21.6.14.131_tb_beta.bin` ->
`openwrt-k3-23.05.6.trx` (OpenWrt 23.05.6, `bcm53xx/generic`).

## 1.1 CFE unbrick (only if the box no longer responds)

Key finding: CFE (`mtd0`) survives a bad firmware write, so the device is
recoverable as long as CFE was not overwritten.

1. Power off. Connect the cable to a **LAN** port (not WAN).
2. Set the host to `192.168.2.2` (CFE listens at `192.168.2.1`).
3. Hold **reset**, apply power, wait 10 s, release.
4. Open `http://192.168.2.1` — a blue "Broadcom - CFE miniWeb Server" means success.
5. Upload the stock image `SW_K3_703004697_V21.6.8.46.bin` (~33MB).
6. Wait 3-5 minutes. **Never cut power during a flash write.**

## 1.2 Enable telnet via config restore

Stock firmware cannot flash the custom image directly:

1. Log in at `http://192.168.2.1`.
2. Settings -> Backup/Restore -> restore `K3开启telnet配置.dat`
   (the ~65KB file is the valid one; the ~40KB one is corrupt).
3. After reboot, log in with the new password printed by the custom firmware docs.
4. Settings -> Storage -> change the username back to `admin`, save.
   Telnet is now open (passwordless root).

## 1.3 Flash the custom (tbvv) firmware — the "never reboot early" lesson

A 25MB `cat image > /dev/mtdblock6` takes 30-60 s. A previous attempt rebooted
after only 8 s and produced a half-written firmware = brick. **Chain the write and
the reboot in one command so the reboot can only happen after the write returns.**

On the host, serve the file over HTTP:

```bash
cd ~/k3_tftp && python3 -m http.server 8080 --bind 192.168.2.2
```

From another terminal, telnet in (`nc 192.168.2.1 23`) and paste exactly this
single line:

```sh
cd /tmp && curl -o k3.bin http://192.168.2.2:8080/k3_root.bin && md5sum k3.bin && sync && cat k3.bin >/dev/mtdblock6 && echo WRITE_FINISHED && sync && reboot
```

Expect 1-3 minutes of no output — this is the flash write, and it is normal.
Wait for `WRITE_FINISHED`. Disconnecting or cutting power mid-write bricks it.

## 1.4 Flash OpenWrt from the custom firmware web UI

The custom firmware's "manual upgrade" page accepts arbitrary images, including
OpenWrt — **no CFE downgrade needed** (a widespread misconception).

1. Log in to the custom firmware UI at `192.168.2.1`.
2. Settings -> Manual upgrade -> select `openwrt-k3-23.05.6.trx` (~8.9MB), upload.
3. Wait 3-5 minutes, do not cut power.
4. The router comes up at `192.168.1.1`, OpenWrt with no password:
   `ssh root@192.168.1.1`.

If it hangs at the PHICOMM logo, use the custom firmware SSH toolbox ->
System & Others -> CFE downgrade, then re-flash.

## 1.5 USB extroot (128MB Flash is far too small for HA)

A 27GB USB stick (`/dev/sda2`, ext4) becomes `/overlay`, giving a ~27GB root.

The trap: the stick's existing `upper/` was a stale 2.4MB copy missing `www`,
`network`, `fstab`. Rebooting onto it silently loses all configuration. Correct
sequence (all executed and verified):

```sh
tar -czf /mnt/sda2/upper_backup.tar.gz -C /overlay upper   # back up current upper
rm -rf /mnt/sda2/upper && mkdir -p /mnt/sda2/upper
cp -a /overlay/upper/. /mnt/sda2/upper/                      # copy the *current* upper
rm -rf /mnt/sda2/work && mkdir -p /mnt/sda2/work             # work MUST be emptied
uci set fstab.@global[0].delay_root=10                       # USB enumeration is slow
uci commit fstab
cp /etc/config/fstab /mnt/sda2/upper/etc/config/fstab
sync && reboot -f
```

`fstab` mount entry:

```
config mount
    option target '/overlay'
    option uuid '<YOUR-UUID>'
    option fstype 'ext4'
    option options 'rw,sync'
    option enabled '1'
```

After boot, **remount async** — the `sync` option causes D-state deadlocks under
HA's thousands of small-file writes:

```sh
mount -o remount,async /overlay
```

## 1.6 Network: make the router reachable from the existing LAN

The K3 sits behind an upstream router (`192.168.31.1`) with its own LAN at
`192.168.1.1`. Add a LAN alias so a host on the upstream network can reach it:

```sh
ip addr add 192.168.31.200/24 dev br-lan
ip route add default via 192.168.31.1 dev br-lan
echo nameserver 223.5.5.5 > /etc/resolv.conf
```

DNS and the default route are lost repeatedly across reboots. Guard them with
`scripts/keep_net.sh` and a cron entry `* * * * * /root/keep_net.sh`.

## 1.7 Optional extras (from the Enshan Wi-Fi-driver article)

- Replace `/lib/firmware/brcm/brcmfmac4366c-pcie.bin` (back up as `.bak`).
- LuCI plugins: `luci-app-adblock`, `luci-app-filetransfer`,
  `luci-theme-material_mod` (**do not use the material theme — see phase 8**).
- Screen driver: `k3screenctrl` 6-1 (`arm_cortex-a9`) + `luci-app-k3screenctrl`.
