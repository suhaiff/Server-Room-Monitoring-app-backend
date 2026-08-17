"""Phase 2 deterministic threshold evaluation and incident creation."""
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from app import models

DEFAULT_RULES = {
    "temperature": (">", 30.0, "critical"),
    "humidity": (">", 70.0, "warning"),
    "water_leak": ("==", 1.0, "critical"),
    "door_open": ("==", 1.0, "warning"),
    "smoke": ("==", 1.0, "critical"),
}

MESSAGES = {
    "temperature": ("Server-room temperature is above the safe operating limit.", "Check cooling units, airflow and rack inlet temperature immediately."),
    "humidity": ("Server-room humidity is above the configured limit.", "Inspect dehumidification and check for condensation risk."),
    "water_leak": ("Water has been detected in the server-room leak zone.", "Protect floor-level power equipment and inspect the leak source immediately."),
    "door_open": ("Server-room door is open and requires operator attention.", "Verify authorized access and secure the server-room door."),
    "smoke": ("Smoke has been detected in the server room.", "Initiate fire-response verification and follow the approved evacuation procedure."),
}


def evaluate(db: Session, event_id: str, readings: dict) -> list[str]:
    created = []
    event = db.get(models.CoreEvent, event_id)
    for name, value in readings.items():
        if name not in DEFAULT_RULES: continue
        operator, threshold, severity = DEFAULT_RULES[name]
        numeric = float(value)
        breached = numeric > threshold if operator == ">" else numeric == threshold
        existing = db.scalar(
            select(models.AlertHeader)
            .join(models.CoreEvent, models.CoreEvent.id == models.AlertHeader.core_event_id)
            .where(models.CoreEvent.device_id == event.device_id,
                   models.AlertHeader.alert_type == f"{name}_threshold",
                   models.AlertHeader.status == "open")
            .order_by(models.AlertHeader.created_at.desc())
        )
        if not breached:
            # A normal reading closes the active condition. The next real
            # breach can then create a fresh alert and voice announcement.
            if existing:
                existing.status = "resolved"
                for incident in db.scalars(select(models.IncidentHeader).where(models.IncidentHeader.alert_id == existing.id)).all():
                    timestamp = datetime.now(timezone.utc)
                    # Physical recovery does not close the human workflow ticket.
                    # The operator must verify the room and explicitly close it.
                    db.add(models.IncidentDetail(incident_id=incident.id, action_type="condition_normalized", action_description=f"{name} returned to its safe operating state", note="Sensor condition normalized; operator verification and ticket closure are still required", action_timestamp=timestamp, resolution_note="Sensor condition normalized"))
            continue
        if existing:
            # Avoid a new alert and repeated speech every simulator interval
            # while the same physical condition remains active.
            event.has_alert = True
            continue
        header = models.AlertHeader(core_event_id=event_id, alert_type=f"{name}_threshold", severity=severity, status="open")
        db.add(header); db.flush()
        message, recommendation = MESSAGES[name]
        db.add(models.AlertDetail(alert_id=header.id, trigger_type="threshold", trigger_value=numeric, threshold_value=threshold, message=message, priority=severity, recommendation=recommendation))
        incident = models.IncidentHeader(core_event_id=event_id, alert_id=header.id, status="open", severity=severity, priority=severity)
        db.add(incident); db.flush()
        db.add(models.IncidentDetail(incident_id=incident.id, action_type="threshold_breach_recorded", action_description=message, note=f"Incident opened automatically after {name} threshold evaluation", action_timestamp=datetime.now(timezone.utc)))
        event.has_alert = True; event.has_incident = True; created.append(header.id)
    db.commit()
    return created
