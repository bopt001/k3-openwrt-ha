#!/bin/sh
# Network keepalive for the K3 behind an upstream router.
# Edit these three values to match the local network, then install with:
#   cp keep_net.sh /root/keep_net.sh && chmod +x /root/keep_net.sh
#   echo '* * * * * /root/keep_net.sh' >> /etc/crontabs/root
#
# The addresses below are illustrative examples (RFC1918 private ranges),
# not real credentials or a real network layout.
UPSTREAM_GW=192.168.31.1
LAN_ALIAS=192.168.31.200/24
DNS=223.5.5.5
IFACE=br-lan

ip route | grep -q "default via $UPSTREAM_GW" || {
  ip addr add "$LAN_ALIAS" dev "$IFACE" 2>/dev/null
  ip route add default via "$UPSTREAM_GW" dev "$IFACE" 2>/dev/null
}
[ "$(head -1 /etc/resolv.conf)" = "nameserver $DNS" ] || echo "nameserver $DNS" > /etc/resolv.conf
