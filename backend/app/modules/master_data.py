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
