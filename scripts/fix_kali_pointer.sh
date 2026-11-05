#!/bin/sh
set -eu
if [ "$(id -u)" -ne 0 ]; then
    echo 'Run with sudo inside Kali.' >&2
    exit 1
fi
config=/etc/X11/xorg.conf.d/99-minishop-software-cursor.conf
if [ -e "$config" ] && ! grep -q 'Managed by MiniShop' "$config"; then
    echo 'An unrelated configuration exists; refusing overwrite.' >&2
    exit 1
fi
install -d -m 755 /etc/X11/xorg.conf.d
cat > "$config" <<'XORG'
# Managed by MiniShop: use an Xorg software cursor for VMware display compatibility.
Section "Device"
    Identifier "MiniShop VMware display"
    Driver "modesetting"
    Option "SWcursor" "true"
EndSection
XORG
chmod 644 "$config"
echo 'Installed persistent software-cursor configuration.'
echo 'Restart LightDM at the login screen, or apply on the next login/reboot.'
