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