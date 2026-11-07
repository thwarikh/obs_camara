"""
Network service for detecting host IP addresses, network interfaces, and connection types (Wi-Fi vs USB Tethering).
"""
import socket
import psutil
from typing import List, Dict, Any

class NetworkService:
    @staticmethod
    def get_local_ip() -> str:
        """
        Attempts to find the best outbound IP address of the Windows PC.
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Does not need to be reachable, purely for route lookup
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        finally:
            s.close()
        return ip

    @staticmethod
    def get_all_interfaces() -> List[Dict[str, Any]]:
        """
        Enumerates all active network interfaces with classification (Wi-Fi, USB Tethering, Ethernet).
        """
        interfaces = []
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()

        for name, addr_list in addrs.items():
            stat = stats.get(name)
            is_up = stat.isup if stat else False
            if not is_up:
                continue

            for addr in addr_list:
                if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                    # Classify interface type
                    lower_name = name.lower()
                    if "wi-fi" in lower_name or "wlan" in lower_name or "wireless" in lower_name:
                        iface_type = "wifi"
                    elif "rndis" in lower_name or "apple mobile" in lower_name or "usb" in lower_name or "tether" in lower_name:
                        iface_type = "usb_tethering"
                    elif "ethernet" in lower_name or "eth" in lower_name:
                        # Some USB tethering adapters name themselves Ethernet 2 / 3
                        # We note it as ethernet / potential usb
                        iface_type = "ethernet"
                    else:
                        iface_type = "unknown"

                    interfaces.append({
                        "name": name,
                        "ip": addr.address,
                        "netmask": addr.netmask,
                        "type": iface_type,
                        "speed_mbps": stat.speed if stat else 0
                    })

        # Ensure we always return at least the best local IP
        if not interfaces:
            interfaces.append({
                "name": "Default",
                "ip": NetworkService.get_local_ip(),
                "netmask": "255.255.255.0",
                "type": "wifi",
                "speed_mbps": 100
            })

        return interfaces

    @staticmethod
    def detect_connection_type(client_ip: str) -> str:
        """
        Classifies whether an incoming client connection is coming over USB tethering subnet or Wi-Fi.
        """
        if not client_ip:
            return "wifi"
            
        # Common USB Tethering subnet ranges:
        # Android USB tethering commonly allocates 192.168.42.x or 192.168.43.x or 192.168.44.x
        # iPhone USB tethering commonly allocates 172.20.10.x
        if client_ip.startswith("192.168.42.") or client_ip.startswith("192.168.44."):
            return "usb_tethering"
        if client_ip.startswith("172.20.10."):
            return "usb_tethering"
            
        # Check against active interface subnets
        for iface in NetworkService.get_all_interfaces():
            if iface["type"] == "usb_tethering":
                iface_ip_prefix = ".".join(iface["ip"].split(".")[:3])
                if client_ip.startswith(iface_ip_prefix):
                    return "usb_tethering"

        return "wifi"

