from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class Token(ORMModel):
    access_token: str; token_type: str = "bearer"

class OrganizationCreate(ORMModel):
    name: str; subscription_plan: str = "demo"
class SiteCreate(ORMModel):
    organization_id: str; name: str; location: str = ""
class RoomCreate(ORMModel):
    site_id: str; name: str; floor: str = ""
class DeviceCreate(ORMModel):
    room_id: str; name: str; hardware_type: str = "Arduino UNO R4 WiFi"; firmware_version: str = "sim-1.0"
class SensorCreate(ORMModel):
    device_id: str; sensor_type: str; unit: str = ""; min_valid: float | None = None; max_valid: float | None = None
class ComponentRegistration(ORMModel):
    sensor_type: str
    quantity: int = Field(1, ge=1, le=10)
class DeviceRegistration(ORMModel):
    name: str = Field(min_length=2, max_length=150)
    hardware_type: str = "ESP32 WiFi"
    firmware_version: str = "not-connected"
    room_id: str | None = None
    sensor_types: list[str] = Field(default_factory=lambda: ["temperature", "humidity"])
class UserCreate(ORMModel):
    organization_id: str; email: EmailStr; full_name: str; password: str = Field(min_length=8); role_name: str = "viewer"

class TelemetryIn(ORMModel):
    device_id: str
    timestamp: datetime | None = None
    readings: dict[str, float | str | bool]
    health: dict[str, Any] = Field(default_factory=dict)
    sources: dict[str, dict[str, Any]] = Field(default_factory=dict)

    @field_validator("readings")
    @classmethod
    def validate_readings(cls, readings: dict[str, float | str | bool]):
        allowed = {"temperature", "humidity", "water_leak", "door_open", "smoke"}
        unknown = sorted(set(readings) - allowed)
        if unknown:
            raise ValueError(f"Unknown sensor field(s): {', '.join(unknown)}")
        if not readings:
            raise ValueError("At least one sensor reading is required")
        limits = {
            "temperature": (-20.0, 100.0), "humidity": (0.0, 100.0),
            "water_leak": (0.0, 1.0), "door_open": (0.0, 1.0), "smoke": (0.0, 1.0),
        }
        normalized = {}
        for name, value in readings.items():
            if isinstance(value, str):
                try:
                    value = float(value)
                except ValueError as exc:
                    raise ValueError(f"{name} must be numeric or boolean") from exc
            numeric = float(value)
            low, high = limits[name]
            if not low <= numeric <= high:
                raise ValueError(f"{name} must be between {low:g} and {high:g}")
            if name in {"water_leak", "door_open", "smoke"} and numeric not in {0.0, 1.0}:
                raise ValueError(f"{name} must be 0/1 or false/true")
            normalized[name] = int(numeric) if name in {"water_leak", "door_open", "smoke"} else numeric
        return normalized

class IncidentUpdate(ORMModel):
    action: str = Field(pattern="^(acknowledge|assign|resolve|close)$")
    assigned_user_id: str | None = None
    note: str = ""

class ThresholdRuleIn(ORMModel):
    measurement_type: str
    operator: str = Field(pattern="^(gt|gte|lt|lte|eq)$")
    threshold: float
    severity: str = "warning"
    enabled: bool = True
    mode: str = Field(default="manual", pattern="^(manual|auto)$")

class IntegrationRequest(ORMModel):
    provider: str = Field(pattern="^(teams|jira|servicenow|webhook)$")
    incident_id: str
    target_url: str | None = None



