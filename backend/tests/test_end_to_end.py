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
