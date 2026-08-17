from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session
from app import models
from app.core.database import SessionLocal, get_db
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
    query = select(models.TelemetryDetail).order_by(desc(models.TelemetryDetail.measurement_timestamp)).limit(limit)
    if device_id:
        query = query.join(models.TelemetryHeader).where(models.TelemetryHeader.device_id == device_id)
    return db.scalars(query).all()
