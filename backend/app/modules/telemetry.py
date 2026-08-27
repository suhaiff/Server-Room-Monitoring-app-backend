from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, desc, select
from sqlalchemy.orm import Session
from app import models
from app.core.database import get_db
from app.core.security import current_user
from app.schemas import TelemetryIn
from app.services.alerts import evaluate
from app.services.telemetry import ingest
from app.services.ai_pipeline import analyze_and_persist

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])

@router.post("/ingest")
def ingest_http(payload: TelemetryIn, db: Session = Depends(get_db)):
    try: result = ingest(db, payload)
    except ValueError as exc: raise HTTPException(404, str(exc)) from exc
    alert_ids = evaluate(db, result["core_event_id"], payload.readings)
    ai_result = analyze_and_persist(db, result["core_event_id"], result["telemetry_header_id"], payload.readings)
    return {**result, "source": "http-device-ingestion", "alert_ids": alert_ids, "alerts_created": len(alert_ids), "ai": ai_result}

@router.get("/latest")
def latest(device_id: str | None = None, limit: int = Query(100, le=1000), db: Session = Depends(get_db), user=Depends(current_user)):
    """Return clean telemetry plus source/raw ADC evidence from the same event."""
    query = (
        select(models.TelemetryDetail, models.RawDataDetail, models.TelemetryHeader)
        .join(models.TelemetryHeader, models.TelemetryHeader.id == models.TelemetryDetail.telemetry_header_id)
        .outerjoin(models.RawDataHeader, models.RawDataHeader.core_event_id == models.TelemetryHeader.core_event_id)
        .outerjoin(models.RawDataDetail, and_(
            models.RawDataDetail.raw_header_id == models.RawDataHeader.id,
            models.RawDataDetail.sensor_id == models.TelemetryDetail.sensor_id))
        .order_by(desc(models.TelemetryDetail.measurement_timestamp)).limit(limit)
    )
    if device_id:
        query = query.where(models.TelemetryHeader.device_id == device_id)
    result=[]
    for clean, raw, header in db.execute(query).all():
        payload=(raw.raw_payload or {}) if raw else {}
        source=payload.get("source") or {}
        result.append({
            "id":clean.id,"telemetry_header_id":clean.telemetry_header_id,"device_id":header.device_id,"sensor_id":clean.sensor_id,
            "measurement_type":clean.measurement_type,"value_numeric":clean.value_numeric,"value_text":clean.value_text,
            "unit":clean.unit,"quality_status":clean.quality_status,"measurement_timestamp":clean.measurement_timestamp,
            "source_mode":source.get("mode","unknown"),"source_provider":source.get("provider","unknown"),
            "raw_adc":source.get("raw"),"pin":source.get("pin"),"sensor_error":source.get("sensor_error",False),
        })
    return result
