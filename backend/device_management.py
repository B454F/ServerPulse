
import time
import subprocess

from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_user
from database_v2 import get_db

router = APIRouter(prefix="/api")


@router.post("/devices/{device_id}/revoke")
def revoke_device(
    device_id: str,
    user=Depends(get_current_user)
):
    now = int(time.time())

    with get_db() as conn:

        conn.execute("BEGIN IMMEDIATE")

        device = conn.execute("""
            SELECT id, user_id, is_active, revoked_at
            FROM devices
            WHERE id = ? AND user_id = ?
        """, (device_id, user["id"])).fetchone()

        if not device:
            raise HTTPException(
                status_code=404,
                detail="Device not found"
            )

        if not device["is_active"] and device["revoked_at"] is None:
            raise HTTPException(
                status_code=409,
                detail="Device provisioning is not complete"
            )

        conn.execute("""
            UPDATE devices
            SET is_active = 0,
                revoked_at = COALESCE(revoked_at, ?)
            WHERE id = ? AND user_id = ?
        """, (now, device_id, user["id"]))

    try:
        result = subprocess.run(
            [
                "sudo",
                "-n",
                "/usr/local/sbin/serverpulse-revoke"
            ],
            input=device_id + "\n",
            text=True,
            capture_output=True,
            timeout=90
        )

        if result.returncode != 0:
            raise RuntimeError("MQTT revocation failed")

    except (OSError, RuntimeError, subprocess.TimeoutExpired):
        raise HTTPException(
            status_code=503,
            detail="Device disabled. MQTT revocation incomplete. Retry required."
        )

    return {
        "success": True,
        "device_id": device_id,
        "status": "revoked"
    }
