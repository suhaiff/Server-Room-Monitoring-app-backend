"""Shared automatic AI execution for HTTP simulation and MQTT hardware events."""
from sqlalchemy import desc, select
from sqlalchemy.orm import Session
import httpx

from app import models
from app.core.config import settings


def analyze_and_persist(db: Session, event_id: str, telemetry_header_id: str, readings: dict) -> dict:
    """Run the AI service and persist a fully linked, auditable result.

    Alert ingestion remains successful if the AI service is temporarily down;
    callers receive an explicit unavailable status instead of losing telemetry.
    """
    event = db.get(models.CoreEvent, event_id)
    history = list(db.scalars(
        select(models.TelemetryDetail.value_numeric)
        .where(models.TelemetryDetail.measurement_type == "temperature",
               models.TelemetryDetail.value_numeric.is_not(None))
        .order_by(desc(models.TelemetryDetail.measurement_timestamp)).limit(12)
    ).all())[::-1]
    current = float(readings.get("temperature", history[-1] if history else 24.0))
    while len(history) < 4:
        history.insert(0, current)
    try:
        response = httpx.post(f"{settings.ai_service_url}/analyze", json={
            "history": {"temperature": history}, "readings": readings, "horizon": 5,
        }, timeout=20)
        response.raise_for_status(); result = response.json()
    except httpx.HTTPError as exc:
        return {"status": "unavailable", "message": str(exc)}

    header = models.AIAnalysisHeader(core_event_id=event.id, telemetry_header_id=telemetry_header_id,
        model_name="baseline-anomaly-forecast-risk", model_version=result["model_version"])
    db.add(header); db.flush()
    db.add_all([
        models.AIPrediction(ai_analysis_id=header.id, result=result["prediction"]),
        models.AIAnomaly(ai_analysis_id=header.id, result=result["anomaly"]),
        models.AIRiskScore(ai_analysis_id=header.id, result=result["risk"]),
        models.AIExplanation(ai_analysis_id=header.id, result={"text": result["explanation"]}),
    ])
    for alert in db.scalars(select(models.AlertHeader).where(models.AlertHeader.core_event_id == event.id)).all():
        alert.ai_analysis_id = header.id
    event.has_ai = True; db.commit()
    return {"status": "complete", "ai_analysis_id": header.id, "core_event_id": event.id, **result}
