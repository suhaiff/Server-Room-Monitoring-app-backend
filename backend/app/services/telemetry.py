"""Phase 1 ingestion pipeline: raw preservation, validation, normalization and clean storage."""
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from app import models
from app.schemas import TelemetryIn

UNITS = {"temperature": "C", "humidity": "%", "water_leak": "bool", "door_open": "bool", "smoke": "bool"}
RANGES = {"temperature": (-20, 100), "humidity": (0, 100), "water_leak": (0, 1), "door_open": (0, 1), "smoke": (0, 1)}


def ingest(db: Session, payload: TelemetryIn) -> dict:
    device = db.get(models.DimDevice, payload.device_id)
    if not device:
        raise ValueError("Unknown device")
    room = db.get(models.DimRoom, device.room_id)
    site = db.get(models.DimSite, room.site_id)
    timestamp = payload.timestamp or datetime.now(timezone.utc)
    event = models.CoreEvent(organization_id=site.organization_id, site_id=site.id, room_id=room.id, device_id=device.id, event_type="telemetry", event_timestamp=timestamp, has_raw_data=True, has_telemetry=True, description="Sensor telemetry received")
    db.add(event); db.flush()
    raw = models.RawDataHeader(core_event_id=event.id, device_id=device.id)
    clean = models.TelemetryHeader(core_event_id=event.id, device_id=device.id)
    db.add_all([raw, clean]); db.flush()
    anomalies = []
    for kind, raw_value in payload.readings.items():
        sensor = db.scalar(select(models.DimSensor).where(models.DimSensor.device_id == device.id, models.DimSensor.sensor_type == kind))
        db.add(models.RawDataDetail(raw_header_id=raw.id, sensor_id=sensor.id if sensor else None, raw_value=str(raw_value), raw_unit=UNITS.get(kind, ""), raw_payload={"value": raw_value}))
        numeric = float(raw_value) if not isinstance(raw_value, str) or raw_value.replace(".", "", 1).isdigit() else None
        low, high = RANGES.get(kind, (-1e30, 1e30))
        quality = "valid" if numeric is not None and low <= numeric <= high else "invalid"
        if quality == "invalid": anomalies.append(f"Invalid {kind}: {raw_value}")
        db.add(models.TelemetryDetail(telemetry_header_id=clean.id, sensor_id=sensor.id if sensor else None, measurement_type=kind, value_numeric=numeric, value_text=None if numeric is not None else str(raw_value), unit=UNITS.get(kind, ""), quality_status=quality, measurement_timestamp=timestamp))
    device.status = "online"; device.last_seen_at = timestamp
    if payload.health:
        db.add(models.DeviceHealth(device_id=device.id, status="online", rssi=payload.health.get("rssi"), uptime_seconds=payload.health.get("uptime_seconds"), recorded_at=timestamp))
    db.commit()
    return {"core_event_id": event.id, "telemetry_header_id": clean.id, "accepted": len(payload.readings), "validation_errors": anomalies}
