
import socket
import platform
import time
import ipaddress
from pathlib import Path

import psutil
import requests


public_ip_cache = None
last_ip_check = float("-inf")


def get_local_ip():

    try:
        with socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM
        ) as sock:

            sock.connect(("1.1.1.1", 443))

            return sock.getsockname()[0]

    except OSError:
        return None


def get_public_ip():

    global public_ip_cache
    global last_ip_check

    now = time.monotonic()

    if now - last_ip_check < 300:
        return public_ip_cache

    last_ip_check = now

    try:

        response = requests.get(
            "https://api.ipify.org?format=json",
            timeout=3
        )

        response.raise_for_status()

        public_ip_cache = str(
            ipaddress.ip_address(response.json()["ip"])
        )

    except Exception:
        public_ip_cache = None

    return public_ip_cache


def collect_metrics(device_id):

    cpu_usage = psutil.cpu_percent(interval=1)

    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(Path.home().anchor)
    network = psutil.net_io_counters()

    return {
        "device_id": device_id,
        "device_name": socket.gethostname(),
        "os": platform.system(),
        "os_version": platform.release(),

        "ip_addresses": {
            "local_ip": get_local_ip(),
            "public_ip": get_public_ip()
        },

        "cpu": {
            "usage": cpu_usage,
            "cores": psutil.cpu_count(logical=True)
        },

        "ram": {
            "total_gb": round(memory.total / 1024**3, 2),
            "used_gb": round(memory.used / 1024**3, 2),
            "usage": memory.percent
        },

        "disk": {
            "total_gb": round(disk.total / 1024**3, 2),
            "used_gb": round(disk.used / 1024**3, 2),
            "usage": disk.percent
        },

        "network": {
            "sent_mb": round(network.bytes_sent / 1024**2, 2),
            "received_mb": round(network.bytes_recv / 1024**2, 2)
        },

        "uptime": int(time.time() - psutil.boot_time()),
        "timestamp": int(time.time())
    }
