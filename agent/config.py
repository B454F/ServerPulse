
import json
import os
import sys
from pathlib import Path

import keyring


APP_NAME = "ServerPulse"

APP_DIR = Path(
    os.getenv("LOCALAPPDATA", str(Path.home()))
) / APP_NAME

APP_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = APP_DIR / "config.json"

RESOURCE_DIR = Path(
    getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)
)

CERTIFICATE = Path(os.getenv("SERVERPULSE_MQTT_CA", str(RESOURCE_DIR / "serverpulse.crt")))

DEFAULT_API_URL = os.getenv("SERVERPULSE_API_URL", "https://localhost")


def load_config():
    if not CONFIG_FILE.exists():
        return None

    with open(CONFIG_FILE, encoding="utf-8") as file:
        config = json.load(file)

    return config


def save_config(config, password):
    username = config["mqtt"]["username"]

    keyring.set_password(
        APP_NAME,
        username,
        password
    )

    with open(CONFIG_FILE, "w", encoding="utf-8") as file:
        json.dump(config, file, indent=4)


def get_password(username):
    return keyring.get_password(
        APP_NAME,
        username
    )


def clear_config():
    config = load_config()

    if config:
        username = config["mqtt"]["username"]

        try:
            keyring.delete_password(
                APP_NAME,
                username
            )
        except keyring.errors.PasswordDeleteError:
            pass

    CONFIG_FILE.unlink(missing_ok=True)
