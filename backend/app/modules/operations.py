from datetime import datetime, timedelta, timezone
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
from app.schemas import IncidentUpdate, IntegrationRequest, ThresholdRuleIn
from app.services.integrations import dispatch
from app.services.alerts import adaptive_rule_details
from app.core.config import settings

router = APIRouter(tags=["Operations"])

@router.get("/settings/thresholds")
def get_thresholds(db: Session=Depends(get_db), user=Depends(current_user)):
    rows=db.scalars(select(models.ThresholdRule).where(models.ThresholdRule.organization_id==user.organization_id).order_by(models.ThresholdRule.measurement_type)).all()
    return [{"id":r.id,"measurement_type":r.measurement_type,"operator":r.operator,"threshold":r.threshold,"severity":r.severity,"enabled":r.enabled,**(adaptive_rule_details(db,user.organization_id,r.measurement_type) or {})} for r in rows]

@router.put("/settings/thresholds/{measurement_type}")
def save_threshold(measurement_type: str, body: ThresholdRuleIn, db: Session=Depends(get_db), user=Depends(require_roles("admin","facility_manager","engineer"))):
    allowed={"temperature","humidity","water_leak","door_open","smoke"}
    if measurement_type not in allowed or body.measurement_type != measurement_type:
        raise HTTPException(422,"Measurement type must match a supported sensor")
    rule=db.scalar(select(models.ThresholdRule).where(models.ThresholdRule.organization_id==user.organization_id,models.ThresholdRule.measurement_type==measurement_type))
    if not rule:
        rule=models.ThresholdRule(organization_id=user.organization_id,measurement_type=measurement_type);db.add(rule)
    rule.operator=body.operator;rule.threshold=body.threshold;rule.severity=body.severity;rule.enabled=body.enabled
    config=db.scalar(select(models.SystemConfiguration).where(models.SystemConfiguration.organization_id==user.organization_id,models.SystemConfiguration.key=="threshold_modes"))
    if not config:
        config=models.SystemConfiguration(organization_id=user.organization_id,key="threshold_modes",value={});db.add(config)
    modes=dict(config.value or {})
    modes[measurement_type]=body.mode if measurement_type in {"temperature","humidity"} else "manual"
    config.value=modes
    db.commit();db.refresh(rule)
    return {**{column.name:getattr(rule,column.name) for column in rule.__table__.columns},**(adaptive_rule_details(db,user.organization_id,measurement_type) or {})}
@router.get("/alerts")
def alerts(db: Session = Depends(get_db), user=Depends(current_user)):
    rows = db.execute(
        select(models.AlertHeader, models.AlertDetail, models.CoreEvent, models.DimDevice,
               models.DimRoom, models.IncidentHeader)
        .join(models.AlertDetail, models.AlertDetail.alert_id == models.AlertHeader.id)
        .join(models.CoreEvent, models.CoreEvent.id == models.AlertHeader.core_event_id)
        .outerjoin(models.DimDevice, models.DimDevice.id == models.CoreEvent.device_id)
        .outerjoin(models.DimRoom, models.DimRoom.id == models.CoreEvent.room_id)
        .outerjoin(models.IncidentHeader, models.IncidentHeader.alert_id == models.AlertHeader.id)
        .order_by(desc(models.AlertHeader.created_at)).limit(500)
    ).all()
    result=[]
    for alert, detail, event, device, room, incident in rows:
        history=[]
        if incident:
            actions=db.scalars(select(models.IncidentDetail).where(
                models.IncidentDetail.incident_id==incident.id
            ).order_by(models.IncidentDetail.action_timestamp)).all()
            history=[{"id":item.id,"action_type":item.action_type,"description":item.action_description,
                      "note":item.note,"timestamp":item.action_timestamp,
                      "resolution_note":item.resolution_note} for item in actions]
        result.append({
            "id":alert.id,"core_event_id":alert.core_event_id,"ai_analysis_id":alert.ai_analysis_id,
            "alert_type":alert.alert_type,"severity":alert.severity,"status":alert.status,
            "message":detail.message,"recommendation":detail.recommendation,
            "trigger_value":detail.trigger_value,"threshold_value":detail.threshold_value,
            "device_name":device.name if device else ("Platform Services" if event.source_system=="software-test-lab" else "Unknown device"),
            "room_name":room.name if room else "Unknown room","event_timestamp":event.event_timestamp,
            "created_at":alert.created_at,"incident_id":incident.id if incident else None,
            "incident_status":incident.status if incident else None,"resolved_at":incident.resolved_at if incident else None,
            "history":history,
        })
    return result

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
    ordered=[models.AgentMessage,models.AgentConversation,models.AgentAction,models.SensorIntelligence,models.NotificationDetail,models.NotificationHeader,models.IntegrationDetail,models.IntegrationHeader,models.IncidentDetail,models.IncidentHeader,models.AlertDetail,models.AlertHeader,models.AIPrediction,models.AIAnomaly,models.AIRiskScore,models.AIExplanation,models.AIAnalysisHeader,models.TelemetryDetail,models.TelemetryHeader,models.RawDataDetail,models.RawDataHeader,models.DeviceHealth,models.AuditDetail,models.AuditHeader,models.CoreEvent]
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
    check("FastAPI backend",lambda:"Protected API request and database session are operational")
    check("Authentication service",lambda:f"Authenticated user {user.id} verified")
    check("Notification delivery",lambda:{"queued":db.scalar(select(func.count()).select_from(models.NotificationHeader).where(models.NotificationHeader.status=="queued")) or 0})
    def http_health(url,label):
        response=httpx.get(url,timeout=2);response.raise_for_status();return f"{label} health endpoint acknowledged"
    check("React dashboard",lambda:http_health("http://frontend/","Frontend"))
    check("Prometheus metrics",lambda:http_health("http://prometheus:9090/-/healthy","Prometheus"))
    check("Grafana monitoring",lambda:http_health("http://grafana:3000/api/health","Grafana"))
    check("Simulator transport",lambda:http_health("http://simulator-api:8010/health","Simulator"))

    # A controlled test must be visible even though the real dependency remains
    # online. Overlay every active software-test alert onto its matching card.
    fault_names={
        "postgres":"PostgreSQL / TimescaleDB","redis":"Redis","mqtt":"Mosquitto MQTT","minio":"MinIO object storage",
        "backend":"FastAPI backend","auth":"Authentication service","notifications":"Notification delivery",
        "frontend":"React dashboard","prometheus":"Prometheus metrics","grafana":"Grafana monitoring","simulator":"Simulator transport",
        "ai_baseline":"AI service","ai_anomaly":"AI service","ai_forecast":"AI service","ai_risk":"AI service","ai_explanation":"AI service",
    }
    active_faults=db.execute(select(models.AlertHeader,models.AlertDetail).join(
        models.AlertDetail,models.AlertDetail.alert_id==models.AlertHeader.id).where(
        models.AlertHeader.status=="open",models.AlertHeader.alert_type.like("software_%"))).all()
    for alert,detail in active_faults:
        key=alert.alert_type.removeprefix("software_");name=fault_names.get(key)
        if not name:continue
        component=next((item for item in components if item["name"]==name),None)
        if component:
            component.update({"status":"error","latency_ms":0,"detail":f"CONTROLLED TEST ACTIVE · {detail.message}"})
    analyses=db.scalar(select(func.count()).select_from(models.AIAnalysisHeader)) or 0
    linked_alerts=db.scalar(select(func.count()).select_from(models.AlertHeader).where(models.AlertHeader.ai_analysis_id.is_not(None))) or 0
    now=datetime.now(timezone.utc); grace_cutoff=now-timedelta(seconds=15); live_window=now-timedelta(minutes=5)
    missing_query=(select(func.count()).select_from(models.CoreEvent)
        .outerjoin(models.AIAnalysisHeader,models.AIAnalysisHeader.core_event_id==models.CoreEvent.id)
        .where(models.CoreEvent.has_telemetry.is_(True),models.AIAnalysisHeader.id.is_(None)))
    processing_backlog=db.scalar(missing_query.where(models.CoreEvent.event_timestamp>=live_window,models.CoreEvent.event_timestamp<=grace_cutoff)) or 0
    historical_unlinked=db.scalar(missing_query.where(models.CoreEvent.event_timestamp<live_window)) or 0
    return {"status":"healthy" if all(c["status"]=="healthy" for c in components) else "degraded","checked_at":now,"components":components,
            "evidence":{"ai_analyses":analyses,"ai_linked_alerts":linked_alerts,"ai_processing_backlog":processing_backlog,
                        "historical_unlinked_telemetry":historical_unlinked,"processing_grace_seconds":15}}




