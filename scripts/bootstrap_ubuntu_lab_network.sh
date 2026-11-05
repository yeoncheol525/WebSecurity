#!/bin/sh
set -eu
# Invoked as root through the user's existing sudo account. Existing NAT netplan stays untouched.
interface=ens37
address=192.168.67.20
if ! command -v arping >/dev/null 2>&1; then
    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y iputils-arping
fi
ip link set "$interface" up
if ! ip -4 address show dev "$interface" | grep -q "$address/24"; then
    arping -D -I "$interface" -c 3 "$address"
fi
config=/etc/netplan/90-minishop-lab.yaml
if [ -e "$config" ] && ! grep -q '# Managed by MiniShop lab setup' "$config"; then
    echo 'Existing unrelated lab network file found; refusing overwrite' >&2
    exit 1
fi
umask 077
cat > "$config" <<'NETPLAN'
# Managed by MiniShop lab setup; preserves existing NAT ens33 configuration.
network:
  version: 2
  ethernets:
    ens37:
      dhcp4: false
      dhcp6: false
      link-local: []
      addresses: [192.168.67.20/24]
      optional: true
NETPLAN
netplan generate
netplan apply
ip -br address
ip route
echo 'Ubuntu Host-only address configured; original NAT configuration preserved.'
