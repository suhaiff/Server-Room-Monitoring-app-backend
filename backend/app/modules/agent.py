from datetime import datetime,timezone
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from sqlalchemy import desc,select
from sqlalchemy.orm import Session
from app import models
from app.core.database import get_db
from app.core.security import current_user,require_roles
from app.services.operations_agent import answer,digital_twin,intelligence,live_evidence
from app.services.alerts import adaptive_rule_details
router=APIRouter(prefix="/agent",tags=["VTAB 2.0 Operations Agent"])
class ChatIn(BaseModel): message:str=Field(min_length=2,max_length=2000);conversation_id:str|None=None
class ActionIn(BaseModel): action_type:str;risk_level:str=Field(pattern="^L[123]$");rationale:str="";incident_id:str|None=None
class KnowledgeIn(BaseModel): title:str;category:str="runbook";content:str;version:str="1.0"
@router.get("/overview")
def overview(db:Session=Depends(get_db),user=Depends(current_user)):return {"version":"2.4.0","agent_status":"monitoring","provider":"evidence-first-local","capabilities":["copilot","governed-remediation","predictive-intelligence","knowledge","digital-twin"],"snapshot":live_evidence(db,user.organization_id)}
@router.post("/chat")
def chat(body:ChatIn,db:Session=Depends(get_db),user=Depends(current_user)):return answer(db,user,body.message,body.conversation_id)
@router.get("/intelligence")
def predictive(db:Session=Depends(get_db),user=Depends(current_user)):return intelligence(db,user.organization_id)
@router.get("/climate-control")
def climate_control(db:Session=Depends(get_db),user=Depends(current_user)):
    current={}
    for name in ("temperature","humidity"):
        row=db.scalar(select(models.TelemetryDetail).join(models.TelemetryHeader).join(models.CoreEvent).where(models.CoreEvent.organization_id==user.organization_id,models.TelemetryDetail.measurement_type==name).order_by(desc(models.TelemetryDetail.measurement_timestamp)))
        current[name]=row.value_numeric if row else None
    active=db.scalars(select(models.AgentAction).where(models.AgentAction.organization_id==user.organization_id,models.AgentAction.action_type.in_(["balance_cooling_setpoint","reduce_cooling_output","activate_dehumidification"]),models.AgentAction.status=="monitoring").order_by(desc(models.AgentAction.created_at))).all()
    temperature_policy=adaptive_rule_details(db,user.organization_id,"temperature") or {}
    lower=float(temperature_policy.get("effective_lower_threshold") or 18);upper=float(temperature_policy.get("effective_threshold") or 30);value=current["temperature"]
    demand="waiting_for_telemetry" if value is None else "reduce_cooling" if value<lower else "increase_cooling" if value>upper else "hold_safe_band"
    return {"target_temperature_c":22,"target_humidity_percent":50,"mode":"balancing" if active else "standby","current":current,"temperature_policy":{"mode":temperature_policy.get("mode","manual"),"minimum_c":lower,"maximum_c":upper,"critical_minimum_c":15,"critical_maximum_c":float(temperature_policy.get("hard_safety_ceiling") or 40)},"cooling_recommendation":demand,"active_controls":[{"id":a.id,"action_type":a.action_type,"status":a.status,"rationale":a.rationale,"timeline":a.execution_log} for a in active],"physical_hvac_configured":False,"simulated_hvac_available":True,"notice":"The Test Lab HVAC model closes the loop through MQTT. Physical HVAC commands remain disabled until an actuator integration is configured."}
@router.get("/digital-twin")
def twin(db:Session=Depends(get_db),user=Depends(current_user)):return digital_twin(db,user.organization_id)
@router.post("/actions")
def propose(body:ActionIn,db:Session=Depends(get_db),user=Depends(current_user)):
    approval=body.risk_level in {"L2","L3"};status="awaiting_approval" if approval else "verified";now=datetime.now(timezone.utc);log=[{"step":1,"state":"diagnosed","at":now.isoformat()},{"step":2,"state":status,"at":now.isoformat()}]
    row=models.AgentAction(organization_id=user.organization_id,incident_id=body.incident_id,action_type=body.action_type,risk_level=body.risk_level,status=status,requires_approval=approval,rationale=body.rationale,execution_log=log,requested_by=user.id,completed_at=now if not approval else None);db.add(row);db.commit();db.refresh(row);return {"id":row.id,"status":row.status,"requires_approval":approval,"timeline":row.execution_log}
@router.get("/actions")
def actions(db:Session=Depends(get_db),user=Depends(current_user)):return [{"id":r.id,"incident_id":r.incident_id,"action_type":r.action_type,"risk_level":r.risk_level,"status":r.status,"requires_approval":r.requires_approval,"rationale":r.rationale,"timeline":r.execution_log,"created_at":r.created_at} for r in db.scalars(select(models.AgentAction).where(models.AgentAction.organization_id==user.organization_id).order_by(desc(models.AgentAction.created_at)).limit(50)).all()]
@router.post("/actions/{action_id}/{decision}")
def decide(action_id:str,decision:str,db:Session=Depends(get_db),user=Depends(require_roles("admin","facility_manager"))):
    if decision not in {"approve","reject"}:raise HTTPException(400,"Decision must be approve or reject")
    row=db.get(models.AgentAction,action_id)
    if not row or row.organization_id!=user.organization_id:raise HTTPException(404,"Action not found")
    row.status="verified" if decision=="approve" else "rejected";row.approved_by=user.id;row.execution_log=[*row.execution_log,{"step":len(row.execution_log)+1,"state":row.status,"by":user.id,"at":datetime.now(timezone.utc).isoformat()}];row.completed_at=datetime.now(timezone.utc);db.commit();return {"id":row.id,"status":row.status,"timeline":row.execution_log}
@router.get("/knowledge")
def knowledge(q:str="",db:Session=Depends(get_db),user=Depends(current_user)):
    rows=db.scalars(select(models.KnowledgeDocument).where(models.KnowledgeDocument.organization_id==user.organization_id,models.KnowledgeDocument.is_active.is_(True))).all();words=q.lower().split();return [{"id":r.id,"title":r.title,"category":r.category,"content":r.content,"version":r.version} for r in rows if not words or any(w in (r.title+" "+r.content).lower() for w in words)]
@router.post("/knowledge")
def add_knowledge(body:KnowledgeIn,db:Session=Depends(get_db),user=Depends(require_roles("admin","facility_manager"))):
    row=models.KnowledgeDocument(organization_id=user.organization_id,**body.model_dump());db.add(row);db.commit();db.refresh(row);return {"id":row.id,"title":row.title}



