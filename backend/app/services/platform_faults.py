"""Persist safe software-fault simulations as normal VTAB alerts and tickets."""
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from app import models

ORG_ID = "00000000-0000-0000-0000-000000000001"
SITE_ID = "00000000-0000-0000-0000-000000000011"
ROOM_ID = "00000000-0000-0000-0000-000000000021"


def process_platform_fault(db: Session, payload: dict) -> dict:
    component = str(payload.get("component", "unknown")).strip().lower().replace(" ", "_")
    action = payload.get("action", "trigger")
    alert_type = f"software_{component}"
    existing = db.scalar(
        select(models.AlertHeader)
        .where(models.AlertHeader.alert_type == alert_type, models.AlertHeader.status == "open")
        .order_by(models.AlertHeader.created_at.desc())
    )
    now = datetime.now(timezone.utc)

    if action == "recover":
        if not existing:
            return {"status": "already_recovered", "alerts_created": 0}
        existing.status = "resolved"
        incidents = db.scalars(select(models.IncidentHeader).where(models.IncidentHeader.alert_id == existing.id)).all()
        for incident in incidents:
            if incident.status in {"open", "assigned", "acknowledged"}:
                db.add(models.IncidentDetail(
                    incident_id=incident.id,
                    action_type="condition_normalized",
                    action_description=f"{payload.get('label', component)} recovered",
                    note="Service health is normal again. Operator verification and ticket closure are still required.",
                    action_timestamp=now,
                ))
        db.commit()
        return {"status": "recovered_pending_verification", "alerts_created": 0, "alert_id": existing.id,
                "incident_ids": [item.id for item in incidents]}

    if existing:
        incident = db.scalar(select(models.IncidentHeader).where(models.IncidentHeader.alert_id == existing.id))
        return {"status": "already_active", "alerts_created": 0, "alert_id": existing.id,
                "incident_ids": [incident.id] if incident else []}

    severity = payload.get("severity", "critical")
    label = payload.get("label", component.replace("_", " ").title())
    message = payload.get("message") or f"Software health test detected a simulated {label} failure"
    event = models.CoreEvent(
        organization_id=ORG_ID, site_id=SITE_ID, room_id=ROOM_ID, device_id=None, sensor_id=None,
        event_type="platform_fault", source_system="software-test-lab", status="processed",
        severity=severity, has_alert=True, has_incident=True, event_timestamp=now,
        description=message,
    )
    db.add(event); db.flush()
    alert = models.AlertHeader(core_event_id=event.id, alert_type=alert_type, severity=severity,
                               status="open", created_by="software-test-lab")
    db.add(alert); db.flush()
    db.add(models.AlertDetail(
        alert_id=alert.id, trigger_type="software_fault_simulation", trigger_value=None,
        threshold_value=None, message=message, priority=severity,
        recommendation=payload.get("recommendation", "Inspect service diagnostics, restore the component, then verify and close this ticket."),
    ))
    incident = models.IncidentHeader(core_event_id=event.id, alert_id=alert.id, status="open",
                                     severity=severity, priority=severity)
    db.add(incident); db.flush()
    db.add(models.IncidentDetail(
        incident_id=incident.id, action_type="software_fault_injected",
        action_description=f"Safe test fault injected for {label}",
        note="This is a controlled software test. No Docker container was stopped.", action_timestamp=now,
    ))
    db.commit()
    return {"status": "fault_recorded", "alerts_created": 1, "alert_id": alert.id,
            "incident_ids": [incident.id], "core_event_id": event.id}
