"""Independent ESP32 lab gateway. Publishes only to MQTT; never calls VTAB APIs."""
import json
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

import paho.mqtt.client as mqtt
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
DEVICE_ID = os.getenv("DEVICE_ID", "00000000-0000-0000-0000-000000000101")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="vtab-independent-test-lab")
state = {"connected": False, "connecting": False, "last_publish_at": None, "published": 0, "last_payload": None}
receipts: dict[str, dict] = {}
lock = Lock()


class Readings(BaseModel):
    temperature: float = Field(ge=-20, le=100)
    humidity: float = Field(ge=0, le=100)
    water_leak: int = Field(ge=0, le=1)
    door_open: int = Field(ge=0, le=1)
    smoke: int = Field(ge=0, le=1)


class PublishRequest(BaseModel):
    readings: Readings
    board: str = "ESP32 DevKit V1"
    firmware: str = "sentinel-esp32-lab-3.0"
    rssi: int = Field(-42, ge=-100, le=0)

    @field_validator("board")
    @classmethod
    def esp_only(cls, value: str):
        if "ESP32" not in value:
            raise ValueError("The production lab supports ESP32 board profiles only")
        return value


def on_connect(_client, _userdata, _flags, reason_code, _properties):
    state["connected"] = not getattr(reason_code, "is_failure", bool(reason_code))
    state["connecting"] = False
    if state["connected"]:
        _client.subscribe(f"devices/{DEVICE_ID}/receipts/+", qos=1)


def on_disconnect(_client, _userdata, _flags, _reason_code, _properties):
    state["connected"] = False
    state["connecting"] = False


def on_message(_client, _userdata, message):
    try:
        data = json.loads(message.payload.decode())
        correlation_id = data["correlation_id"]
        with lock:
            receipts[correlation_id] = data
            if len(receipts) > 200:
                receipts.pop(next(iter(receipts)))
    except (ValueError, KeyError):
        return


def connect(raise_error: bool = True):
    if state["connected"] or state["connecting"]:
        return
    try:
        state["connecting"] = True
        client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
        client.loop_start()
        deadline = time.time() + 3
        while not state["connected"] and time.time() < deadline:
            time.sleep(0.05)
    except OSError as exc:
        state["connecting"] = False
        if raise_error:
            raise HTTPException(503, f"MQTT broker unavailable: {exc}") from exc


@asynccontextmanager
async def lifespan(_app: FastAPI):
    connect(raise_error=False)
    yield
    client.loop_stop()
    client.disconnect()


app = FastAPI(title="VTAB Independent ESP32 Test Lab", version="3.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5174"], allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message


@app.get("/health")
def health():
    state["connected"] = bool(client.is_connected())
    if not state["connected"]:
        connect(raise_error=False)
    return {"status": "healthy" if state["connected"] else "waiting-for-mqtt", "mqtt_connected": state["connected"], "device_id": DEVICE_ID}


@app.get("/status")
def status():
    state["connected"] = bool(client.is_connected())
    if not state["connected"]:
        connect(raise_error=False)
    return {**state, "device_id": DEVICE_ID, "mqtt_host": MQTT_HOST, "mqtt_port": MQTT_PORT}


@app.post("/publish")
def publish(body: PublishRequest):
    connect()
    timestamp = datetime.now(timezone.utc).isoformat()
    correlation_id = str(uuid4())
    payload = {
        "device_id": DEVICE_ID, "timestamp": timestamp, "correlation_id": correlation_id,
        "readings": body.readings.model_dump(),
        "health": {"rssi": body.rssi, "uptime_seconds": int(time.monotonic()), "firmware": body.firmware, "board": body.board, "source": "independent-test-lab"},
    }
    info = client.publish(f"devices/{DEVICE_ID}/telemetry", json.dumps(payload), qos=1)
    info.wait_for_publish(timeout=5)
    if info.rc != mqtt.MQTT_ERR_SUCCESS:
        raise HTTPException(503, "MQTT publish was not acknowledged")
    with lock:
        # A QoS-1 publish acknowledgement is stronger evidence than the client's
        # transient socket flag and also keeps test doubles implementation-neutral.
        state["connected"] = True; state["last_publish_at"] = timestamp; state["published"] += 1; state["last_payload"] = payload
    return {"status": "published", "message_id": info.mid, "correlation_id": correlation_id, "topic": f"devices/{DEVICE_ID}/telemetry", "timestamp": timestamp, "next_stage": "mqtt-worker -> database -> alerts -> AI"}


@app.get("/receipts/{correlation_id}")
def processing_receipt(correlation_id: str):
    receipt = receipts.get(correlation_id)
    if not receipt:
        return {"status": "processing", "correlation_id": correlation_id}
    return receipt
