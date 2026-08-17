"""VTAB Sentinel AI runtime with model diagnostics and bounded operational logs."""
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from prometheus_fastapi_instrumentator import Instrumentator

from models import anomaly, explain, forecast, learn_baseline, risk_score

MODEL_VERSION = "transparent-baseline-2.0"
MODEL_NAMES = ["baseline", "anomaly", "forecast", "risk", "explanation"]
STARTED_AT = datetime.now(timezone.utc)
LOGS: deque[dict] = deque(maxlen=250)
MODEL_STATE = {
    name: {"name": name, "status": "ready", "last_run_at": None, "latency_ms": None, "runs": 0, "errors": 0}
    for name in MODEL_NAMES
}


def log(level: str, component: str, message: str, *, run_id: str | None = None, event: str = "runtime", details: dict | None = None) -> None:
    """Store structured, UI-friendly events in a bounded in-memory journal."""
    LOGS.appendleft({
        "id": str(uuid4()), "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level, "component": component, "event": event,
        "run_id": run_id, "message": message, "details": details or {},
    })


def mark_model(name: str, started: float, run_id: str, output: dict | str | None = None, error: Exception | None = None) -> None:
    state = MODEL_STATE[name]
    state["last_run_at"] = datetime.now(timezone.utc).isoformat()
    state["latency_ms"] = round((perf_counter() - started) * 1000, 2)
    state["runs"] += 1
    if error:
        state["status"] = "error"; state["errors"] += 1
        log("error", name, f"Model execution failed: {error}", run_id=run_id, event="model_failed")
    else:
        state["status"] = "healthy"
        log("info", name, f"Model completed in {state['latency_ms']} ms", run_id=run_id, event="model_completed", details={"latency_ms": state["latency_ms"], "output": output})


class AnalyzeRequest(BaseModel):
    history: dict[str, list[float]]
    readings: dict[str, float]
    horizon: int = Field(5, ge=1, le=48)


@asynccontextmanager
async def lifespan(_: FastAPI):
    log("info", "runtime", f"AI service {MODEL_VERSION} started with {len(MODEL_NAMES)} models")
    yield


app = FastAPI(title="VTAB Sentinel AI Service", version="2.0.0", lifespan=lifespan)
Instrumentator().instrument(app).expose(app)


@app.get("/health")
def health():
    failed = [name for name, state in MODEL_STATE.items() if state["status"] == "error"]
    return {"status": "degraded" if failed else "healthy", "version": MODEL_VERSION, "models": MODEL_NAMES, "failed_models": failed}


@app.get("/status")
def status():
    failed = sum(1 for state in MODEL_STATE.values() if state["status"] == "error")
    return {
        "service": "vtab-ai", "version": MODEL_VERSION,
        "status": "degraded" if failed else "healthy",
        "started_at": STARTED_AT.isoformat(),
        "models": list(MODEL_STATE.values()),
        "logs": list(LOGS)[:150],
        "active_pipeline": None,
    }


@app.post("/self-test")
def self_test():
    sample = AnalyzeRequest(history={"temperature": [23.8, 24.1, 24.0, 24.3]}, readings={"temperature": 24.3, "humidity": 48, "water_leak": 0, "door_open": 0, "smoke": 0})
    result = analyze(sample)
    log("info", "self-test", "All AI model checks completed successfully")
    return {"status": "passed", "result": result}


@app.post("/analyze")
def analyze(body: AnalyzeRequest):
    run_id = str(uuid4())
    pipeline_started = perf_counter()
    series = body.history.get("temperature", [])
    if len(series) < 3:
        log("warning", "validation", "Analysis rejected: fewer than three temperature history points", run_id=run_id, event="request_rejected")
        raise HTTPException(422, "At least three temperature history points are required")
    log("info", "pipeline", "New sensor event accepted for AI analysis", run_id=run_id, event="pipeline_started", details={"readings": body.readings, "history_points": len(series), "horizon": body.horizon})
    results = {}
    try:
        started = perf_counter(); baseline = learn_baseline(series[:-1] or series); results["baseline"] = baseline.__dict__; mark_model("baseline", started, run_id, results["baseline"])
        started = perf_counter(); anomalous = anomaly(series, baseline); results["anomaly"] = anomalous; mark_model("anomaly", started, run_id, anomalous)
        started = perf_counter(); prediction = forecast(series, body.horizon); results["prediction"] = prediction; mark_model("forecast", started, run_id, prediction)
        started = perf_counter(); risk = risk_score(body.readings, anomalous["anomaly_score"]); results["risk"] = risk; mark_model("risk", started, run_id, risk)
        started = perf_counter(); explanation = explain(body.readings, anomalous, risk); results["explanation"] = explanation; mark_model("explanation", started, run_id, explanation)
    except Exception as exc:
        log("error", "pipeline", str(exc), run_id=run_id, event="pipeline_failed"); raise HTTPException(500, "AI pipeline execution failed") from exc
    precautions = recommended_actions(body.readings, results["risk"])
    total_ms = round((perf_counter() - pipeline_started) * 1000, 2)
    log("info" if risk["level"] == "low" else "warning", "decision", f"Analysis completed with {risk['level']} risk ({risk['score']}/100)", run_id=run_id, event="pipeline_completed", details={"risk": risk, "precautions": precautions, "total_latency_ms": total_ms})
    return {"run_id": run_id, "model_version": MODEL_VERSION, "total_latency_ms": total_ms, "precautions": precautions, **results}


def recommended_actions(readings: dict, risk: dict) -> list[dict]:
    """Transparent response policy; replace commands with approved BMS integrations in production."""
    actions: list[dict] = []
    if readings.get("smoke"):
        actions += [{"priority": "emergency", "action": "Initiate fire-response verification and evacuation protocol", "automation": "notification_dispatched"}, {"priority": "emergency", "action": "Isolate affected electrical zone after operator confirmation", "automation": "operator_approval_required"}]
    if readings.get("water_leak"):
        actions += [{"priority": "critical", "action": "Inspect leak zone and protect floor-level power equipment", "automation": "incident_created"}]
    if readings.get("temperature", 0) > 30:
        actions += [{"priority": "high", "action": "Verify cooling units and increase approved cooling capacity", "automation": "work_order_recommended"}]
    if readings.get("humidity", 0) > 70:
        actions += [{"priority": "high", "action": "Inspect dehumidification and condensation risk", "automation": "inspection_recommended"}]
    if readings.get("door_open"):
        actions += [{"priority": "medium", "action": "Verify authorized access and close the server-room door", "automation": "security_check_recommended"}]
    if not actions:
        actions.append({"priority": "normal", "action": "Continue monitoring; no intervention required", "automation": "monitoring"})
    return actions
