"""Select only a non-default private interface; never guess a public/NAT bind."""
import ipaddress
import json
import platform
import subprocess


def interface_data():
    if platform.system() != "Linux":
        return [], []
    addresses = json.loads(subprocess.check_output(["ip", "-j", "address"], text=True))
    routes = json.loads(subprocess.check_output(["ip", "-j", "route", "show", "default"], text=True))
    return addresses, routes


def private_candidates(addresses, routes):
    default_devices = {route.get("dev") for route in routes}
    candidates = []
    for interface in addresses:
        name = interface.get("ifname", "")
        if name in default_devices or name.startswith(("lo", "docker", "br-", "veth", "virbr", "tun", "tap")):
            continue
        if interface.get("operstate") != "UP":
            continue
        for item in interface.get("addr_info", []):
            if item.get("family") != "inet" or item.get("scope") != "global":
                continue
            address = ipaddress.ip_address(item["local"])
            if address.is_private and not (address.is_loopback or address.is_link_local):
                candidates.append(str(address))
    return sorted(set(candidates))


def auto_bind():
    addresses, routes = interface_data()
    choices = private_candidates(addresses, routes)
    if len(choices) > 1:
        raise ValueError("Multiple private lab addresses found; select one with --bind IP: " + ", ".join(choices))
    return choices[0] if choices else "127.0.0.1"


def validate_bind(value):
    address = ipaddress.ip_address(value)
    if address.version != 4 or address.is_unspecified or address.is_multicast or not address.is_private or address.is_link_local:
        raise ValueError("Use loopback or an assigned private IPv4 address")
    if not address.is_loopback and platform.system() == "Linux":
        interfaces, _routes = interface_data()
        assigned = {item.get("local") for interface in interfaces for item in interface.get("addr_info", [])
                    if item.get("family") == "inet"}
        if str(address) not in assigned:
            raise ValueError("The requested address is not assigned to this Ubuntu VM: " + str(address))
    return str(address)
