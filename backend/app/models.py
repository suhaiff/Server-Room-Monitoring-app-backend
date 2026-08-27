"""ORM representation of the PDF's 37-table centralized event model."""
import uuid
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


def uid() -> str: return str(uuid.uuid4())
def now() -> datetime: return datetime.now(timezone.utc)


class UUIDMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


# 12 master/dimension tables
class DimOrganization(UUIDMixin, Base):
    __tablename__ = "dim_organizations"
    name: Mapped[str] = mapped_column(String(150), unique=True)
    subscription_plan: Mapped[str] = mapped_column(String(50), default="demo")
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

class DimSite(UUIDMixin, Base):
    __tablename__ = "dim_sites"
    organization_id: Mapped[str] = mapped_column(ForeignKey("dim_organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(150)); location: Mapped[str] = mapped_column(String(255), default="")

class DimRoom(UUIDMixin, Base):
    __tablename__ = "dim_rooms"
    site_id: Mapped[str] = mapped_column(ForeignKey("dim_sites.id"), index=True)
    name: Mapped[str] = mapped_column(String(150)); floor: Mapped[str] = mapped_column(String(50), default="")

class DimDevice(UUIDMixin, Base):
    __tablename__ = "dim_devices"
    room_id: Mapped[str] = mapped_column(ForeignKey("dim_rooms.id"), index=True)
    name: Mapped[str] = mapped_column(String(150)); hardware_type: Mapped[str] = mapped_column(String(80), default="Arduino UNO R4 WiFi")
    firmware_version: Mapped[str] = mapped_column(String(40), default="sim-1.0"); status: Mapped[str] = mapped_column(String(30), default="online")
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class DimSensor(UUIDMixin, Base):
    __tablename__ = "dim_sensors"
    device_id: Mapped[str] = mapped_column(ForeignKey("dim_devices.id"), index=True)
    sensor_type: Mapped[str] = mapped_column(String(50)); unit: Mapped[str] = mapped_column(String(20), default="")
    min_valid: Mapped[float | None] = mapped_column(Float); max_valid: Mapped[float | None] = mapped_column(Float)

class DimUser(UUIDMixin, Base):
    __tablename__ = "dim_users"
    organization_id: Mapped[str] = mapped_column(ForeignKey("dim_organizations.id"), index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True); full_name: Mapped[str] = mapped_column(String(150))
    password_hash: Mapped[str] = mapped_column(String(255)); role_name: Mapped[str] = mapped_column(String(30), default="viewer")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class DimRole(UUIDMixin, Base):
    __tablename__ = "dim_roles"
    name: Mapped[str] = mapped_column(String(30), unique=True); permissions: Mapped[list] = mapped_column(JSON, default=list)

class DimEventType(UUIDMixin, Base):
    __tablename__ = "dim_event_types"
    name: Mapped[str] = mapped_column(String(60), unique=True)

class DimSourceSystem(UUIDMixin, Base):
    __tablename__ = "dim_source_systems"
    name: Mapped[str] = mapped_column(String(60), unique=True)

class DimStatus(UUIDMixin, Base):
    __tablename__ = "dim_status"
    name: Mapped[str] = mapped_column(String(40), unique=True)

class DimSeverity(UUIDMixin, Base):
    __tablename__ = "dim_severity"
    name: Mapped[str] = mapped_column(String(30), unique=True); rank: Mapped[int] = mapped_column(Integer, default=0)

class DimTime(UUIDMixin, Base):
    __tablename__ = "dim_time"
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), unique=True); hour: Mapped[int] = mapped_column(Integer); day_of_week: Mapped[int] = mapped_column(Integer)


class CoreEvent(UUIDMixin, Base):
    __tablename__ = "core_events"
    organization_id: Mapped[str] = mapped_column(ForeignKey("dim_organizations.id"), index=True)
    site_id: Mapped[str | None] = mapped_column(ForeignKey("dim_sites.id")); room_id: Mapped[str | None] = mapped_column(ForeignKey("dim_rooms.id"))
    device_id: Mapped[str | None] = mapped_column(ForeignKey("dim_devices.id")); sensor_id: Mapped[str | None] = mapped_column(ForeignKey("dim_sensors.id"))
    event_type: Mapped[str] = mapped_column(String(60)); source_system: Mapped[str] = mapped_column(String(60), default="mqtt")
    status: Mapped[str] = mapped_column(String(40), default="received"); severity: Mapped[str] = mapped_column(String(30), default="info")
    has_raw_data: Mapped[bool] = mapped_column(Boolean, default=False); has_telemetry: Mapped[bool] = mapped_column(Boolean, default=False)
    has_ai: Mapped[bool] = mapped_column(Boolean, default=False); has_alert: Mapped[bool] = mapped_column(Boolean, default=False)
    has_incident: Mapped[bool] = mapped_column(Boolean, default=False); has_notification: Mapped[bool] = mapped_column(Boolean, default=False)
    has_integration: Mapped[bool] = mapped_column(Boolean, default=False); event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    description: Mapped[str] = mapped_column(Text, default="")


# Header -> details modules (24 tables)
class RawDataHeader(UUIDMixin, Base):
    __tablename__ = "raw_data_headers"
    core_event_id: Mapped[str] = mapped_column(ForeignKey("core_events.id"), unique=True); device_id: Mapped[str] = mapped_column(ForeignKey("dim_devices.id")); source_system: Mapped[str] = mapped_column(String(50), default="mqtt")
class RawDataDetail(UUIDMixin, Base):
    __tablename__ = "raw_data_details"
    raw_header_id: Mapped[str] = mapped_column(ForeignKey("raw_data_headers.id"), index=True); sensor_id: Mapped[str | None] = mapped_column(ForeignKey("dim_sensors.id")); raw_value: Mapped[str] = mapped_column(Text); raw_unit: Mapped[str] = mapped_column(String(20), default=""); raw_payload: Mapped[dict] = mapped_column(JSON, default=dict); received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
class TelemetryHeader(UUIDMixin, Base):
    __tablename__ = "telemetry_headers"
    core_event_id: Mapped[str] = mapped_column(ForeignKey("core_events.id"), unique=True); device_id: Mapped[str] = mapped_column(ForeignKey("dim_devices.id"), index=True); processing_status: Mapped[str] = mapped_column(String(30), default="clean"); processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
class TelemetryDetail(UUIDMixin, Base):
    __tablename__ = "telemetry_details"; __table_args__ = (UniqueConstraint("telemetry_header_id", "measurement_type", "measurement_timestamp"),)
    telemetry_header_id: Mapped[str] = mapped_column(ForeignKey("telemetry_headers.id"), index=True); sensor_id: Mapped[str | None] = mapped_column(ForeignKey("dim_sensors.id")); measurement_type: Mapped[str] = mapped_column(String(50)); value_numeric: Mapped[float | None] = mapped_column(Float); value_text: Mapped[str | None] = mapped_column(String(100)); unit: Mapped[str] = mapped_column(String(20), default=""); quality_status: Mapped[str] = mapped_column(String(30), default="valid"); measurement_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True, index=True)
class AIAnalysisHeader(UUIDMixin, Base):
    __tablename__ = "ai_analysis_headers"
    core_event_id: Mapped[str] = mapped_column(ForeignKey("core_events.id"), index=True); telemetry_header_id: Mapped[str | None] = mapped_column(ForeignKey("telemetry_headers.id")); model_name: Mapped[str] = mapped_column(String(100)); model_version: Mapped[str] = mapped_column(String(30), default="1.0"); analysis_status: Mapped[str] = mapped_column(String(30), default="complete"); analysis_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

def analysis_table(name: str):
    return type(name, (UUIDMixin, Base), {"__tablename__": name, "ai_analysis_id": mapped_column(ForeignKey("ai_analysis_headers.id"), index=True), "result": mapped_column(JSON, default=dict)})
class AIPrediction(UUIDMixin, Base):
    __tablename__="ai_predictions"; ai_analysis_id: Mapped[str]=mapped_column(ForeignKey("ai_analysis_headers.id")); result: Mapped[dict]=mapped_column(JSON, default=dict)
class AIAnomaly(UUIDMixin, Base):
    __tablename__="ai_anomalies"; ai_analysis_id: Mapped[str]=mapped_column(ForeignKey("ai_analysis_headers.id")); result: Mapped[dict]=mapped_column(JSON, default=dict)
class AIRiskScore(UUIDMixin, Base):
    __tablename__="ai_risk_scores"; ai_analysis_id: Mapped[str]=mapped_column(ForeignKey("ai_analysis_headers.id")); result: Mapped[dict]=mapped_column(JSON, default=dict)
class AIExplanation(UUIDMixin, Base):
    __tablename__="ai_explanations"; ai_analysis_id: Mapped[str]=mapped_column(ForeignKey("ai_analysis_headers.id")); result: Mapped[dict]=mapped_column(JSON, default=dict)
class AlertHeader(UUIDMixin, Base):
    __tablename__="alert_headers"; core_event_id: Mapped[str]=mapped_column(ForeignKey("core_events.id")); ai_analysis_id: Mapped[str|None]=mapped_column(ForeignKey("ai_analysis_headers.id")); alert_type: Mapped[str]=mapped_column(String(60)); severity: Mapped[str]=mapped_column(String(30)); status: Mapped[str]=mapped_column(String(30), default="open"); created_by: Mapped[str]=mapped_column(String(80), default="system")
class AlertDetail(UUIDMixin, Base):
    __tablename__="alert_details"; alert_id: Mapped[str]=mapped_column(ForeignKey("alert_headers.id"), index=True); trigger_type: Mapped[str]=mapped_column(String(50)); trigger_value: Mapped[float|None]=mapped_column(Float); threshold_value: Mapped[float|None]=mapped_column(Float); message: Mapped[str]=mapped_column(Text); priority: Mapped[str]=mapped_column(String(30)); recommendation: Mapped[str]=mapped_column(Text, default="")
class IncidentHeader(UUIDMixin, Base):
    __tablename__="incident_headers"; core_event_id: Mapped[str]=mapped_column(ForeignKey("core_events.id")); alert_id: Mapped[str]=mapped_column(ForeignKey("alert_headers.id")); assigned_user_id: Mapped[str|None]=mapped_column(ForeignKey("dim_users.id")); status: Mapped[str]=mapped_column(String(30), default="open"); severity: Mapped[str]=mapped_column(String(30)); priority: Mapped[str]=mapped_column(String(30)); acknowledged_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); resolved_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
class IncidentDetail(UUIDMixin, Base):
    __tablename__="incident_details"; incident_id: Mapped[str]=mapped_column(ForeignKey("incident_headers.id"), index=True); action_type: Mapped[str]=mapped_column(String(60)); action_description: Mapped[str]=mapped_column(Text); note: Mapped[str]=mapped_column(Text, default=""); action_timestamp: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now); resolution_note: Mapped[str]=mapped_column(Text, default="")
class NotificationHeader(UUIDMixin, Base):
    __tablename__="notification_headers"; core_event_id: Mapped[str]=mapped_column(ForeignKey("core_events.id")); alert_id: Mapped[str|None]=mapped_column(ForeignKey("alert_headers.id")); incident_id: Mapped[str|None]=mapped_column(ForeignKey("incident_headers.id")); notification_type: Mapped[str]=mapped_column(String(30)); channel: Mapped[str]=mapped_column(String(30)); status: Mapped[str]=mapped_column(String(30), default="queued")
class NotificationDetail(UUIDMixin, Base):
    __tablename__="notification_details"; notification_id: Mapped[str]=mapped_column(ForeignKey("notification_headers.id"), index=True); recipient: Mapped[str]=mapped_column(String(255)); subject: Mapped[str]=mapped_column(String(255)); message: Mapped[str]=mapped_column(Text); sent_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); delivered_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); failure_reason: Mapped[str]=mapped_column(Text, default="")
class IntegrationHeader(UUIDMixin, Base):
    __tablename__="integration_headers"; core_event_id: Mapped[str]=mapped_column(ForeignKey("core_events.id")); incident_id: Mapped[str|None]=mapped_column(ForeignKey("incident_headers.id")); source_system: Mapped[str]=mapped_column(String(50)); integration_type: Mapped[str]=mapped_column(String(50)); status: Mapped[str]=mapped_column(String(30), default="pending")
class IntegrationDetail(UUIDMixin, Base):
    __tablename__="integration_details"; integration_id: Mapped[str]=mapped_column(ForeignKey("integration_headers.id"), index=True); external_reference: Mapped[str]=mapped_column(String(255), default=""); request_payload: Mapped[dict]=mapped_column(JSON, default=dict); response_payload: Mapped[dict]=mapped_column(JSON, default=dict); response_status: Mapped[int|None]=mapped_column(Integer); processed_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); error_message: Mapped[str]=mapped_column(Text, default="")
class AuditHeader(UUIDMixin, Base):
    __tablename__="audit_headers"; core_event_id: Mapped[str|None]=mapped_column(ForeignKey("core_events.id")); user_id: Mapped[str|None]=mapped_column(ForeignKey("dim_users.id")); entity_type: Mapped[str]=mapped_column(String(60)); action_type: Mapped[str]=mapped_column(String(60))
class AuditDetail(UUIDMixin, Base):
    __tablename__="audit_details"; audit_id: Mapped[str]=mapped_column(ForeignKey("audit_headers.id"), index=True); old_value: Mapped[dict]=mapped_column(JSON, default=dict); new_value: Mapped[dict]=mapped_column(JSON, default=dict); change_description: Mapped[str]=mapped_column(Text, default=""); ip_address: Mapped[str]=mapped_column(String(60), default="")

# The centralized header/detail slide enumerates 32 names while the multilayer slide
# explicitly specifies 37. These five operational/configuration tables reconcile both.
class DeviceCredential(UUIDMixin, Base):
    __tablename__="device_credentials"; device_id: Mapped[str]=mapped_column(ForeignKey("dim_devices.id"), unique=True); credential_type: Mapped[str]=mapped_column(String(30), default="certificate"); secret_reference: Mapped[str]=mapped_column(String(255)); expires_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); is_active: Mapped[bool]=mapped_column(Boolean, default=True)
class SensorCalibration(UUIDMixin, Base):
    __tablename__="sensor_calibrations"; sensor_id: Mapped[str]=mapped_column(ForeignKey("dim_sensors.id"), index=True); offset: Mapped[float]=mapped_column(Float, default=0); scale: Mapped[float]=mapped_column(Float, default=1); calibrated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now); notes: Mapped[str]=mapped_column(Text, default="")
class DeviceHealth(UUIDMixin, Base):
    __tablename__="device_health"; device_id: Mapped[str]=mapped_column(ForeignKey("dim_devices.id"), index=True); status: Mapped[str]=mapped_column(String(30)); rssi: Mapped[int|None]=mapped_column(Integer); uptime_seconds: Mapped[int|None]=mapped_column(Integer); recorded_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now, index=True)
class ThresholdRule(UUIDMixin, Base):
    __tablename__="threshold_rules"; organization_id: Mapped[str]=mapped_column(ForeignKey("dim_organizations.id"), index=True); measurement_type: Mapped[str]=mapped_column(String(50)); operator: Mapped[str]=mapped_column(String(10)); threshold: Mapped[float]=mapped_column(Float); severity: Mapped[str]=mapped_column(String(30), default="warning"); enabled: Mapped[bool]=mapped_column(Boolean, default=True)
class SystemConfiguration(UUIDMixin, Base):
    __tablename__="system_configurations"; organization_id: Mapped[str]=mapped_column(ForeignKey("dim_organizations.id"), index=True); key: Mapped[str]=mapped_column(String(100)); value: Mapped[dict]=mapped_column(JSON, default=dict); is_secret_reference: Mapped[bool]=mapped_column(Boolean, default=False)

# Version 2.0: governed operations agent and predictive evidence.
class AgentConversation(UUIDMixin, Base):
    __tablename__="agent_conversations"; organization_id: Mapped[str]=mapped_column(ForeignKey("dim_organizations.id"), index=True); user_id: Mapped[str]=mapped_column(ForeignKey("dim_users.id"), index=True); title: Mapped[str]=mapped_column(String(180), default="Operations conversation"); status: Mapped[str]=mapped_column(String(30), default="active")
class AgentMessage(UUIDMixin, Base):
    __tablename__="agent_messages"; conversation_id: Mapped[str]=mapped_column(ForeignKey("agent_conversations.id"), index=True); role: Mapped[str]=mapped_column(String(20)); content: Mapped[str]=mapped_column(Text); evidence: Mapped[list]=mapped_column(JSON, default=list); confidence: Mapped[float]=mapped_column(Float, default=0)
class AgentAction(UUIDMixin, Base):
    __tablename__="agent_actions"; organization_id: Mapped[str]=mapped_column(ForeignKey("dim_organizations.id"), index=True); incident_id: Mapped[str|None]=mapped_column(ForeignKey("incident_headers.id")); action_type: Mapped[str]=mapped_column(String(80)); risk_level: Mapped[str]=mapped_column(String(10), default="L1"); status: Mapped[str]=mapped_column(String(30), default="proposed"); requires_approval: Mapped[bool]=mapped_column(Boolean, default=False); rationale: Mapped[str]=mapped_column(Text, default=""); execution_log: Mapped[list]=mapped_column(JSON, default=list); requested_by: Mapped[str]=mapped_column(String(36)); approved_by: Mapped[str|None]=mapped_column(String(36)); completed_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
class KnowledgeDocument(UUIDMixin, Base):
    __tablename__="knowledge_documents"; organization_id: Mapped[str]=mapped_column(ForeignKey("dim_organizations.id"), index=True); title: Mapped[str]=mapped_column(String(180)); category: Mapped[str]=mapped_column(String(60), default="runbook"); content: Mapped[str]=mapped_column(Text); version: Mapped[str]=mapped_column(String(30), default="1.0"); is_active: Mapped[bool]=mapped_column(Boolean, default=True)
class SensorIntelligence(UUIDMixin, Base):
    __tablename__="sensor_intelligence"; organization_id: Mapped[str]=mapped_column(ForeignKey("dim_organizations.id"), index=True); device_id: Mapped[str|None]=mapped_column(ForeignKey("dim_devices.id")); measurement_type: Mapped[str]=mapped_column(String(50), index=True); current_value: Mapped[float|None]=mapped_column(Float); forecast_value: Mapped[float|None]=mapped_column(Float); anomaly_score: Mapped[float]=mapped_column(Float, default=0); trust_score: Mapped[float]=mapped_column(Float, default=0); status: Mapped[str]=mapped_column(String(30), default="learning"); explanation: Mapped[str]=mapped_column(Text, default=""); evidence: Mapped[dict]=mapped_column(JSON, default=dict)
