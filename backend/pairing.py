
import time
import uuid
import secrets
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from database_v2 import get_db
from auth import get_current_user
from security import hash_token

from provisioning import (
    provision_device,
    ProvisioningError
)

router = APIRouter(
    prefix="/api",
    tags=["Device Pairing"]
)

PAIRING_DURATION = 600
MAX_DEVICES_PER_USER = 5


def check_device_quota(conn, user_id):
    count = conn.execute(
        '''
        SELECT COUNT(*)
        FROM devices
        WHERE user_id = ?
        AND revoked_at IS NULL
        ''',
        (user_id,)
    ).fetchone()[0]

    if count >= MAX_DEVICES_PER_USER:
        raise HTTPException(
            status_code=409,
            detail="Device limit reached. Maximum 5 devices per account."
        )


MQTT_HOST = os.getenv(
    "PUBLIC_MQTT_HOST",
    "localhost"
)

MQTT_PORT = int(
    os.getenv("PUBLIC_MQTT_PORT", "8883")
)


class PairDeviceRequest(BaseModel):
    code: str = Field(min_length=10, max_length=64)
    device_name: str = Field(min_length=1, max_length=100)
    os: str = Field(min_length=1, max_length=100)


def generate_pairing_code():
    return "SP-" + "-".join(
        secrets.token_hex(2).upper()
        for _ in range(4)
    )


@router.post("/pairing/create", status_code=201)
def create_pairing_code(
    user=Depends(get_current_user)
):
    code = generate_pairing_code()
    now = int(time.time())

    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        check_device_quota(conn, user["id"])

        conn.execute("""
            DELETE FROM pairing_codes
            WHERE user_id = ?
            AND used_at IS NULL
        """, (user["id"],))

        conn.execute("""
            INSERT INTO pairing_codes (
                code_hash,
                user_id,
                created_at,
                expires_at
            )
            VALUES (?, ?, ?, ?)
        """, (
            hash_token(code),
            user["id"],
            now,
            now + PAIRING_DURATION
        ))

    return {
        "pairing_code": code,
        "expires_in": PAIRING_DURATION
    }


@router.post("/pairing/connect", status_code=201)
def pair_device(data: PairDeviceRequest):

    code_hash = hash_token(
        data.code.strip().upper()
    )

    now = int(time.time())
    device_id = uuid.uuid4().hex
    mqtt_username = f"device_{device_id}"

    device_name = data.device_name.strip()

    if not device_name:
        raise HTTPException(
            status_code=400,
            detail="Invalid device name"
        )

    with get_db() as conn:

        conn.execute("BEGIN IMMEDIATE")

        pairing = conn.execute("""
            SELECT pairing_codes.*
            FROM pairing_codes
            JOIN users
                ON users.id = pairing_codes.user_id
            WHERE code_hash = ?
            AND expires_at > ?
            AND used_at IS NULL
            AND users.is_active = 1
        """, (
            code_hash,
            now
        )).fetchone()

        if not pairing:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired pairing code"
            )

        check_device_quota(conn, pairing["user_id"])

        conn.execute("""
            INSERT INTO devices (
                id,
                user_id,
                device_name,
                os,
                mqtt_username,
                created_at,
                is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, 0)
        """, (
            device_id,
            pairing["user_id"],
            device_name,
            data.os.strip(),
            mqtt_username,
            now
        ))

        conn.execute("""
            UPDATE pairing_codes
            SET used_at = ?
            WHERE code_hash = ?
        """, (now, code_hash))

    try:
        credentials = provision_device(device_id)

    except ProvisioningError:
        raise HTTPException(
            status_code=503,
            detail=(
                "Device provisioning failed. "
                "Create a new pairing code."
            )
        )

    with get_db() as conn:
        conn.execute("""
            UPDATE devices
            SET is_active = 1
            WHERE id = ?
        """, (device_id,))

    return {
        "message": "Device paired successfully",
        "device_id": device_id,
        "device_name": device_name,
        "status": "active",
        "mqtt": {
            "host": MQTT_HOST,
            "port": MQTT_PORT,
            "tls": True,
            "username": credentials["mqtt_username"],
            "password": credentials["mqtt_password"],
            "topic": credentials["mqtt_topic"]
        }
    }


@router.get("/devices")
def list_devices(
    user=Depends(get_current_user)
):

    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                id AS device_id,
                device_name,
                os,
                created_at,
                last_seen,
                is_active,
                revoked_at
            FROM devices
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user["id"],)).fetchall()

    devices = []

    for row in rows:
        device = dict(row)

        device["online"] = bool(
            device["is_active"]
            and device["last_seen"]
            and time.time() - device["last_seen"] < 20
        )

        device["status"] = (
            "revoked" if device["revoked_at"] is not None
            else "pending_provisioning"
            if not device["is_active"]
            else "online" if device["online"]
            else "offline"
        )

        devices.append(device)

    return devices
