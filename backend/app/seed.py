"""Idempotent local seed matching the simulated ESP32 device identifier."""
from app import models
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password

ORG="00000000-0000-0000-0000-000000000001"; SITE="00000000-0000-0000-0000-000000000011"; ROOM="00000000-0000-0000-0000-000000000021"; DEVICE="00000000-0000-0000-0000-000000000101"

def run():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        existing = db.get(models.DimOrganization, ORG)
        if existing:
            device = db.get(models.DimDevice, DEVICE)
            if device and "Arduino" in device.hardware_type:
                device.hardware_type="ESP32 WiFi"; device.name="ESP32 Sentinel 01"; device.firmware_version="esp32-sim-2.0"; db.commit()
            return
        db.add(models.DimOrganization(id=ORG,name="VTAB Demo Organization",subscription_plan="enterprise")); db.flush()
        db.add(models.DimSite(id=SITE,organization_id=ORG,name="Demo Data Center",location="Local Lab")); db.flush()
        db.add(models.DimRoom(id=ROOM,site_id=SITE,name="Server Room A",floor="Ground")); db.flush()
        db.add(models.DimDevice(id=DEVICE,room_id=ROOM,name="ESP32 Sentinel 01",hardware_type="ESP32 WiFi",firmware_version="esp32-sim-2.0")); db.flush()
        for kind,unit,low,high in [("temperature","C",-20,100),("humidity","%",0,100),("water_leak","bool",0,1),("door_open","bool",0,1),("smoke","bool",0,1)]: db.add(models.DimSensor(device_id=DEVICE,sensor_type=kind,unit=unit,min_valid=low,max_valid=high))
        for name,permissions in [("admin",["*"]),("facility_manager",["manage_devices","manage_incidents"]),("engineer",["manage_incidents"]),("viewer",["read"])]: db.add(models.DimRole(name=name,permissions=permissions))
        db.add(models.DimUser(organization_id=ORG,email="admin@vtab.local",full_name="VTAB Administrator",password_hash=hash_password("Admin123!"),role_name="admin"))
        for name in ["telemetry","alert","incident","notification","integration","device_health"]: db.add(models.DimEventType(name=name))
        for name in ["mqtt","https","system","ai"]: db.add(models.DimSourceSystem(name=name))
        for name in ["received","processed","open","acknowledged","resolved","failed"]: db.add(models.DimStatus(name=name))
        for rank,name in enumerate(["info","warning","critical"]): db.add(models.DimSeverity(name=name,rank=rank))
        for measurement,operator,threshold,severity in [("temperature","gt",30,"critical"),("humidity","gt",70,"warning"),("water_leak","eq",1,"critical"),("door_open","eq",1,"warning"),("smoke","eq",1,"critical")]: db.add(models.ThresholdRule(organization_id=ORG,measurement_type=measurement,operator=operator,threshold=threshold,severity=severity))
        db.commit(); print("Seeded VTAB Sentinel ESP32 demo tenant")

if __name__ == "__main__": run()
