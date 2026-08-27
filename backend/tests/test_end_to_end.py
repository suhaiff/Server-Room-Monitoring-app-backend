from app.seed import DEVICE
from app import models
from app.core.database import SessionLocal
from app.services.platform_faults import process_platform_fault

def test_health(client):
    assert client.get("/health").json()["status"] == "healthy"

def test_auth_and_ingestion_flow(client, token):
    payload={"device_id":DEVICE,"readings":{"temperature":35.2,"humidity":55,"water_leak":0,"door_open":0,"smoke":0}}
    response=client.post("/api/v1/telemetry/ingest", json=payload)
    assert response.status_code == 200 and response.json()["accepted"] == 5
    headers={"Authorization":f"Bearer {token}"}
    assert client.get("/api/v1/telemetry/latest",headers=headers).status_code == 200
    summary=client.get("/api/v1/reports/summary",headers=headers).json()
    assert summary["telemetry_points"] >= 5

def test_rbac_requires_token(client):
    assert client.get("/api/v1/incidents").status_code == 401
    assert client.get("/api/v1/devices").status_code == 401

def test_protected_devices_endpoint_exists(client, token):
    response = client.get("/api/v1/devices", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert any(device["id"] == DEVICE for device in response.json())

def test_unknown_device_and_invalid_payload_are_rejected(client, token):
    headers={"Authorization":f"Bearer {token}"}
    unknown=client.post("/api/v1/telemetry/ingest",json={"device_id":"00000000-0000-0000-0000-999999999999","readings":{"temperature":24}})
    assert unknown.status_code == 404
    invalid=client.post("/api/v1/telemetry/ingest",json={"device_id":DEVICE,"readings":{"unknown_probe":1}})
    assert invalid.status_code == 422
    invalid_range=client.post("/api/v1/telemetry/ingest",json={"device_id":DEVICE,"readings":{"humidity":140}})
    assert invalid_range.status_code == 422

def test_door_event_creates_enriched_alert(client, token):
    headers={"Authorization":f"Bearer {token}"}
    response=client.post("/api/v1/telemetry/ingest",json={"device_id":DEVICE,"readings":{"temperature":24,"humidity":48,"water_leak":0,"door_open":1,"smoke":0}})
    assert response.status_code == 200
    assert response.json()["alerts_created"] == 1
    alerts=client.get("/api/v1/alerts",headers=headers).json()
    door=next(alert for alert in alerts if alert["core_event_id"]==response.json()["core_event_id"])
    assert door["alert_type"] == "door_open_threshold"
    assert "door is open" in door["message"].lower()
    assert door["event_timestamp"]

def test_ai_result_is_linked_to_core_event_and_alert(client, token, monkeypatch):
    headers={"Authorization":f"Bearer {token}"}
    event=client.post("/api/v1/telemetry/ingest",json={"device_id":DEVICE,"readings":{"temperature":24,"humidity":48,"water_leak":0,"door_open":0,"smoke":1}}).json()
    async def fake_ai(*args, **kwargs):
        return {"run_id":"test-run","model_version":"test-2.0","total_latency_ms":1.0,"baseline":{"mean":24,"std":0.1},"prediction":{"trend":"stable","forecast":[24]},"anomaly":{"is_anomaly":False,"anomaly_score":0,"z_score":0},"risk":{"score":10,"level":"low"},"explanation":"Door event detected.","precautions":[{"priority":"medium","action":"Verify access","automation":"security_check_recommended"}]}
    monkeypatch.setattr("app.modules.ai._ai_request",fake_ai)
    analyzed=client.post("/api/v1/ai/analyze",headers=headers,json={"core_event_id":event["core_event_id"],"telemetry_header_id":event["telemetry_header_id"],"history":{"temperature":[24,24,24,24]},"readings":{"temperature":24,"humidity":48,"water_leak":0,"door_open":0,"smoke":1}})
    assert analyzed.status_code == 200
    with SessionLocal() as db:
        header=db.get(models.AIAnalysisHeader,analyzed.json()["ai_analysis_id"])
        alert=db.query(models.AlertHeader).filter_by(core_event_id=event["core_event_id"]).one()
        assert header.core_event_id == event["core_event_id"]
        assert alert.ai_analysis_id == header.id

def test_dashboard_has_no_direct_simulator_endpoint(client, token):
    response = client.post("/api/v1/telemetry/simulate", headers={"Authorization": f"Bearer {token}"}, json={"device_id": DEVICE, "readings": {"temperature": 24}})
    assert response.status_code == 404

def test_ticket_can_be_closed_and_health_returns_to_normal(client, token):
    headers={"Authorization":f"Bearer {token}"}
    client.post("/api/v1/telemetry/ingest",json={"device_id":DEVICE,"readings":{"temperature":24,"humidity":48,"water_leak":0,"door_open":0,"smoke":0}})
    event=client.post("/api/v1/telemetry/ingest",json={"device_id":DEVICE,"readings":{"temperature":24,"humidity":48,"water_leak":1,"door_open":0,"smoke":0}}).json()
    ticket=next(x for x in client.get("/api/v1/incidents",headers=headers).json() if x["core_event_id"]==event["core_event_id"])
    assert any(item["action_type"] == "threshold_breach_recorded" for item in ticket["history"])
    closed=client.patch(f"/api/v1/incidents/{ticket['id']}",headers=headers,json={"action":"close","note":"Verified and handled"})
    assert closed.status_code==200 and closed.json()["status"]=="closed"
    updated=next(x for x in client.get("/api/v1/incidents",headers=headers).json() if x["id"]==ticket["id"])
    assert [item["action_type"] for item in updated["history"]][-1] == "close"
    assert updated["history"][-1]["note"] == "Verified and handled"
    alert=next(x for x in client.get("/api/v1/alerts",headers=headers).json() if x["id"]==ticket["alert_id"])
    assert alert["status"]=="closed"

def test_admin_can_clear_test_history(client, token):
    headers={"Authorization":f"Bearer {token}"}
    response=client.post("/api/v1/admin/test-data/reset",headers=headers)
    assert response.status_code==200 and response.json()["deleted_rows"]>0
    summary=client.get("/api/v1/reports/summary",headers=headers).json()
    assert summary["telemetry_points"]==0 and summary["open_alerts"]==0 and summary["open_incidents"]==0
    assert summary["system_state"]=="healthy"

def test_normalized_condition_keeps_ticket_for_operator(client, token):
    headers={"Authorization":f"Bearer {token}"}
    client.post("/api/v1/admin/test-data/reset",headers=headers)
    raised=client.post("/api/v1/telemetry/ingest",json={"device_id":DEVICE,"readings":{"door_open":1}}).json()
    ticket=next(x for x in client.get("/api/v1/incidents",headers=headers).json() if x["core_event_id"]==raised["core_event_id"])
    client.post("/api/v1/telemetry/ingest",json={"device_id":DEVICE,"readings":{"door_open":0}})
    summary=client.get("/api/v1/reports/summary",headers=headers).json()
    assert summary["open_alerts"] == 0
    assert summary["open_incidents"] == 1
    assert summary["system_state"] == "pending"
    updated=next(x for x in client.get("/api/v1/incidents",headers=headers).json() if x["id"]==ticket["id"])
    assert updated["status"] == "open"
    assert updated["history"][-1]["action_type"] == "condition_normalized"

def test_software_fault_creates_and_recovers_real_ticket(client, token):
    headers={"Authorization":f"Bearer {token}"}
    client.post("/api/v1/admin/test-data/reset",headers=headers)
    with SessionLocal() as db:
        created=process_platform_fault(db,{"component":"ai","label":"AI anomaly models","severity":"critical","action":"trigger"})
    assert created["status"] == "fault_recorded" and created["alerts_created"] == 1
    ticket=next(x for x in client.get("/api/v1/incidents",headers=headers).json() if x["id"]==created["incident_ids"][0])
    assert ticket["device_name"] == "Platform Services"
    assert ticket["alert_type"] == "software_ai"
    with SessionLocal() as db:
        recovered=process_platform_fault(db,{"component":"ai","label":"AI anomaly models","action":"recover"})
    assert recovered["status"] == "recovered_pending_verification"
    summary=client.get("/api/v1/reports/summary",headers=headers).json()
    assert summary["open_alerts"] == 0 and summary["open_incidents"] == 1

def test_l2_software_fault_is_automatically_repaired_and_closed(client, token):
    headers={"Authorization":f"Bearer {token}"}
    client.post("/api/v1/admin/test-data/reset",headers=headers)
    with SessionLocal() as db:
        created=process_platform_fault(db,{"component":"redis","label":"Redis cache","action":"trigger"})
    assert created["level"]=="L1" and created["automatic"] is True
    with SessionLocal() as db:
        recovered=process_platform_fault(db,{"component":"redis","label":"Redis cache","action":"recover","automatic":True})
    assert recovered["status"]=="auto_remediated"
    ticket=next(x for x in client.get("/api/v1/incidents",headers=headers).json() if x["id"]==created["incident_ids"][0])
    assert ticket["status"]=="closed"
    assert ticket["history"][-1]["action_type"]=="ai_verified_recovery"
    assert "automatically closed" in ticket["history"][-1]["description"]
    alert=next(x for x in client.get("/api/v1/alerts",headers=headers).json() if x["id"]==created["alert_id"])
    assert alert["incident_id"]==ticket["id"] and alert["incident_status"]=="closed"
    assert [step["action_type"] for step in alert["history"]]==["software_fault_injected","ai_root_cause_identified","ai_remediation_started","ai_verified_recovery"]


def test_l3_fault_cannot_bypass_human_approval(client, token):
    headers={"Authorization":f"Bearer {token}"}
    client.post("/api/v1/admin/test-data/reset",headers=headers)
    with SessionLocal() as db:
        created=process_platform_fault(db,{"component":"postgres","label":"PostgreSQL","action":"trigger"})
        recovered=process_platform_fault(db,{"component":"postgres","label":"PostgreSQL","action":"recover","automatic":True})
    assert created["level"]=="L3" and created["automatic"] is False
    assert recovered["status"]=="recovered_pending_verification" and recovered["automatic"] is False
    ticket=next(x for x in client.get("/api/v1/incidents",headers=headers).json() if x["id"]==created["incident_ids"][0])
    assert ticket["status"]=="open"

def test_named_ai_fault_is_visible_in_ai_operations(client, token, monkeypatch):
    headers={"Authorization":f"Bearer {token}"}
    client.post("/api/v1/admin/test-data/reset",headers=headers)
    with SessionLocal() as db:
        process_platform_fault(db,{"component":"ai_anomaly","label":"AI anomaly detector","severity":"critical","action":"trigger","message":"Simulated AI anomaly-detection model failure"})
    async def fake_status(*args, **kwargs):
        return {"status":"healthy","version":"test","models":[{"name":name,"status":"healthy","runs":2,"errors":0} for name in ["baseline","anomaly","forecast","risk","explanation"]],"logs":[]}
    monkeypatch.setattr("app.modules.ai._ai_request",fake_status)
    response=client.get("/api/v1/ai/status",headers=headers)
    assert response.status_code == 200
    data=response.json()
    assert data["status"] == "degraded" and data["active_fault_tests"] == 1
    assert next(model for model in data["models"] if model["name"]=="anomaly")["status"] == "error"
    assert all(next(model for model in data["models"] if model["name"]==name)["status"] == "blocked" for name in ["forecast","risk","explanation"])
    assert data["logs"][0]["component"] == "anomaly"

def test_risk_failure_holds_dependent_explanation_stage(client, token, monkeypatch):
    headers={"Authorization":f"Bearer {token}"}
    client.post("/api/v1/admin/test-data/reset",headers=headers)
    with SessionLocal() as db:
        process_platform_fault(db,{"component":"ai_risk","label":"AI risk engine","severity":"critical","action":"trigger","message":"Simulated AI risk-scoring model failure"})
    async def fake_status(*args, **kwargs):
        return {"status":"healthy","version":"test","models":[{"name":name,"status":"healthy","runs":2,"errors":0} for name in ["baseline","anomaly","forecast","risk","explanation"]],"logs":[]}
    monkeypatch.setattr("app.modules.ai._ai_request",fake_status)
    data=client.get("/api/v1/ai/status",headers=headers).json()
    states={model["name"]:model for model in data["models"]}
    assert states["risk"]["status"] == "error"
    assert states["explanation"]["status"] == "blocked"
    assert states["explanation"]["blocked_by"] == "risk"
    assert all(states[name]["status"] == "healthy" for name in ["baseline","anomaly","forecast"])
    assert data["pipeline"] == {"mode":"linear","failed":["risk"],"blocked":["explanation"]}

def test_admin_can_download_single_csv_system_log(client, token):
    headers={"Authorization":f"Bearer {token}"}
    response=client.get("/api/v1/admin/logs/export",headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "vtab-sentinel-system-log-" in response.headers["content-disposition"]
    assert response.text.startswith("timestamp,category,source,severity,status,record_id,core_event_id,name,message,details")
    assert "AI risk engine" in response.text

def test_threshold_settings_and_automatic_recovery(client, token):
    headers={"Authorization":f"Bearer {token}"}
    client.post("/api/v1/admin/test-data/reset",headers=headers)
    rules=client.get("/api/v1/settings/thresholds",headers=headers)
    assert rules.status_code==200 and any(r["measurement_type"]=="humidity" for r in rules.json())
    saved=client.put("/api/v1/settings/thresholds/humidity",headers=headers,json={"measurement_type":"humidity","operator":"gt","threshold":85,"severity":"warning","enabled":True})
    assert saved.status_code==200 and saved.json()["threshold"]==85
    raised=client.post("/api/v1/telemetry/ingest",json={"device_id":DEVICE,"readings":{"humidity":90}}).json()
    ticket=next(x for x in client.get("/api/v1/incidents",headers=headers).json() if x["core_event_id"]==raised["core_event_id"])
    for _ in range(3):
        client.post("/api/v1/telemetry/ingest",json={"device_id":DEVICE,"readings":{"humidity":50}})
    updated=next(x for x in client.get("/api/v1/incidents",headers=headers).json() if x["id"]==ticket["id"])
    assert updated["status"]=="closed"
    assert updated["history"][-1]["action_type"]=="ai_verified_recovery"



def test_environmental_threshold_adapts_without_exceeding_safety_ceiling(client, token):
    headers={"Authorization":f"Bearer {token}"}
    client.post("/api/v1/admin/test-data/reset",headers=headers)
    manual=client.put("/api/v1/settings/thresholds/humidity",headers=headers,json={
        "measurement_type":"humidity","operator":"gt","threshold":70,"severity":"warning","enabled":True,"mode":"manual"})
    assert manual.status_code==200
    assert manual.json()["mode"]=="manual" and manual.json()["effective_threshold"]==70
    saved=client.put("/api/v1/settings/thresholds/humidity",headers=headers,json={
        "measurement_type":"humidity","operator":"gt","threshold":70,"severity":"warning","enabled":True,"mode":"auto"})
    assert saved.status_code==200 and saved.json()["mode"]=="auto"
    for second in range(1,11):
        response=client.post("/api/v1/telemetry/ingest",json={
            "device_id":DEVICE,
            "timestamp":f"2026-08-24T11:00:{second:02d}Z",
            "readings":{"humidity":77},
            "sources":{"humidity":{"mode":"simulated"}}})
        assert response.status_code==200
    rules=client.get("/api/v1/settings/thresholds",headers=headers).json()
    humidity=next(rule for rule in rules if rule["measurement_type"]=="humidity")
    assert humidity["configured_threshold"]==70
    assert humidity["mode"]=="auto"
    assert humidity["learning_status"]=="active"
    assert humidity["baseline"]==77
    assert humidity["effective_threshold"]==82
    assert humidity["hard_safety_ceiling"]==90
    assert client.get("/api/v1/reports/summary",headers=headers).json()["open_alerts"]==0
    critical=client.post("/api/v1/telemetry/ingest",json={
        "device_id":DEVICE,
        "timestamp":"2026-08-24T11:00:30Z",
        "readings":{"humidity":92},
        "sources":{"humidity":{"mode":"simulated"}}})
    assert critical.status_code==200
    alert=next(item for item in client.get("/api/v1/alerts",headers=headers).json() if item["core_event_id"]==critical.json()["core_event_id"])
    assert alert["severity"]=="critical"

def test_latest_telemetry_exposes_hardware_raw_adc(client, token):
    headers={"Authorization":f"Bearer {token}"}
    client.post("/api/v1/admin/test-data/reset",headers=headers)
    response=client.post("/api/v1/telemetry/ingest",json={
        "device_id":DEVICE,
        "readings":{"water_leak":1,"smoke":0},
        "sources":{"water_leak":{"mode":"hardware","provider":"esp32","raw":742,"pin":34},"smoke":{"mode":"hardware","provider":"esp32","raw":385,"pin":35}}
    })
    assert response.status_code==200
    rows=client.get("/api/v1/telemetry/latest?limit=10",headers=headers).json()
    water=next(row for row in rows if row["measurement_type"]=="water_leak")
    smoke=next(row for row in rows if row["measurement_type"]=="smoke")
    assert water["raw_adc"]==742 and water["source_mode"]=="hardware" and water["pin"]==34
    assert smoke["raw_adc"]==385 and smoke["pin"]==35

def test_multi_device_registration_defaults_to_simulation(client, token):
    headers={"Authorization":f"Bearer {token}"}
    response=client.post("/api/v1/devices/register",headers=headers,json={
        "name":"ESP32 Expansion Node","hardware_type":"ESP32-S3 DevKitC","sensor_types":["temperature","water_leak"]})
    assert response.status_code==200
    device=response.json()
    assert device["status"]=="offline" and device["effective_mode"]=="simulated"
    assert device["sensor_types"]==["temperature","water_leak"]
    registry=client.get("/api/v1/simulator/device-registry").json()
    registered=next(item for item in registry if item["id"]==device["id"])
    assert registered["hardware_online"] is False and registered["effective_mode"]=="simulated"
    ingested=client.post("/api/v1/telemetry/ingest",json={"device_id":device["id"],"readings":{"temperature":24,"water_leak":0},
        "sources":{"temperature":{"mode":"simulated"},"water_leak":{"mode":"simulated"}}})
    assert ingested.status_code==200
    rows=client.get(f"/api/v1/telemetry/latest?device_id={device['id']}&limit=10",headers=headers).json()
    assert rows and all(row["device_id"]==device["id"] for row in rows)


def test_diagnostics_reports_live_backlog_separately_from_history(client, token):
    headers={"Authorization":f"Bearer {token}"}
    data=client.get("/api/v1/system/diagnostics",headers=headers).json()["evidence"]
    assert "ai_processing_backlog" in data
    assert "historical_unlinked_telemetry" in data
    assert "telemetry_events_without_ai" not in data
def test_add_duplicate_component_to_existing_controller(client, token):
    headers={"Authorization":f"Bearer {token}"}
    registered=client.post("/api/v1/devices/register",headers=headers,json={"name":"Component Expansion Node","hardware_type":"ESP32-WROOM-32","sensor_types":["water_leak"]})
    assert registered.status_code==200
    device=registered.json()
    added=client.post(f"/api/v1/devices/{device['id']}/components",headers=headers,json={"sensor_type":"water_leak","quantity":1})
    assert added.status_code==200 and len(added.json()["created"])==1
    registry=client.get("/api/v1/simulator/device-registry").json()
    entry=next(item for item in registry if item["id"]==device["id"])
    water=[sensor for sensor in entry["sensors"] if sensor["sensor_type"]=="water_leak"]
    assert len(water)==2 and [sensor["label"] for sensor in water]==["Water Leak sensor 1","Water Leak sensor 2"]
    for index,sensor in enumerate(water):
        response=client.post("/api/v1/telemetry/ingest",json={"device_id":device["id"],"readings":{"water_leak":index},"sources":{"water_leak":{"mode":"simulated","sensor_id":sensor["id"]}}})
        assert response.status_code==200
    rows=client.get(f"/api/v1/telemetry/latest?device_id={device['id']}&limit=10",headers=headers).json()
    assert {row["sensor_id"] for row in rows if row["measurement_type"]=="water_leak"}=={sensor["id"] for sensor in water}


def test_controlled_software_fault_is_visible_in_dependency_diagnostics(client, token):
    headers={"Authorization":f"Bearer {token}"}
    client.post("/api/v1/admin/test-data/reset",headers=headers)
    with SessionLocal() as db:
        process_platform_fault(db,{"component":"redis","label":"Redis cache","action":"trigger"})
    data=client.get("/api/v1/system/diagnostics",headers=headers).json()
    redis=next(item for item in data["components"] if item["name"]=="Redis")
    assert redis["status"]=="error" and "CONTROLLED TEST ACTIVE" in redis["detail"]

# VTAB Sentinel 2.0 agent tests
def test_agent_chat_is_evidence_backed(client, token):
    headers={"Authorization":f"Bearer {token}"}
    response=client.post("/api/v1/agent/chat",headers=headers,json={"message":"Is the server room healthy?"})
    assert response.status_code==200
    data=response.json();assert data["conversation_id"] and data["evidence"] and data["confidence"]>=.9
    assert data["suggested_actions"] and data["suggested_actions"][0]["page"] in {"Incidents","AI Operations"}
    assert "open_alerts" in data["snapshot"]

def test_agent_governance_requires_approval_for_l2(client, token):
    headers={"Authorization":f"Bearer {token}"}
    made=client.post("/api/v1/agent/actions",headers=headers,json={"action_type":"restart_redis","risk_level":"L2","rationale":"Connectivity diagnostic"})
    assert made.status_code==200 and made.json()["status"]=="awaiting_approval"
    approved=client.post(f"/api/v1/agent/actions/{made.json()['id']}/approve",headers=headers)
    assert approved.status_code==200 and approved.json()["status"]=="verified"

def test_predictive_intelligence_and_digital_twin(client, token):
    headers={"Authorization":f"Bearer {token}"}
    intelligence=client.get("/api/v1/agent/intelligence",headers=headers)
    assert intelligence.status_code==200 and isinstance(intelligence.json(),list)
    twin=client.get("/api/v1/agent/digital-twin",headers=headers)
    assert twin.status_code==200 and "sites" in twin.json()

def test_agent_routes_are_protected(client):
    assert client.get("/api/v1/agent/overview").status_code==401

def test_environmental_control_deduplicates_and_verifies_recovery(client, token):
    headers={"Authorization":f"Bearer {token}"}
    client.post("/api/v1/admin/test-data/reset",headers=headers)
    for name,limit,severity in [("temperature",30,"critical"),("humidity",70,"warning")]:
        client.put(f"/api/v1/settings/thresholds/{name}",headers=headers,json={"measurement_type":name,"operator":"gt","threshold":limit,"severity":severity,"enabled":True})
    for second,temp,humidity in [(1,35,77),(2,36,78)]:
        response=client.post("/api/v1/telemetry/ingest",json={"device_id":DEVICE,"timestamp":f"2026-08-24T10:00:{second:02d}Z","readings":{"temperature":temp,"humidity":humidity},"sources":{"temperature":{"mode":"simulated"},"humidity":{"mode":"simulated"}}})
        assert response.status_code==200
    actions=client.get("/api/v1/agent/actions",headers=headers).json()
    climate=[a for a in actions if a["action_type"] in {"balance_cooling_setpoint","activate_dehumidification"}]
    assert len(climate)==2 and all(a["status"]=="monitoring" for a in climate)
    control=client.get("/api/v1/agent/climate-control",headers=headers).json()
    assert control["mode"]=="balancing" and control["target_temperature_c"]==22
    prediction=client.get("/api/v1/agent/intelligence",headers=headers).json()
    temperature=next(r for r in prediction if r["measurement_type"]=="temperature")
    assert temperature["threshold"]==30 and "forecast_breach" in temperature
    for second in (3,4,5):
        client.post("/api/v1/telemetry/ingest",json={"device_id":DEVICE,"timestamp":f"2026-08-24T10:00:{second:02d}Z","readings":{"temperature":22,"humidity":50}})
    actions=client.get("/api/v1/agent/actions",headers=headers).json()
    climate=[a for a in actions if a["action_type"] in {"balance_cooling_setpoint","activate_dehumidification"}]
    assert all(a["status"]=="verified" for a in climate)
    assert client.get("/api/v1/agent/climate-control",headers=headers).json()["mode"]=="standby"






def test_excessive_cooling_opens_critical_ticket_and_ai_verifies_recovery(client, token):
    headers={"Authorization":f"Bearer {token}"}
    client.post("/api/v1/admin/test-data/reset",headers=headers)
    raised=client.post("/api/v1/telemetry/ingest",json={"device_id":DEVICE,"readings":{"temperature":14},"health":{"source":"hvac-thermal-simulator"},"sources":{"temperature":{"mode":"simulated","provider":"hvac-thermal-model"}}})
    assert raised.status_code==200 and raised.json()["alerts_created"]==1
    alert=next(item for item in client.get("/api/v1/alerts",headers=headers).json() if item["core_event_id"]==raised.json()["core_event_id"])
    assert alert["alert_type"]=="temperature_low_threshold" and alert["severity"]=="critical"
    ticket=next(item for item in client.get("/api/v1/incidents",headers=headers).json() if item["alert_id"]==alert["id"])
    actions=client.get("/api/v1/agent/actions",headers=headers).json()
    action=next(item for item in actions if item["incident_id"]==ticket["id"])
    assert action["action_type"]=="reduce_cooling_output" and action["status"]=="monitoring"
    for _ in range(3):
        client.post("/api/v1/telemetry/ingest",json={"device_id":DEVICE,"readings":{"temperature":22},"sources":{"temperature":{"mode":"simulated","provider":"hvac-thermal-model"}}})
    updated=next(item for item in client.get("/api/v1/incidents",headers=headers).json() if item["id"]==ticket["id"])
    assert updated["status"]=="closed" and updated["history"][-1]["action_type"]=="ai_verified_recovery"
    action=next(item for item in client.get("/api/v1/agent/actions",headers=headers).json() if item["id"]==action["id"])
    assert action["status"]=="verified"


def test_climate_control_exposes_complete_temperature_safe_band(client, token):
    headers={"Authorization":f"Bearer {token}"}
    response=client.get("/api/v1/agent/climate-control",headers=headers)
    assert response.status_code==200
    policy=response.json()["temperature_policy"]
    assert policy["critical_minimum_c"]==15 and policy["minimum_c"]>=18
    assert policy["maximum_c"]<=policy["critical_maximum_c"]
    assert response.json()["simulated_hvac_available"] is True