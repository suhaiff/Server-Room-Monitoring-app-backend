"""Phase 2 AI client: calls the separate service and persists its governed outputs."""
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc, select
from app import models
from app.core.config import settings
from app.core.database import get_db
from app.core.security import current_user

router=APIRouter(prefix="/ai",tags=["AI / ML"])
class AIRequest(BaseModel):
    core_event_id: str
    telemetry_header_id: str | None = None
    history: dict[str,list[float]]
    readings: dict[str,float]
    horizon: int = 5

async def _ai_request(method: str, path: str, json: dict | None = None):
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.request(method, f"{settings.ai_service_url}{path}", json=json)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(503, "AI service unavailable") from exc

@router.get("/status")
async def ai_status(db: Session=Depends(get_db), user=Depends(current_user)):
    """Return live runtime status overlaid with persisted fault-test state.

    The AI container can still answer HTTP while one logical model is under a
    controlled failure test. Reading the open software alerts here makes that
    distinction visible in AI Operations instead of incorrectly showing green.
    """
    data = await _ai_request("GET", "/status")
    active = db.execute(
        select(models.AlertHeader, models.AlertDetail, models.CoreEvent)
        .join(models.AlertDetail, models.AlertDetail.alert_id == models.AlertHeader.id)
        .join(models.CoreEvent, models.CoreEvent.id == models.AlertHeader.core_event_id)
        .where(models.AlertHeader.status == "open",
               models.AlertHeader.alert_type.like("software_ai_%"))
        .order_by(desc(models.AlertHeader.created_at))
    ).all()
    failed = {alert.alert_type.removeprefix("software_ai_"): (alert, detail, event)
              for alert, detail, event in active}
    for model in data.get("models", []):
        if model.get("name") in failed:
            alert, detail, event = failed[model["name"]]
            model.update({"status": "error", "errors": model.get("errors", 0) + 1,
                          "fault_alert_id": alert.id, "fault_since": event.event_timestamp,
                          "fault_message": detail.message})
    if failed:
        data["status"] = "degraded"
        order = ["baseline", "anomaly", "forecast", "risk", "explanation"]
        first_failed = min((order.index(name) for name in failed if name in order), default=len(order))
        blocker = order[first_failed] if first_failed < len(order) else "upstream model"
        blocked = []
        for model in data.get("models", []):
            name = model.get("name")
            if name in order and order.index(name) > first_failed and model.get("status") != "error":
                model.update({"status": "blocked", "blocked_by": blocker,
                              "blocked_reason": f"Held because upstream {blocker} stage failed"})
                blocked.append(name)
        synthetic = [{"id": alert.id, "timestamp": event.event_timestamp,
                      "level": "error", "component": name,
                      "event": "simulated_model_failure", "run_id": None,
                      "message": detail.message,
                      "details": {"alert_id": alert.id, "test_mode": True,
                                  "recommendation": detail.recommendation}}
                     for name, (alert, detail, event) in failed.items()]
        synthetic += [{"id": f"blocked-{blocker}-{name}", "timestamp": list(failed.values())[0][2].event_timestamp,
                       "level": "warning", "component": name, "event": "pipeline_blocked",
                       "run_id": None, "message": f"Stage held because upstream {blocker} model failed",
                       "details": {"blocked_by": blocker, "dependency_mode": "linear"}}
                      for name in blocked]
        data["logs"] = synthetic + data.get("logs", [])
        data["pipeline"] = {"mode": "linear", "failed": list(failed), "blocked": blocked}
    data["active_fault_tests"] = len(failed)
    return data

@router.post("/self-test")
async def ai_self_test(user=Depends(current_user)):
    return await _ai_request("POST", "/self-test")

@router.post("/analyze")
async def analyze(body: AIRequest, db: Session=Depends(get_db), user=Depends(current_user)):
    event=db.get(models.CoreEvent,body.core_event_id)
    if not event: raise HTTPException(404,"Core event not found")
    result = await _ai_request("POST", "/analyze", body.model_dump(exclude={"core_event_id","telemetry_header_id"}))
    header=models.AIAnalysisHeader(core_event_id=event.id,telemetry_header_id=body.telemetry_header_id,model_name="baseline-anomaly-forecast-risk",model_version=result["model_version"])
    db.add(header); db.flush()
    db.add_all([models.AIPrediction(ai_analysis_id=header.id,result=result["prediction"]),models.AIAnomaly(ai_analysis_id=header.id,result=result["anomaly"]),models.AIRiskScore(ai_analysis_id=header.id,result=result["risk"]),models.AIExplanation(ai_analysis_id=header.id,result={"text":result["explanation"]})])
    # Link alerts created from this event to the exact AI analysis. This makes
    # the core event -> telemetry -> AI -> alert lineage directly auditable.
    for alert in db.query(models.AlertHeader).filter(models.AlertHeader.core_event_id == event.id).all():
        alert.ai_analysis_id = header.id
    event.has_ai=True; db.commit()
    return {"ai_analysis_id":header.id,"core_event_id":event.id,**result}

@router.get("/results")
def recent_results(limit: int = 100, db: Session=Depends(get_db), user=Depends(current_user)):
    """Return persisted AI runs with their originating event identifiers."""
    headers = db.scalars(select(models.AIAnalysisHeader).order_by(desc(models.AIAnalysisHeader.analysis_timestamp)).limit(min(limit, 500))).all()
    output=[]
    for header in headers:
        risk=db.scalar(select(models.AIRiskScore).where(models.AIRiskScore.ai_analysis_id==header.id))
        anomaly=db.scalar(select(models.AIAnomaly).where(models.AIAnomaly.ai_analysis_id==header.id))
        explanation=db.scalar(select(models.AIExplanation).where(models.AIExplanation.ai_analysis_id==header.id))
        output.append({"id":header.id,"core_event_id":header.core_event_id,"telemetry_header_id":header.telemetry_header_id,"model_name":header.model_name,"model_version":header.model_version,"status":header.analysis_status,"analysis_timestamp":header.analysis_timestamp,"risk":risk.result if risk else None,"anomaly":anomaly.result if anomaly else None,"explanation":explanation.result.get("text") if explanation else None})
    return output
