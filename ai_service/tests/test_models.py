from models import anomaly, explain, forecast, learn_baseline, risk_score
from fastapi.testclient import TestClient
from app import app

def test_anomaly_and_risk():
    base=learn_baseline([23,24,23.5,24])
    assert anomaly([23,24,40],base)["is_anomaly"]
    assert risk_score({"temperature":40,"water_leak":1},1)["level"] in {"high","critical"}

def test_forecast(): assert len(forecast([1,2,3,4],3)["forecast"]) == 3

def test_door_open_affects_risk_and_explanation():
    readings={"temperature":24,"humidity":48,"water_leak":0,"door_open":1,"smoke":0}
    risk=risk_score(readings,0)
    text=explain(readings,{"is_anomaly":False,"anomaly_score":0},risk)
    assert risk["score"] > 0
    assert "door open" in text.lower()

def test_ai_terminal_and_self_test():
    client = TestClient(app)
    result = client.post("/self-test").json()
    assert result["status"] == "passed"
    assert result["result"]["run_id"]
    assert result["result"]["precautions"]
    status = client.get("/status").json()
    assert status["status"] == "healthy"
    assert len(status["models"]) == 5
    assert all(model["runs"] >= 1 for model in status["models"])
    run_logs = [log for log in status["logs"] if log["run_id"] == result["result"]["run_id"]]
    assert any(log["event"] == "pipeline_started" for log in run_logs)
    assert any(log["event"] == "pipeline_completed" for log in run_logs)

def test_emergency_precautions_are_returned():
    client = TestClient(app)
    response = client.post("/analyze", json={
        "history": {"temperature": [24, 24.2, 24.1, 44]},
        "readings": {"temperature": 44, "humidity": 45, "smoke": 1, "water_leak": 0},
        "horizon": 5,
    })
    assert response.status_code == 200
    result = response.json()
    assert result["risk"]["level"] in {"high", "critical"}
    assert any(item["priority"] == "emergency" for item in result["precautions"])
