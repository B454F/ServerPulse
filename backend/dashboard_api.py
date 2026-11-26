
import json
import time

from fastapi import APIRouter, Depends
from fastapi import HTTPException, Query

from auth import get_current_user
from database_v2 import get_db


router = APIRouter(
    prefix="/api",
    tags=["Dashboard"]
)


def check_device(conn, device_id, user_id):

    device = conn.execute("""
        SELECT *
        FROM devices
        WHERE id = ?
        AND user_id = ?
    """, (device_id, user_id)).fetchone()

    if not device:
        raise HTTPException(
            status_code=404,
            detail="Device not found"
        )

    return device


@router.get("/dashboard/summary")
def dashboard_summary(
    user=Depends(get_current_user)
):

    now = int(time.time())

    with get_db() as conn:

        rows = conn.execute("""
            SELECT
                d.id AS device_id,
                d.device_name,
                d.os,
                d.last_seen,
                d.is_active,
                d.revoked_at,
                t.payload
            FROM devices d
            LEFT JOIN telemetry t
                ON t.id = (
                    SELECT t2.id
                    FROM telemetry t2
                    WHERE t2.device_id = d.id
                    ORDER BY t2.id DESC
                    LIMIT 1
                )
            WHERE d.user_id = ?
            ORDER BY d.created_at DESC
        """, (user["id"],)).fetchall()

    devices = []
    online_devices = []

    for row in rows:

        device = dict(row)
        payload = device.pop("payload")

        online = bool(
            device["is_active"]
            and device["last_seen"]
            and now - device["last_seen"] < 20
        )

        device["online"] = online

        device["status"] = (
            "revoked" if device["revoked_at"] is not None
            else "pending_provisioning"
            if not device["is_active"]
            else "online" if online else "offline"
        )

        metrics = json.loads(payload) if payload else None

        device["metrics"] = metrics

        devices.append(device)

        if online and metrics:
            online_devices.append(metrics)

    def average(key):

        if not online_devices:
            return 0

        return round(
            sum(
                item[key]["usage"]
                for item in online_devices
            ) / len(online_devices),
            1
        )

    return {
        "user": user["display_name"],

        "total_devices": len(devices),

        "online_devices": sum(
            1 for d in devices
            if d["status"] == "online"
        ),

        "offline_devices": sum(
            1 for d in devices
            if d["status"] == "offline"
        ),

        "pending_devices": sum(
            1 for d in devices
            if d["status"] == "pending_provisioning"
        ),

        "revoked_devices": sum(
            1 for d in devices
            if d["status"] == "revoked"
        ),

        "average_cpu": average("cpu"),
        "average_ram": average("ram"),
        "average_disk": average("disk"),

        "devices": devices
    }


@router.get("/devices/{device_id}/latest")
def latest_telemetry(
    device_id: str,
    user=Depends(get_current_user)
):

    with get_db() as conn:

        device = check_device(
            conn,
            device_id,
            user["id"]
        )

        row = conn.execute("""
            SELECT payload
            FROM telemetry
            WHERE device_id = ?
            ORDER BY id DESC
            LIMIT 1
        """, (device_id,)).fetchone()

    return {
        "device_id": device_id,
        "device_name": device["device_name"],
        "metrics": (
            json.loads(row["payload"])
            if row else None
        )
    }


@router.get("/devices/{device_id}/history")
def telemetry_history(
    device_id: str,
    hours: int = Query(default=1, ge=1, le=24),
    limit: int = Query(default=300, ge=1, le=1000),
    user=Depends(get_current_user)
):

    since = int(time.time()) - hours * 3600

    with get_db() as conn:

        check_device(
            conn,
            device_id,
            user["id"]
        )

        rows = conn.execute("""
            SELECT timestamp, payload
            FROM telemetry
            WHERE device_id = ?
            AND received_at >= ?
            ORDER BY received_at DESC, id DESC
            LIMIT ?
        """, (
            device_id,
            since,
            limit
        )).fetchall()

    history = []

    for row in reversed(rows):

        data = json.loads(row["payload"])

        history.append({
            "timestamp": row["timestamp"],
            "cpu": data["cpu"]["usage"],
            "ram": data["ram"]["usage"],
            "disk": data["disk"]["usage"]
        })

    return {
        "device_id": device_id,
        "hours": hours,
        "count": len(history),
        "history": history
    }
