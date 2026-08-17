from fastapi.testclient import TestClient
import api
import json
import pytest


class PublishResult:
    rc = 0
    mid = 42
    def wait_for_publish(self, timeout=5): return True


class FakeMQTT:
    def publish(self, topic, payload, qos):
        assert topic.startswith("devices/") and topic.endswith("/telemetry")
        assert qos == 1 and '"readings"' in payload and '"temperature"' in payload
        return PublishResult()


def test_health_and_mqtt_publish(monkeypatch):
    monkeypatch.setattr(api, "client", FakeMQTT())
    monkeypatch.setattr(api, "connect", lambda: None)
    client = TestClient(api.app)
    response = client.post("/publish", json={"readings":{"temperature":25,"humidity":48,"water_leak":0,"door_open":1,"smoke":0},"board":"ESP32 DevKit V1"})
    assert response.status_code == 200
    assert response.json()["status"] == "published"
    assert "mqtt-worker" in response.json()["next_stage"]


def test_invalid_sensor_value_is_rejected():
    client = TestClient(api.app)
    response = client.post("/publish", json={"readings":{"temperature":25,"humidity":48,"water_leak":0,"door_open":2,"smoke":0},"board":"ESP32 DevKit V1"})
    assert response.status_code == 422

@pytest.mark.parametrize("readings",[
    {"temperature":24,"humidity":48,"water_leak":0,"door_open":0,"smoke":0},
    {"temperature":36,"humidity":55,"water_leak":0,"door_open":0,"smoke":0},
    {"temperature":27,"humidity":86,"water_leak":1,"door_open":0,"smoke":0},
    {"temperature":25,"humidity":48,"water_leak":0,"door_open":1,"smoke":0},
    {"temperature":44,"humidity":41,"water_leak":0,"door_open":0,"smoke":1},
    {"temperature":42,"humidity":88,"water_leak":1,"door_open":1,"smoke":1},
])
def test_every_lab_scenario_publishes(monkeypatch,readings):
    monkeypatch.setattr(api,"client",FakeMQTT());monkeypatch.setattr(api,"connect",lambda:None)
    response=TestClient(api.app).post("/publish",json={"readings":readings,"board":"ESP32 DevKit V1"})
    assert response.status_code==200 and response.json()["correlation_id"]

def test_processing_receipt_is_correlated():
    correlation="test-correlation"
    message=type("Message",(),{"payload":json.dumps({"status":"complete","correlation_id":correlation,"database":"committed","alerts_created":1,"ai_status":"complete"}).encode()})()
    api.on_message(None,None,message)
    response=TestClient(api.app).get(f"/receipts/{correlation}")
    assert response.json()["database"]=="committed" and response.json()["ai_status"]=="complete"
