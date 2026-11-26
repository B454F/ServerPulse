
import socket
import platform
from urllib.parse import urlparse

import requests

from config import save_config


def pair_device(api_url, code):
    api_url = api_url.strip().rstrip("/")
    parsed = urlparse(api_url)

    if parsed.scheme != "https":
        if not (
            parsed.scheme == "http"
            and parsed.hostname in ("127.0.0.1", "localhost")
        ):
            raise ValueError(
                "Remote server connections require HTTPS."
            )

    payload = {
        "code": code.strip().upper(),
        "device_name": socket.gethostname(),
        "os": f"{platform.system()} {platform.release()}"
    }

    response = requests.post(
        f"{api_url}/api/pairing/connect",
        json=payload,
        timeout=100,
        allow_redirects=False
    )

    if response.status_code != 201:
        try:
            detail = response.json().get(
                "detail", "Pairing failed"
            )
        except ValueError:
            detail = "Server connection failed"

        raise RuntimeError(str(detail))

    data = response.json()

    if data.get("status") != "active":
        raise RuntimeError("Device provisioning failed")

    mqtt_data = data["mqtt"].copy()
    password = mqtt_data.pop("password")

    config = {
        "api_url": api_url,
        "device_id": data["device_id"],
        "device_name": payload["device_name"],
        "mqtt": mqtt_data,
        "interval": 5
    }

    save_config(config, password)

    return config
