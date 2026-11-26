
import json
import subprocess
import re


class ProvisioningError(Exception):
    pass


def provision_device(device_id: str):

    if not re.fullmatch(r"[a-f0-9]{32}", device_id):
        raise ProvisioningError("Invalid device ID")

    try:
        result = subprocess.run(
            [
                "/usr/bin/sudo",
                "-n",
                "/usr/local/sbin/serverpulse-provision"
            ],
            input=device_id + "\n",
            capture_output=True,
            text=True,
            check=True,
            timeout=90
        )

        credentials = json.loads(result.stdout)

        required = {
            "mqtt_username",
            "mqtt_password",
            "mqtt_topic"
        }

        if not required.issubset(credentials):
            raise ProvisioningError(
                "Incomplete MQTT credentials"
            )

        return credentials

    except (
        subprocess.SubprocessError,
        json.JSONDecodeError
    ) as error:
        raise ProvisioningError(
            "MQTT provisioning failed"
        ) from error
