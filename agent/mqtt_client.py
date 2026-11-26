
import json
import ssl
import threading

import paho.mqtt.client as mqtt

from config import CERTIFICATE, get_password
from telemetry import collect_metrics


class MQTTService:

    def __init__(self, config, status_callback, data_callback):

        self.config = config
        self.status_callback = status_callback
        self.data_callback = data_callback

        self.stop_event = threading.Event()

        self.connected = False
        self.access_denied = False
        self.thread = None

        self.ack_condition = threading.Condition()
        self.ack_results = {}

        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"sp-{config['device_id']}",
            protocol=mqtt.MQTTv5
        )

        mqtt_config = config["mqtt"]

        password = get_password(
            mqtt_config["username"]
        )

        if not password:
            raise RuntimeError(
                "Saved MQTT credentials not found"
            )

        self.client.username_pw_set(
            mqtt_config["username"],
            password
        )

        self.client.tls_set(
            ca_certs=str(CERTIFICATE) if CERTIFICATE.is_file() else None,
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLS_CLIENT
        )

        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_connect_fail = self.on_connect_fail
        self.client.on_publish = self.on_publish

        self.client.reconnect_delay_set(
            min_delay=1,
            max_delay=30
        )

    def on_connect(
        self, client, userdata, flags,
        reason_code, properties
    ):

        if reason_code == 0:

            self.connected = True
            self.access_denied = False
            self.status_callback("Connected")

        else:

            self.connected = False

            if reason_code.value in (134, 135):

                self.access_denied = True
                self.status_callback("Access denied")
                client.disconnect()

            else:

                self.status_callback(
                    f"Connection rejected: {reason_code}"
                )

    def on_connect_fail(self, client, userdata):

        if not self.access_denied:

            self.status_callback(
                "Connection failed. Retrying..."
            )

    def on_disconnect(
        self, client, userdata, flags,
        reason_code, properties
    ):

        self.connected = False

        if self.stop_event.is_set():

            self.status_callback("Disconnected")

        elif self.access_denied:

            self.status_callback("Access denied")

        else:

            self.status_callback("Reconnecting...")

    def on_publish(
        self, client, userdata, mid,
        reason_code, properties
    ):

        with self.ack_condition:

            if len(self.ack_results) >= 100:
                self.ack_results.clear()

            self.ack_results[mid] = (
                not reason_code.is_failure
            )

            self.ack_condition.notify_all()

    def start(self):

        mqtt_config = self.config["mqtt"]

        self.status_callback("Connecting...")

        self.client.connect_async(
            mqtt_config["host"],
            mqtt_config["port"],
            60
        )

        self.client.loop_start()

        self.thread = threading.Thread(
            target=self.telemetry_loop,
            daemon=True
        )

        self.thread.start()

    def telemetry_loop(self):

        interval = self.config.get("interval", 5)

        while not self.stop_event.is_set():

            if self.connected and not self.access_denied:

                try:

                    data = collect_metrics(
                        self.config["device_id"]
                    )

                    with self.ack_condition:
                        self.ack_results.clear()

                    result = self.client.publish(
                        self.config["mqtt"]["topic"],
                        json.dumps(data),
                        qos=1
                    )

                    if result.rc != mqtt.MQTT_ERR_SUCCESS:
                        raise RuntimeError("Publish failed")

                    result.wait_for_publish(timeout=5)

                    with self.ack_condition:

                        self.ack_condition.wait_for(
                            lambda: result.mid in self.ack_results
                            or self.stop_event.is_set(),
                            timeout=5
                        )

                        accepted = self.ack_results.pop(
                            result.mid, None
                        )

                    if accepted is True:

                        self.data_callback(data)

                    elif accepted is False:

                        self.status_callback(
                            "Telemetry rejected"
                        )

                    elif self.connected:

                        self.status_callback(
                            "Telemetry timeout"
                        )

                except Exception:

                    if self.connected:
                        self.status_callback("Telemetry error")

            self.stop_event.wait(interval)

    def stop(self):

        self.stop_event.set()

        with self.ack_condition:
            self.ack_condition.notify_all()

        self.client.disconnect()
        self.client.loop_stop()

        if self.thread:
            self.thread.join(timeout=2)
