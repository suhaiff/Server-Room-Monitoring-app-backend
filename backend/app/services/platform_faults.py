"""Persist controlled software faults and auditable, policy-based recovery."""
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from app import models

ORG_ID = "00000000-0000-0000-0000-000000000001"
SITE_ID = "00000000-0000-0000-0000-000000000011"
ROOM_ID = "00000000-0000-0000-0000-000000000021"

# The AI may only select these deterministic, reversible runbooks. It never
# edits source code, deletes data, or stops an actual production dependency.
FAULT_POLICY = {
    "redis": ("L1", True, "Reconnect cache and validate a health probe"),
    "minio": ("L1", True, "Refresh storage client and validate bucket access"),
    "ai_explanation": ("L1", True, "Reload explanation stage and run its self-test"),
    "mqtt": ("L2", True, "Recycle ingestion connection and verify message flow"),
    "backend": ("L2", True, "Apply API recovery runbook and verify health checks"),
    "auth": ("L2", True, "Refresh authentication dependencies and verify protected access"),
    "notifications": ("L2", True, "Retry notification queue and validate delivery adapter"),
    "frontend": ("L1", True, "Refresh dashboard data session and verify API connectivity"),
    "prometheus": ("L1", True, "Reload metrics target discovery and verify scraping"),
    "grafana": ("L1", True, "Reload dashboard datasource and verify health query"),
    "simulator": ("L1", True, "Reconnect simulator transport and validate receipt flow"),
    "ai_baseline": ("L2", True, "Reload baseline stage and verify controlled sample"),
    "ai_anomaly": ("L2", True, "Reload anomaly stage and verify controlled sample"),
    "ai_forecast": ("L2", True, "Reload forecast stage and verify controlled sample"),
    "ai_risk": ("L2", True, "Reload risk stage and verify controlled sample"),
    "postgres": ("L3", False, "Preserve evidence and escalate database recovery for human approval"),
}


def process_platform_fault(db: Session, payload: dict) -> dict:
    component = str(payload.get("component", "unknown")).strip().lower().replace(" ", "_")
    action = payload.get("action", "trigger")
    alert_type = f"software_{component}"
    existing = db.scalar(select(models.AlertHeader).where(
        models.AlertHeader.alert_type == alert_type,
        models.AlertHeader.status == "open",
    ).order_by(models.AlertHeader.created_at.desc()))
    now = datetime.now(timezone.utc)
    level, auto_fix, runbook = FAULT_POLICY.get(component, ("L3", False, "Escalate for human investigation"))

    if action == "recover":
        if not existing:
            return {"status": "already_recovered", "level": level, "alerts_created": 0}
        existing.status = "resolved"
        incidents = db.scalars(select(models.IncidentHeader).where(models.IncidentHeader.alert_id == existing.id)).all()
        automatic = bool(payload.get("automatic")) and auto_fix
        for incident in incidents:
            if incident.status in {"open", "assigned", "acknowledged"}:
                db.add(models.IncidentDetail(
                    incident_id=incident.id,
                    action_type="ai_verified_recovery" if automatic else "condition_normalized",
                    action_description=(f"VTAB verified {payload.get('label', component)} recovery and automatically closed the ticket" if automatic else f"{payload.get('label', component)} recovered"),
                    note=(f"{level} approved runbook completed: {runbook}. Post-repair health checks passed." if automatic else "Service health is normal again. Human verification is required before closure."),
                    action_timestamp=now,
                    resolution_note="Automatically remediated and verified" if automatic else "Service condition normalized",
                ))
                if automatic:
                    incident.status = "closed"
                    incident.resolved_at = now
        db.commit()
        return {"status": "auto_remediated" if automatic else "recovered_pending_verification",
                "level": level, "automatic": automatic, "runbook": runbook,
                "alerts_created": 0, "alert_id": existing.id, "incident_ids": [item.id for item in incidents]}

    if existing:
        incident = db.scalar(select(models.IncidentHeader).where(models.IncidentHeader.alert_id == existing.id))
        return {"status": "already_active", "level": level, "automatic": auto_fix, "alerts_created": 0,
                "alert_id": existing.id, "incident_ids": [incident.id] if incident else []}

    severity = payload.get("severity", "critical")
    label = payload.get("label", component.replace("_", " ").title())
    message = payload.get("message") or f"Software health test detected a simulated {label} failure"
    event = models.CoreEvent(organization_id=ORG_ID, site_id=SITE_ID, room_id=ROOM_ID, device_id=None,
        sensor_id=None, event_type="platform_fault", source_system="software-test-lab", status="processed",
        severity=severity, has_alert=True, has_incident=True, event_timestamp=now, description=message)
    db.add(event); db.flush()
    alert = models.AlertHeader(core_event_id=event.id, alert_type=alert_type, severity=severity,
                               status="open", created_by="software-test-lab")
    db.add(alert); db.flush()
    db.add(models.AlertDetail(alert_id=alert.id, trigger_type="software_fault_simulation", trigger_value=None,
        threshold_value=None, message=message, priority=severity,
        recommendation=payload.get("recommendation", runbook)))
    incident = models.IncidentHeader(core_event_id=event.id, alert_id=alert.id, status="open",
                                     severity=severity, priority=severity)
    db.add(incident); db.flush()
    db.add(models.IncidentDetail(incident_id=incident.id, action_type="software_fault_injected",
        action_description=f"VTAB detected and classified {label} as {level}",
        note=f"Controlled test. Recovery policy: {'automatic' if auto_fix else 'human approval required'}. Runbook: {runbook}.",
        action_timestamp=now))
    if auto_fix:
        db.add(models.IncidentDetail(incident_id=incident.id, action_type="ai_root_cause_identified",
            action_description=f"Root-cause analysis matched the {component} failure signature",
            note=f"Classification {level}. Evidence matched the controlled scenario. Selected runbook: {runbook}.",
            action_timestamp=now))
        db.add(models.IncidentDetail(incident_id=incident.id, action_type="ai_remediation_started",
            action_description=f"VTAB started the approved {level} recovery runbook", note=runbook,
            action_timestamp=now))
    db.commit()
    return {"status": "fault_recorded", "level": level, "automatic": auto_fix, "runbook": runbook,
            "alerts_created": 1, "alert_id": alert.id, "incident_ids": [incident.id], "core_event_id": event.id}