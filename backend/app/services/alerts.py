"""Configurable alert evaluation with deduplication and evidence-based recovery."""
from datetime import datetime, timezone
from statistics import median
from sqlalchemy import desc, select
from sqlalchemy.orm import Session
from app import models

DEFAULT_RULES = {
    "temperature": ("gt", 30.0, "critical"),
    "humidity": ("gt", 70.0, "warning"),
    "water_leak": ("eq", 1.0, "critical"),
    "door_open": ("eq", 1.0, "warning"),
    "smoke": ("eq", 1.0, "critical"),
}
RECOVERY_SAMPLES = 3
MIN_SAFE_TEMPERATURE_C = 18.0
CRITICAL_LOW_TEMPERATURE_C = 15.0
MESSAGES = {
    "temperature": ("Server-room temperature is above the configured safe limit.", "Check cooling units, airflow and rack inlet temperature immediately."),
    "humidity": ("Server-room humidity is above the configured limit.", "Inspect humidification controls and check for condensation risk."),
    "water_leak": ("Water has been detected in the server-room leak zone.", "Protect floor-level power equipment and inspect the leak source immediately."),
    "door_open": ("Server-room door is open and requires operator attention.", "Verify authorized access and secure the server-room door."),
    "smoke": ("Smoke has been detected in the server room.", "Initiate fire-response verification and follow the approved evacuation procedure."),
}

def is_breached(value: float, operator: str, threshold: float) -> bool:
    return {"gt": value > threshold, "gte": value >= threshold, "lt": value < threshold,
            "lte": value <= threshold, "eq": value == threshold}.get(operator, False)

def threshold_mode(db: Session, organization_id: str, name: str) -> str:
    """Return the operator-selected threshold mode without requiring a schema migration."""
    config = db.scalar(select(models.SystemConfiguration).where(
        models.SystemConfiguration.organization_id == organization_id,
        models.SystemConfiguration.key == "threshold_modes",
    ))
    configured_modes = config.value if config and isinstance(config.value, dict) else {}
    requested = configured_modes.get(name, "manual")
    return "auto" if name in {"temperature", "humidity"} and requested == "auto" else "manual"


def adaptive_rule_details(db: Session, organization_id: str, name: str) -> dict | None:
    row = db.scalar(select(models.ThresholdRule).where(
        models.ThresholdRule.organization_id == organization_id,
        models.ThresholdRule.measurement_type == name,
        models.ThresholdRule.enabled.is_(True),
    ))
    base = (row.operator, row.threshold, row.severity) if row else DEFAULT_RULES.get(name)
    if not base:
        return None

    operator, configured, severity = base
    mode = threshold_mode(db, organization_id, name)
    details = {
        "operator": operator,
        "configured_threshold": float(configured),
        "effective_threshold": float(configured),
        "severity": severity,
        "mode": mode,
        "learning_status": "manual",
        "sample_count": 0,
        "baseline": None,
        "hard_safety_ceiling": None,
        "hard_safety_floor": CRITICAL_LOW_TEMPERATURE_C if name == "temperature" else None,
        "effective_lower_threshold": MIN_SAFE_TEMPERATURE_C if name == "temperature" else None,
    }

    if name not in {"temperature", "humidity"} or operator not in {"gt", "gte"}:
        return details

    ceiling = 40.0 if name == "temperature" else 90.0
    details["hard_safety_ceiling"] = ceiling
    details["effective_threshold"] = min(float(configured), ceiling)
    if mode != "auto":
        return details

    values = [float(value) for value in db.scalars(
        select(models.TelemetryDetail.value_numeric)
        .join(models.TelemetryHeader)
        .join(models.CoreEvent)
        .where(
            models.CoreEvent.organization_id == organization_id,
            models.TelemetryDetail.measurement_type == name,
            models.TelemetryDetail.quality_status == "valid",
            models.TelemetryDetail.value_numeric.is_not(None),
        )
        .order_by(desc(models.TelemetryDetail.measurement_timestamp))
        .limit(60)
    ).all()]
    details["sample_count"] = len(values)
    details["learning_status"] = "learning" if len(values) < 8 else "active"
    if len(values) < 8:
        return details

    baseline = float(median(values))
    margin = 3.0 if name == "temperature" else 5.0
    details.update({
        "baseline": round(baseline, 2),
        "effective_threshold": round(min(ceiling, max(float(configured), baseline + margin)), 2),
    })
    if name == "temperature":
        details["effective_lower_threshold"] = round(min(22.0, max(MIN_SAFE_TEMPERATURE_C, baseline - 5.0)), 2)
    return details


def active_rule(db: Session, organization_id: str, name: str):
    details = adaptive_rule_details(db, organization_id, name)
    return (details["operator"], details["effective_threshold"], details["severity"]) if details else None
def stable_recovery(db: Session, device_id: str, name: str, operator: str, threshold: float) -> bool:
    values = db.scalars(
        select(models.TelemetryDetail.value_numeric)
        .join(models.TelemetryHeader, models.TelemetryHeader.id == models.TelemetryDetail.telemetry_header_id)
        .where(models.TelemetryHeader.device_id == device_id,
               models.TelemetryDetail.measurement_type == name,
               models.TelemetryDetail.quality_status == "valid")
        .order_by(desc(models.TelemetryDetail.measurement_timestamp)).limit(RECOVERY_SAMPLES)
    ).all()
    return len(values) == RECOVERY_SAMPLES and all(not is_breached(float(v), operator, threshold) for v in values if v is not None)

def ensure_climate_action(db: Session, event, incident, name: str, numeric: float, threshold: float):
    """Create one auditable climate-control action per active environmental ticket."""
    if name not in {"temperature", "humidity"}: return
    action_type = "balance_cooling_setpoint" if name == "temperature" else "activate_dehumidification"
    existing = db.scalar(select(models.AgentAction).where(models.AgentAction.incident_id == incident.id, models.AgentAction.action_type == action_type, models.AgentAction.status.in_(["monitoring", "verified", "awaiting_approval"])))
    if existing: return
    now = datetime.now(timezone.utc)
    simulated = event.source_system != "mqtt"
    mode = "simulated actuator" if simulated else "HVAC integration command"
    action = models.AgentAction(organization_id=event.organization_id, incident_id=incident.id, action_type=action_type, risk_level="L1", status="monitoring", requires_approval=False, rationale=f"{name} {numeric:g} breached configured limit {threshold:g}", requested_by="operations-agent", execution_log=[{"step":1,"state":"breach_confirmed","value":numeric,"threshold":threshold,"at":now.isoformat()},{"step":2,"state":"control_command_issued","mode":mode,"target_temperature_c":22,"target_humidity_percent":50,"at":now.isoformat()},{"step":3,"state":"monitoring_recovery","safe_samples_required":RECOVERY_SAMPLES,"at":now.isoformat()}])
    db.add(action)
    db.add(models.IncidentDetail(incident_id=incident.id,action_type="ai_climate_control_started",action_description=f"Operations agent started {action_type.replace('_',' ')}",note=f"Target 22 C / 50% RH via {mode}; physical HVAC requires configured actuator integration",action_timestamp=now))

def ensure_low_temperature_action(db: Session, event, incident, numeric: float, threshold: float):
    existing = db.scalar(select(models.AgentAction).where(models.AgentAction.incident_id == incident.id, models.AgentAction.action_type == "reduce_cooling_output", models.AgentAction.status.in_(["monitoring", "verified", "awaiting_approval"])))
    if existing: return
    now = datetime.now(timezone.utc); simulated = event.source_system != "mqtt"; mode = "simulated actuator" if simulated else "HVAC integration command"
    db.add(models.AgentAction(organization_id=event.organization_id, incident_id=incident.id, action_type="reduce_cooling_output", risk_level="L1", status="monitoring", requires_approval=False, rationale=f"temperature {numeric:g} fell below minimum safe limit {threshold:g}", requested_by="operations-agent", execution_log=[{"step":1,"state":"cold_breach_confirmed","value":numeric,"threshold":threshold,"at":now.isoformat()},{"step":2,"state":"cooling_reduction_command_issued","mode":mode,"target_temperature_c":22,"at":now.isoformat()},{"step":3,"state":"monitoring_recovery","safe_samples_required":RECOVERY_SAMPLES,"at":now.isoformat()}]))
    db.add(models.IncidentDetail(incident_id=incident.id,action_type="ai_climate_control_started",action_description="Operations agent reduced cooling demand",note=f"Target 22 C via {mode}; inspect condensation and rack inlet temperatures",action_timestamp=now))


def evaluate_low_temperature(db: Session, event, numeric: float) -> list[str]:
    details = adaptive_rule_details(db, event.organization_id, "temperature") or {}
    threshold = float(details.get("effective_lower_threshold") or MIN_SAFE_TEMPERATURE_C)
    breached = numeric < threshold
    severity = "critical" if numeric <= CRITICAL_LOW_TEMPERATURE_C else "warning"
    existing = db.scalar(select(models.AlertHeader).join(models.CoreEvent,models.CoreEvent.id==models.AlertHeader.core_event_id).where(models.CoreEvent.device_id==event.device_id,models.AlertHeader.alert_type=="temperature_low_threshold",models.AlertHeader.status.in_(["open","resolved"])).order_by(models.AlertHeader.created_at.desc()))
    active_incidents=[] if not existing else db.scalars(select(models.IncidentHeader).where(models.IncidentHeader.alert_id==existing.id,models.IncidentHeader.status.in_(["open","assigned","acknowledged"]))).all()
    if not breached:
        if existing and active_incidents:
            timestamp=datetime.now(timezone.utc)
            if existing.status=="open":
                existing.status="resolved"
                for incident in active_incidents:
                    db.add(models.IncidentDetail(incident_id=incident.id,action_type="condition_normalized",action_description="Temperature returned above the minimum safe limit",note=f"Waiting for {RECOVERY_SAMPLES} consecutive safe readings before automatic closure",action_timestamp=timestamp,resolution_note="Excessive-cooling condition normalized"))
            if stable_recovery(db,event.device_id,"temperature","lt",threshold):
                existing.status="closed"
                for incident in active_incidents:
                    incident.status="closed";incident.resolved_at=timestamp;complete_climate_actions(db,incident.id,timestamp)
                    db.add(models.IncidentDetail(incident_id=incident.id,action_type="ai_verified_recovery",action_description=f"Recovery policy verified {RECOVERY_SAMPLES} consecutive safe temperature readings and closed the excessive-cooling ticket",note="Cooling demand can return to automatic control",action_timestamp=timestamp,resolution_note=f"Temperature normalized above {threshold:g} C"))
        return []
    if existing and active_incidents:
        if severity=="critical" and existing.severity!="critical":
            existing.severity="critical"
            for incident in active_incidents:
                incident.severity="critical";incident.priority="critical"
                db.add(models.IncidentDetail(incident_id=incident.id,action_type="severity_escalated",action_description="Temperature crossed the critical low safety floor",note=f"Measured {numeric:g} C; critical floor {CRITICAL_LOW_TEMPERATURE_C:g} C",action_timestamp=datetime.now(timezone.utc)))
        if existing.status=="resolved":existing.status="open"
        ensure_low_temperature_action(db,event,active_incidents[0],numeric,threshold);event.has_alert=True
        return []
    header=models.AlertHeader(core_event_id=event.id,alert_type="temperature_low_threshold",severity=severity,status="open");db.add(header);db.flush()
    message="Server-room temperature is below the minimum safe operating limit."
    recommendation="Reduce or stop cooling output, inspect thermostat control and check for condensation or unsafe rack inlet temperatures."
    db.add(models.AlertDetail(alert_id=header.id,trigger_type="minimum_temperature_safety",trigger_value=numeric,threshold_value=threshold,message=message,priority=severity,recommendation=recommendation))
    incident=models.IncidentHeader(core_event_id=event.id,alert_id=header.id,status="open",severity=severity,priority=severity);db.add(incident);db.flush()
    db.add(models.IncidentDetail(incident_id=incident.id,action_type="threshold_breach_recorded",action_description=message,note=f"Ticket opened using adaptive minimum-temperature limit {threshold:g} C",action_timestamp=datetime.now(timezone.utc)))
    ensure_low_temperature_action(db,event,incident,numeric,threshold);event.has_alert=True;event.has_incident=True
    return [header.id]

def complete_climate_actions(db: Session, incident_id: str, timestamp: datetime):
    for action in db.scalars(select(models.AgentAction).where(models.AgentAction.incident_id==incident_id,models.AgentAction.status=="monitoring")).all():
        action.status="verified";action.completed_at=timestamp;action.execution_log=[*action.execution_log,{"step":len(action.execution_log)+1,"state":"recovery_verified","at":timestamp.isoformat()}]

def evaluate(db: Session, event_id: str, readings: dict) -> list[str]:
    created=[]; event=db.get(models.CoreEvent,event_id)
    if "temperature" in readings:
        created.extend(evaluate_low_temperature(db,event,float(readings["temperature"])))
    for name,value in readings.items():
        rule=active_rule(db,event.organization_id,name)
        if not rule: continue
        operator,threshold,severity=rule; numeric=float(value); adaptive=adaptive_rule_details(db,event.organization_id,name); hard_ceiling=adaptive.get("hard_safety_ceiling") if adaptive else None; breached=is_breached(numeric,operator,float(threshold)) or bool(hard_ceiling and numeric>=hard_ceiling); severity="critical" if hard_ceiling and numeric>=hard_ceiling else severity
        existing=db.scalar(select(models.AlertHeader).join(models.CoreEvent,models.CoreEvent.id==models.AlertHeader.core_event_id).where(
            models.CoreEvent.device_id==event.device_id,models.AlertHeader.alert_type==f"{name}_threshold",models.AlertHeader.status.in_(["open","resolved"])).order_by(models.AlertHeader.created_at.desc()))
        active_incidents=[] if not existing else db.scalars(select(models.IncidentHeader).where(models.IncidentHeader.alert_id==existing.id,models.IncidentHeader.status.in_(["open","assigned","acknowledged"]))).all()
        if not breached:
            if existing and active_incidents:
                timestamp=datetime.now(timezone.utc)
                if existing.status=="open":
                    existing.status="resolved"
                    for incident in active_incidents:
                        db.add(models.IncidentDetail(incident_id=incident.id,action_type="condition_normalized",action_description=f"{name} returned to its configured safe range",note=f"Waiting for {RECOVERY_SAMPLES} consecutive safe readings before automatic closure",action_timestamp=timestamp,resolution_note="Sensor condition normalized"))
                if stable_recovery(db,event.device_id,name,operator,float(threshold)):
                    existing.status="closed"
                    for incident in active_incidents:
                        incident.status="closed";incident.resolved_at=timestamp;complete_climate_actions(db,incident.id,timestamp)
                        db.add(models.IncidentDetail(incident_id=incident.id,action_type="ai_verified_recovery",action_description=f"VTAB recovery policy verified {RECOVERY_SAMPLES} consecutive safe {name} readings and closed the ticket",note="Automatic closure is evidence-based and auditable",action_timestamp=timestamp,resolution_note=f"{name} normalized against configured threshold {threshold}"))
            continue
        if existing and active_incidents:
            if existing.status=="resolved":
                existing.status="open"
                for incident in active_incidents:
                    db.add(models.IncidentDetail(incident_id=incident.id,action_type="condition_recurred",action_description=f"{name} breached again before recovery verification completed",note="Automatic recovery counter reset",action_timestamp=datetime.now(timezone.utc)))
            ensure_climate_action(db,event,active_incidents[0],name,numeric,float(threshold));event.has_alert=True;continue
        header=models.AlertHeader(core_event_id=event_id,alert_type=f"{name}_threshold",severity=severity,status="open");db.add(header);db.flush()
        message,recommendation=MESSAGES[name]
        db.add(models.AlertDetail(alert_id=header.id,trigger_type="configured_threshold",trigger_value=numeric,threshold_value=threshold,message=message,priority=severity,recommendation=recommendation))
        incident=models.IncidentHeader(core_event_id=event_id,alert_id=header.id,status="open",severity=severity,priority=severity);db.add(incident);db.flush()
        db.add(models.IncidentDetail(incident_id=incident.id,action_type="threshold_breach_recorded",action_description=message,note=f"Ticket opened using configured {operator} {threshold} rule",action_timestamp=datetime.now(timezone.utc)));ensure_climate_action(db,event,incident,name,numeric,float(threshold))
        event.has_alert=True;event.has_incident=True;created.append(header.id)
    db.commit();return created







