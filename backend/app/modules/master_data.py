from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app import models, schemas
from app.core.database import get_db
from app.core.security import current_user, hash_password, require_roles

router = APIRouter(tags=["Master Data"])
MAP = {"organizations": (models.DimOrganization, schemas.OrganizationCreate), "sites": (models.DimSite, schemas.SiteCreate), "rooms": (models.DimRoom, schemas.RoomCreate), "devices": (models.DimDevice, schemas.DeviceCreate), "sensors": (models.DimSensor, schemas.SensorCreate)}

@router.get("/master/{resource}")
def list_resource(resource: str, db: Session = Depends(get_db), user=Depends(current_user)):
    if resource not in MAP: raise HTTPException(404, "Resource not found")
    model = MAP[resource][0]
    values = db.scalars(select(model).order_by(model.created_at.desc()).limit(500)).all()
    return values

@router.get("/devices")
def list_devices(db: Session = Depends(get_db), user=Depends(current_user)):
    """Stable protected device endpoint used by API acceptance tests and clients."""
    return db.scalars(select(models.DimDevice).order_by(models.DimDevice.created_at.desc()).limit(500)).all()

@router.post("/master/{resource}")
def create_resource(resource: str, body: dict, db: Session = Depends(get_db), user=Depends(require_roles("admin", "facility_manager"))):
    if resource not in MAP: raise HTTPException(404, "Resource not found")
    model, schema = MAP[resource]
    item = model(**schema.model_validate(body).model_dump()); db.add(item); db.commit(); db.refresh(item)
    return item

@router.post("/users")
def create_user(body: schemas.UserCreate, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    item = models.DimUser(**body.model_dump(exclude={"password"}), password_hash=hash_password(body.password))
    db.add(item); db.commit(); db.refresh(item); return item

@router.get("/users")
def users(db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    return db.scalars(select(models.DimUser)).all()

SENSOR_UNITS={"temperature":"C","humidity":"%","water_leak":"bool","door_open":"bool","smoke":"bool"}

@router.post("/devices/register")
def register_device(body: schemas.DeviceRegistration, db: Session=Depends(get_db), user=Depends(require_roles("admin","facility_manager"))):
    unknown=sorted(set(body.sensor_types)-set(SENSOR_UNITS))
    if unknown: raise HTTPException(422,f"Unsupported sensors: {', '.join(unknown)}")
    if body.room_id:
        room=db.execute(select(models.DimRoom).join(models.DimSite).where(models.DimRoom.id==body.room_id,models.DimSite.organization_id==user.organization_id)).scalar_one_or_none()
    else:
        room=db.execute(select(models.DimRoom).join(models.DimSite).where(models.DimSite.organization_id==user.organization_id).order_by(models.DimRoom.created_at)).scalars().first()
    if not room: raise HTTPException(404,"No room is available for this organization")
    device=models.DimDevice(room_id=room.id,name=body.name,hardware_type=body.hardware_type,
                            firmware_version=body.firmware_version,status="offline",last_seen_at=None)
    db.add(device);db.flush()
    for sensor_type in dict.fromkeys(body.sensor_types):
        db.add(models.DimSensor(device_id=device.id,sensor_type=sensor_type,unit=SENSOR_UNITS[sensor_type]))
    db.commit();db.refresh(device)
    return {"id":device.id,"name":device.name,"hardware_type":device.hardware_type,"firmware_version":device.firmware_version,
            "status":"offline","last_seen_at":None,"room_id":device.room_id,"sensor_types":list(dict.fromkeys(body.sensor_types)),"effective_mode":"simulated"}

@router.post("/devices/{device_id}/components")
def add_device_components(device_id: str, body: schemas.ComponentRegistration, db: Session=Depends(get_db), user=Depends(require_roles("admin","facility_manager"))):
    if body.sensor_type not in SENSOR_UNITS: raise HTTPException(422,"Unsupported sensor type")
    device=db.execute(select(models.DimDevice).join(models.DimRoom).join(models.DimSite).where(
        models.DimDevice.id==device_id,models.DimSite.organization_id==user.organization_id)).scalar_one_or_none()
    if not device: raise HTTPException(404,"Device not found")
    existing=db.scalars(select(models.DimSensor).where(models.DimSensor.device_id==device.id,models.DimSensor.sensor_type==body.sensor_type)).all()
    created=[]
    for offset in range(body.quantity):
        sensor=models.DimSensor(device_id=device.id,sensor_type=body.sensor_type,unit=SENSOR_UNITS[body.sensor_type])
        db.add(sensor);db.flush();created.append({"id":sensor.id,"sensor_type":sensor.sensor_type,
            "label":f"{sensor.sensor_type.replace('_',' ').title()} sensor {len(existing)+offset+1}"})
    db.commit()
    return {"device_id":device.id,"created":created,"effective_mode":"simulated",
            "message":"New components default to simulation until their sensor IDs appear in a physical packet"}
@router.get("/simulator/device-registry")
def simulator_device_registry(db: Session=Depends(get_db)):
    """Read-only local registry used by the isolated Test Lab."""
    now=datetime.now(timezone.utc);result=[]
    for device in db.scalars(select(models.DimDevice).order_by(models.DimDevice.created_at)).all():
        sensors=db.scalars(select(models.DimSensor).where(models.DimSensor.device_id==device.id).order_by(models.DimSensor.sensor_type)).all()
        online=False
        if device.last_seen_at:
            stamp=device.last_seen_at if device.last_seen_at.tzinfo else device.last_seen_at.replace(tzinfo=timezone.utc)
            online=(now-stamp).total_seconds()<20
        counts={};component_rows=[]
        for sensor in sensors:
            counts[sensor.sensor_type]=counts.get(sensor.sensor_type,0)+1
            component_rows.append({"id":sensor.id,"sensor_type":sensor.sensor_type,
                "label":f"{sensor.sensor_type.replace('_',' ').title()} sensor {counts[sensor.sensor_type]}"})
        result.append({"id":device.id,"name":device.name,"hardware_type":device.hardware_type,
            "firmware_version":device.firmware_version,"status":"online" if online else "offline","hardware_online":online,
            "effective_mode":"hardware" if online else "simulated","last_seen_at":device.last_seen_at,
            "sensor_types":[sensor.sensor_type for sensor in sensors],"sensors":component_rows})
    return result

@router.get("/organizations/{org_id}/export")
def export_organization_data(org_id: str, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    org = db.get(models.DimOrganization, org_id)
    if not org:
        raise HTTPException(404, "Organization not found")
    
    sites = db.scalars(select(models.DimSite).where(models.DimSite.organization_id == org_id)).all()
    rooms = db.scalars(select(models.DimRoom).join(models.DimSite).where(models.DimSite.organization_id == org_id)).all()
    devices = db.scalars(select(models.DimDevice).join(models.DimRoom).join(models.DimSite).where(models.DimSite.organization_id == org_id)).all()
    users = db.scalars(select(models.DimUser).where(models.DimUser.organization_id == org_id)).all()
    
    return {
        "organization": {"id": org.id, "name": org.name, "subscription_plan": org.subscription_plan},
        "sites": [{"id": s.id, "name": s.name, "location": s.location} for s in sites],
        "rooms": [{"id": r.id, "name": r.name, "floor": r.floor, "site_id": r.site_id} for r in rooms],
        "devices": [{"id": d.id, "name": d.name, "hardware_type": d.hardware_type, "room_id": d.room_id} for d in devices],
        "users": [{"id": u.id, "email": u.email, "role": u.role_name} for u in users]
    }

from sqlalchemy import delete

@router.delete("/organizations/{org_id}")
def delete_organization(org_id: str, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    org = db.get(models.DimOrganization, org_id)
    if not org:
        raise HTTPException(404, "Organization not found")
        
    sites_sq = select(models.DimSite.id).where(models.DimSite.organization_id == org_id).subquery()
    rooms_sq = select(models.DimRoom.id).where(models.DimRoom.site_id.in_(sites_sq)).subquery()
    devices_sq = select(models.DimDevice.id).where(models.DimDevice.room_id.in_(rooms_sq)).subquery()
    sensors_sq = select(models.DimSensor.id).where(models.DimSensor.device_id.in_(devices_sq)).subquery()
    events_sq = select(models.CoreEvent.id).where(models.CoreEvent.organization_id == org_id).subquery()
    incidents_sq = select(models.IncidentHeader.id).where(models.IncidentHeader.core_event_id.in_(events_sq)).subquery()
    alerts_sq = select(models.AlertHeader.id).where(models.AlertHeader.core_event_id.in_(events_sq)).subquery()
    ai_headers_sq = select(models.AIAnalysisHeader.id).where(models.AIAnalysisHeader.core_event_id.in_(events_sq)).subquery()
    telemetry_headers_sq = select(models.TelemetryHeader.id).where(models.TelemetryHeader.core_event_id.in_(events_sq)).subquery()
    raw_headers_sq = select(models.RawDataHeader.id).where(models.RawDataHeader.core_event_id.in_(events_sq)).subquery()
    convs_sq = select(models.AgentConversation.id).where(models.AgentConversation.organization_id == org_id).subquery()

    db.execute(delete(models.AuditDetail).where(models.AuditDetail.audit_id.in_(select(models.AuditHeader.id).where(models.AuditHeader.core_event_id.in_(events_sq)))))
    db.execute(delete(models.AuditHeader).where(models.AuditHeader.core_event_id.in_(events_sq)))
    
    db.execute(delete(models.IntegrationDetail).where(models.IntegrationDetail.integration_id.in_(select(models.IntegrationHeader.id).where(models.IntegrationHeader.core_event_id.in_(events_sq)))))
    db.execute(delete(models.IntegrationHeader).where(models.IntegrationHeader.core_event_id.in_(events_sq)))
    
    db.execute(delete(models.NotificationDetail).where(models.NotificationDetail.notification_id.in_(select(models.NotificationHeader.id).where(models.NotificationHeader.core_event_id.in_(events_sq)))))
    db.execute(delete(models.NotificationHeader).where(models.NotificationHeader.core_event_id.in_(events_sq)))
    
    db.execute(delete(models.IncidentDetail).where(models.IncidentDetail.incident_id.in_(incidents_sq)))
    db.execute(delete(models.AgentAction).where(models.AgentAction.incident_id.in_(incidents_sq)))
    db.execute(delete(models.AgentAction).where(models.AgentAction.organization_id == org_id))
    db.execute(delete(models.IncidentHeader).where(models.IncidentHeader.id.in_(incidents_sq)))
    
    db.execute(delete(models.AlertDetail).where(models.AlertDetail.alert_id.in_(alerts_sq)))
    db.execute(delete(models.AlertHeader).where(models.AlertHeader.id.in_(alerts_sq)))
    
    db.execute(delete(models.AIPrediction).where(models.AIPrediction.ai_analysis_id.in_(ai_headers_sq)))
    db.execute(delete(models.AIAnomaly).where(models.AIAnomaly.ai_analysis_id.in_(ai_headers_sq)))
    db.execute(delete(models.AIRiskScore).where(models.AIRiskScore.ai_analysis_id.in_(ai_headers_sq)))
    db.execute(delete(models.AIExplanation).where(models.AIExplanation.ai_analysis_id.in_(ai_headers_sq)))
    db.execute(delete(models.AIAnalysisHeader).where(models.AIAnalysisHeader.id.in_(ai_headers_sq)))
    
    db.execute(delete(models.TelemetryDetail).where(models.TelemetryDetail.telemetry_header_id.in_(telemetry_headers_sq)))
    db.execute(delete(models.TelemetryHeader).where(models.TelemetryHeader.id.in_(telemetry_headers_sq)))
    
    db.execute(delete(models.RawDataDetail).where(models.RawDataDetail.raw_header_id.in_(raw_headers_sq)))
    db.execute(delete(models.RawDataHeader).where(models.RawDataHeader.id.in_(raw_headers_sq)))
    
    db.execute(delete(models.CoreEvent).where(models.CoreEvent.organization_id == org_id))
    
    db.execute(delete(models.AgentMessage).where(models.AgentMessage.conversation_id.in_(convs_sq)))
    db.execute(delete(models.AgentConversation).where(models.AgentConversation.organization_id == org_id))
    
    db.execute(delete(models.SensorIntelligence).where(models.SensorIntelligence.organization_id == org_id))
    db.execute(delete(models.KnowledgeDocument).where(models.KnowledgeDocument.organization_id == org_id))
    db.execute(delete(models.SystemConfiguration).where(models.SystemConfiguration.organization_id == org_id))
    db.execute(delete(models.ThresholdRule).where(models.ThresholdRule.organization_id == org_id))
    
    db.execute(delete(models.SensorCalibration).where(models.SensorCalibration.sensor_id.in_(sensors_sq)))
    db.execute(delete(models.DeviceHealth).where(models.DeviceHealth.device_id.in_(devices_sq)))
    db.execute(delete(models.DeviceCredential).where(models.DeviceCredential.device_id.in_(devices_sq)))
    
    db.execute(delete(models.DimSensor).where(models.DimSensor.device_id.in_(devices_sq)))
    db.execute(delete(models.DimDevice).where(models.DimDevice.room_id.in_(rooms_sq)))
    db.execute(delete(models.DimRoom).where(models.DimRoom.site_id.in_(sites_sq)))
    db.execute(delete(models.DimSite).where(models.DimSite.organization_id == org_id))
    
    db.execute(delete(models.DimUser).where(models.DimUser.organization_id == org_id))
    db.execute(delete(models.DimOrganization).where(models.DimOrganization.id == org_id))
    
    db.commit()
    return {"status": "success", "message": "Organization and all related data successfully deleted"}