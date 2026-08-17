from datetime import datetime, timezone
import csv
from io import StringIO
from time import perf_counter
import socket
import httpx
import redis
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, desc, func, select, update
from sqlalchemy.orm import Session
from app import models
from app.core.database import get_db
from app.core.security import current_user, require_roles
from app.schemas import IncidentUpdate, IntegrationRequest
from app.services.integrations import dispatch
from app.core.config import settings

router = APIRouter(tags=["Operations"])

@router.get("/alerts")
def alerts(db: Session = Depends(get_db), user=Depends(current_user)):
    rows = db.execute(
        select(models.AlertHeader, models.AlertDetail, models.CoreEvent, models.DimDevice, models.DimRoom)
        .join(models.AlertDetail, models.AlertDetail.alert_id == models.AlertHeader.id)
        .join(models.CoreEvent, models.CoreEvent.id == models.AlertHeader.core_event_id)
        .outerjoin(models.DimDevice, models.DimDevice.id == models.CoreEvent.device_id)
        .outerjoin(models.DimRoom, models.DimRoom.id == models.CoreEvent.room_id)
        .order_by(desc(models.AlertHeader.created_at)).limit(500)
    ).all()
    return [{
        "id": alert.id, "core_event_id": alert.core_event_id,
        "ai_analysis_id": alert.ai_analysis_id, "alert_type": alert.alert_type,
        "severity": alert.severity, "status": alert.status,
        "message": detail.message, "recommendation": detail.recommendation,
        "trigger_value": detail.trigger_value, "threshold_value": detail.threshold_value,
        "device_name": device.name if device else ("Platform Services" if event.source_system == "software-test-lab" else "Unknown device"),
        "room_name": room.name if room else "Unknown room",
        "event_timestamp": event.event_timestamp, "created_at": alert.created_at,
    } for alert, detail, event, device, room in rows]

@router.get("/incidents")
def incidents(db: Session = Depends(get_db), user=Depends(current_user)):
    rows=db.execute(select(models.IncidentHeader,models.AlertHeader,models.AlertDetail,models.CoreEvent,models.DimDevice,models.DimRoom).join(models.AlertHeader,models.AlertHeader.id==models.IncidentHeader.alert_id).join(models.AlertDetail,models.AlertDetail.alert_id==models.AlertHeader.id).join(models.CoreEvent,models.CoreEvent.id==models.IncidentHeader.core_event_id).outerjoin(models.DimDevice,models.DimDevice.id==models.CoreEvent.device_id).outerjoin(models.DimRoom,models.DimRoom.id==models.CoreEvent.room_id).order_by(desc(models.IncidentHeader.created_at)).limit(500)).all()
    result=[]
    for incident,alert,detail,event,device,room in rows:
        history=db.scalars(select(models.IncidentDetail).where(models.IncidentDetail.incident_id==incident.id).order_by(models.IncidentDetail.action_timestamp)).all()
        result.append({"id":incident.id,"core_event_id":incident.core_event_id,"alert_id":incident.alert_id,"status":incident.status,"severity":incident.severity,"priority":incident.priority,"message":detail.message,"recommendation":detail.recommendation,"alert_type":alert.alert_type,"device_name":device.name if device else ("Platform Services" if event.source_system == "software-test-lab" else "Unknown device"),"room_name":room.name if room else "Unknown room","event_timestamp":event.event_timestamp,"created_at":incident.created_at,"acknowledged_at":incident.acknowledged_at,"resolved_at":incident.resolved_at,"history":[{"id":item.id,"action_type":item.action_type,"description":item.action_description,"note":item.note,"timestamp":item.action_timestamp,"resolution_note":item.resolution_note} for item in history]})
    return result

@router.patch("/incidents/{incident_id}")
def update_incident(incident_id: str, body: IncidentUpdate, db: Session = Depends(get_db), user=Depends(require_roles("admin", "facility_manager", "engineer"))):
    incident = db.get(models.IncidentHeader, incident_id)
    if not incident: raise HTTPException(404, "Incident not found")
    timestamp = datetime.now(timezone.utc)
    if body.action == "acknowledge": incident.status = "acknowledged"; incident.acknowledged_at = timestamp
    elif body.action == "assign": incident.assigned_user_id = body.assigned_user_id; incident.status = "assigned"
    elif body.action in {"resolve", "close"}:
        incident.status = "resolved" if body.action == "resolve" else "closed"; incident.resolved_at = timestamp
        alert = db.get(models.AlertHeader, incident.alert_id)
        if alert: alert.status = "resolved" if body.action == "resolve" else "closed"
    db.add(models.IncidentDetail(incident_id=incident.id, action_type=body.action, action_description=body.note or body.action, note=body.note, action_timestamp=timestamp, resolution_note=body.note if body.action == "resolve" else ""))
    db.commit(); return incident

@router.post("/integrations/dispatch")
async def integrate(body: IntegrationRequest, db: Session = Depends(get_db), user=Depends(require_roles("admin", "facility_manager"))):
    incident = db.get(models.IncidentHeader, body.incident_id)
    if not incident: raise HTTPException(404, "Incident not found")
    return await dispatch(body.provider, {"incident_id": incident.id, "status": incident.status, "severity": incident.severity}, body.target_url)

@router.get("/reports/summary")
def summary(db: Session = Depends(get_db), user=Depends(current_user)):
    def count(model): return db.scalar(select(func.count()).select_from(model)) or 0
    open_alerts=db.scalar(select(func.count()).select_from(models.AlertHeader).where(models.AlertHeader.status == "open")) or 0
    open_incidents=db.scalar(select(func.count()).select_from(models.IncidentHeader).where(models.IncidentHeader.status.in_(["open", "assigned", "acknowledged"]))) or 0
    system_state="alert" if open_alerts else "pending" if open_incidents else "healthy"
    return {"devices": count(models.DimDevice), "telemetry_points": count(models.TelemetryDetail), "open_alerts":open_alerts,"open_incidents":open_incidents,"environment_state":"attention" if open_alerts else "normalized","workflow_state":"pending" if open_incidents else "clear","system_state":system_state}

@router.post("/admin/test-data/reset")
def reset_test_data(db: Session=Depends(get_db), user=Depends(require_roles("admin"))):
    """Delete test/event history while preserving users, devices and configuration."""
    ordered=[models.NotificationDetail,models.NotificationHeader,models.IntegrationDetail,models.IntegrationHeader,models.IncidentDetail,models.IncidentHeader,models.AlertDetail,models.AlertHeader,models.AIPrediction,models.AIAnomaly,models.AIRiskScore,models.AIExplanation,models.AIAnalysisHeader,models.TelemetryDetail,models.TelemetryHeader,models.RawDataDetail,models.RawDataHeader,models.DeviceHealth,models.AuditDetail,models.AuditHeader,models.CoreEvent]
    deleted={}
    for model in ordered:
        result=db.execute(delete(model));deleted[model.__tablename__]=result.rowcount or 0
    db.execute(update(models.DimDevice).values(last_seen_at=None,status="offline"))
    db.commit()
    return {"status":"reset","deleted_rows":sum(deleted.values()),"tables":deleted,"preserved":["organizations","sites","rooms","devices","sensors","users","roles","thresholds","configuration"]}

@router.get("/admin/logs/export")
def export_system_log(db: Session=Depends(get_db), user=Depends(require_roles("admin"))):
    """Download one chronological CSV containing the platform's auditable records."""
    rows=[]
    for event in db.scalars(select(models.CoreEvent).order_by(models.CoreEvent.event_timestamp)).all():
        rows.append([event.event_timestamp,"core_event",event.source_system,event.severity,event.status,
                     event.id,event.id,event.event_type,event.description,""])
    for alert, detail in db.execute(select(models.AlertHeader,models.AlertDetail).join(models.AlertDetail,models.AlertDetail.alert_id==models.AlertHeader.id)).all():
        rows.append([alert.created_at,"alert",alert.created_by,alert.severity,alert.status,alert.id,
                     alert.core_event_id,alert.alert_type,detail.message,detail.recommendation])
    for incident in db.scalars(select(models.IncidentHeader)).all():
        rows.append([incident.created_at,"incident","alert-engine",incident.severity,incident.status,
                     incident.id,incident.core_event_id,"operator_ticket","Incident workflow ticket",f"alert_id={incident.alert_id}"])
    for action in db.scalars(select(models.IncidentDetail)).all():
        rows.append([action.action_timestamp,"incident_action","operator-workflow","info",action.action_type,
                     action.id,"",action.action_type,action.action_description,action.note or action.resolution_note])
    for analysis in db.scalars(select(models.AIAnalysisHeader)).all():
        rows.append([analysis.analysis_timestamp,"ai_analysis","ai-service","info",analysis.analysis_status,
                     analysis.id,analysis.core_event_id,analysis.model_name,
                     f"AI analysis using {analysis.model_version}",f"telemetry_header_id={analysis.telemetry_header_id or ''}"])
    rows.sort(key=lambda row: row[0] or datetime.min.replace(tzinfo=timezone.utc))
    output=StringIO(); writer=csv.writer(output)
    writer.writerow(["timestamp","category","source","severity","status","record_id","core_event_id","name","message","details"])
    for row in rows: writer.writerow([value.isoformat() if isinstance(value,datetime) else value for value in row])
    filename=f"vtab-sentinel-system-log-{datetime.now(timezone.utc).date().isoformat()}.csv"
    return StreamingResponse(iter([output.getvalue()]),media_type="text/csv",
                             headers={"Content-Disposition":f'attachment; filename="{filename}"'})

@router.get("/audit")
def audit(db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    return db.scalars(select(models.AuditHeader).order_by(desc(models.AuditHeader.created_at)).limit(500)).all()

@router.get("/system/diagnostics")
def diagnostics(db: Session=Depends(get_db), user=Depends(current_user)):
    """Live engineering evidence for platform dependencies and event linkage."""
    components=[]
    def check(name,fn):
        started=perf_counter()
        try:
            detail=fn();components.append({"name":name,"status":"healthy","latency_ms":round((perf_counter()-started)*1000,2),"detail":detail})
        except Exception as exc:
            components.append({"name":name,"status":"error","latency_ms":round((perf_counter()-started)*1000,2),"detail":str(exc)[:300]})
    check("PostgreSQL / TimescaleDB",lambda: {"core_events":db.scalar(select(func.count()).select_from(models.CoreEvent)) or 0,"telemetry_points":db.scalar(select(func.count()).select_from(models.TelemetryDetail)) or 0})
    check("Redis",lambda: "PING acknowledged" if redis.from_url(settings.redis_url,socket_timeout=2).ping() else "No response")
    def mqtt_check():
        with socket.create_connection((settings.mqtt_host,settings.mqtt_port),timeout=2): return f"TCP reachable at {settings.mqtt_host}:{settings.mqtt_port}"
    check("Mosquitto MQTT",mqtt_check)
    def ai_check():
        response=httpx.get(f"{settings.ai_service_url}/status",timeout=3);response.raise_for_status();data=response.json()
        active=db.scalars(select(models.AlertHeader).where(models.AlertHeader.status=="open",models.AlertHeader.alert_type.like("software_ai_%"))).all()
        if active:
            names=[item.alert_type.removeprefix("software_ai_") for item in active]
            raise RuntimeError(f"Controlled model failure active: {', '.join(names)}")
        return {"runtime":data.get("status"),"version":data.get("version"),"models":len(data.get("models",[]))}
    def minio_check():
        response=httpx.get(f"{settings.s3_endpoint}/minio/health/live",timeout=3);response.raise_for_status();return "Health endpoint acknowledged"
    check("AI service",ai_check)
    check("MinIO object storage",minio_check)
    analyses=db.scalar(select(func.count()).select_from(models.AIAnalysisHeader)) or 0
    linked_alerts=db.scalar(select(func.count()).select_from(models.AlertHeader).where(models.AlertHeader.ai_analysis_id.is_not(None))) or 0
    unlinked_events=db.scalar(select(func.count()).select_from(models.CoreEvent).where(models.CoreEvent.has_telemetry.is_(True),models.CoreEvent.has_ai.is_(False))) or 0
    return {"status":"healthy" if all(c["status"]=="healthy" for c in components) else "degraded","checked_at":datetime.now(timezone.utc),"components":components,"evidence":{"ai_analyses":analyses,"ai_linked_alerts":linked_alerts,"telemetry_events_without_ai":unlinked_events}}
