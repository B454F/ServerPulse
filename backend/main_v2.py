from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

from device_management import router as device_management_router
from security_middleware import SecurityMiddleware
from dashboard_api import router as dashboard_router
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends

from database_v2 import init_db
from auth import router as auth_router
from auth import get_current_user
from pairing import router as pairing_router
from pairing import list_devices
from mqtt_handler_v2 import start_mqtt


@asynccontextmanager
async def lifespan(app: FastAPI):

    init_db()

    mqtt_client = start_mqtt()

    print(
        "[SERVERPULSE] Cloud v2 started.",
        flush=True
    )

    try:
        yield

    finally:
        mqtt_client.disconnect()
        mqtt_client.loop_stop()


app = FastAPI(
    title="ServerPulse Cloud API",
    version="2.0.0",
    lifespan=lifespan
)
app.add_middleware(SecurityMiddleware)
app.include_router(auth_router)
app.include_router(pairing_router)
app.include_router(dashboard_router)
app.include_router(device_management_router)

@app.get("/")
def root():
    return {
        "application": "ServerPulse Cloud",
        "version": "2.0.0",
        "status": "online"
    }


@app.get("/api/overview")
def overview(user=Depends(get_current_user)):

    devices = list_devices(user)

    online = sum(
        1 for device in devices
        if device["status"] == "online"
    )

    offline = sum(
        1 for device in devices
        if device["status"] == "offline"
    )

    pending = sum(
        1 for device in devices
        if device["status"] == "pending_provisioning"
    )

    return {
        "user": user["display_name"],
        "total_devices": len(devices),
        "online_devices": online,
        "offline_devices": offline,
        "pending_devices": pending,
        "revoked_devices": sum(
            1 for device in devices
            if device["status"] == "revoked"
        )
    }
