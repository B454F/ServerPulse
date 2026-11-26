import ipaddress
import os
import json
import time
import logging
import re
import math

from pathlib import Path

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

from database_v2 import get_db


load_dotenv(
    Path(__file__).resolve().parent / ".env"
)

logger = logging.getLogger("serverpulse.mqtt")


def validate_telemetry(data):

    if not isinstance(data, dict):
        raise ValueError("Invalid payload")

    for key in ("cpu", "ram", "disk"):

        value = data[key]["usage"]

        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or not 0 <= value <= 100
        ):
            raise ValueError(f"Invalid {key} usage")
        ips = data.get("ip_addresses", {})

    if not isinstance(ips, dict):
        raise ValueError("Invalid IP data")

    for key in ("local_ip", "public_ip"):

        value = ips.get(key)

        if value is not None:

            if not isinstance(value, str):
                raise ValueError("Invalid IP address")

            ips[key] = str(
                ipaddress.ip_address(value)
            )

    data["ip_addresses"] = ips
    timestamp = data["timestamp"]

    if (
        isinstance(timestamp, bool)
        or not isinstance(timestamp, int)
        or abs(time.time() - timestamp) > 600
    ):
        raise ValueError("Invalid timestamp")


def on_connect(
    client, userdata, flags,
    reason_code, properties
):
    if reason_code == 0:

        print(
            "[MQTT V2] Connected successfully",
            flush=True
        )

        client.subscribe(
            "serverpulse/devices/+/telemetry",
            qos=1
        )

    else:
        print(
            f"[MQTT V2] Connection rejected: {reason_code}",
            flush=True
        )


def on_message(client, userdata, message):

    try:

        if len(message.payload) > 16384:
            raise ValueError("Payload too large")

        topic = message.topic.split("/")

        if (
            len(topic) != 4
            or topic[0] != "serverpulse"
            or topic[1] != "devices"
            or topic[3] != "telemetry"
        ):
            return

        device_id = topic[2]

        if not re.fullmatch(r"[a-f0-9]{32}", device_id):
            return

        data = json.loads(
            message.payload.decode("utf-8")
        )

        validate_telemetry(data)

        if data["device_id"] != device_id:
            raise ValueError("Device ID mismatch")

        now = int(time.time())

        with get_db() as conn:

            device = conn.execute("""
                SELECT devices.id, devices.device_name
                FROM devices
                JOIN users ON users.id = devices.user_id
                WHERE devices.id = ?
                AND devices.is_active = 1
                AND users.is_active = 1
            """, (device_id,)).fetchone()

            if not device:
                return

            data["device_name"] = device["device_name"]

            conn.execute("""
                INSERT INTO telemetry (
                    device_id,
                    timestamp,
                    received_at,
                    payload
                )
                VALUES (?, ?, ?, ?)
            """, (
                device_id,
                data["timestamp"],
                now,
                json.dumps(data, allow_nan=False)
            ))

            conn.execute("""
                UPDATE devices
                SET last_seen = ?
                WHERE id = ?
            """, (now, device_id))

        print(
            f"[V2 DATABASE] Saved: {device_id} | "
            f"CPU: {data['cpu']['usage']}% | "
            f"RAM: {data['ram']['usage']}%",
            flush=True
        )

    except Exception:
        logger.exception("Telemetry rejected")


def start_mqtt():

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="serverpulse-backend-v2",
        protocol=mqtt.MQTTv5
    )

    client.username_pw_set(
        os.getenv("MQTT_USERNAME"),
        os.getenv("MQTT_PASSWORD")
    )

    client.on_connect = on_connect
    client.on_message = on_message

    client.reconnect_delay_set(1, 30)

    client.connect_async(
        os.getenv("MQTT_HOST", "127.0.0.1"),
        int(os.getenv("MQTT_PORT", "1883")),
        60
    )

    client.loop_start()

    return client
