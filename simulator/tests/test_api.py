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

def test_component_configuration_is_retained(monkeypatch):
    published = {}
    class ConfigMQTT:
        def publish(self, topic, payload, qos, retain=False):
            published.update(topic=topic, payload=json.loads(payload), qos=qos, retain=retain)
            return PublishResult()
    monkeypatch.setattr(api, "client", ConfigMQTT())
    monkeypatch.setattr(api, "connect", lambda: None)
    response = TestClient(api.app).post("/components/configure", json={"components":{"door_open":{"mode":"simulated","simulated_value":1},"temperature":{"mode":"hardware"}}})
    assert response.status_code == 200
    assert published["topic"].endswith("/config/sources") and published["retain"] is True
    assert published["payload"]["components"]["door_open"]["mode"] == "simulated"

def test_hardware_packet_updates_presence():
    message=type("Message",(),{"topic":f"devices/{api.DEVICE_ID}/telemetry","payload":json.dumps({"timestamp":"2026-08-20T10:00:00+00:00","readings":{"temperature":25},"health":{"source":"esp32-hardware"}}).encode()})()
    api.on_message(None,None,message)
    assert api.state["latest_hardware_payload"]["health"]["source"] == "esp32-hardware"

def test_registry_lists_multiple_devices_and_routes_selected_topic(monkeypatch):
    second="00000000-0000-0000-0000-000000000202"
    monkeypatch.setattr(api,"registry",lambda:[
        {"id":api.DEVICE_ID,"name":"Primary","sensor_types":["temperature"],"hardware_online":False},
        {"id":second,"name":"Expansion","sensor_types":["humidity","water_leak"],"hardware_online":False},
    ])
    published={}
    class MultiMQTT:
        def publish(self,topic,payload,qos,retain=False):
            published.update(topic=topic,payload=json.loads(payload));return PublishResult()
    monkeypatch.setattr(api,"client",MultiMQTT());monkeypatch.setattr(api,"connect",lambda:None)
    client=TestClient(api.app)
    devices=client.get("/devices").json()
    assert len(devices)==2 and all(item["effective_mode"]=="simulated" for item in devices)
    response=client.post("/publish",json={"device_id":second,"readings":{"humidity":52,"water_leak":0},"board":"ESP32 DevKit V1"})
    assert response.status_code==200 and published["topic"]==f"devices/{second}/telemetry"
    assert published["payload"]["device_id"]==second
def test_component_level_hardware_presence_does_not_mark_simulated_door(monkeypatch):
    temperature_id="11111111-1111-1111-1111-111111111111"
    door_id="22222222-2222-2222-2222-222222222222"
    monkeypatch.setattr(api,"registry",lambda:[{"id":api.DEVICE_ID,"name":"Primary","sensor_types":["temperature","door_open"],"sensors":[{"id":temperature_id,"sensor_type":"temperature","label":"temperature sensor 1"},{"id":door_id,"sensor_type":"door_open","label":"door open sensor 1"}]}])
    message=type("Message",(),{"topic":f"devices/{api.DEVICE_ID}/telemetry","payload":json.dumps({"device_id":api.DEVICE_ID,"timestamp":"2026-08-20T10:00:00+00:00","readings":{"temperature":25,"door_open":0},"sources":{"temperature":{"mode":"hardware","provider":"esp32","sensor_id":temperature_id},"door_open":{"mode":"simulated","provider":"firmware-fallback","sensor_id":door_id}},"health":{"source":"esp32-hardware"}}).encode()})()
    api.on_message(None,None,message)
    device=TestClient(api.app).get("/devices").json()[0]
    assert temperature_id in device["hardware_sensor_ids"]
    assert door_id not in device["hardware_sensor_ids"]

def test_simulated_source_remains_hardware_capable_for_restore(monkeypatch):
    temperature_id="33333333-3333-3333-3333-333333333333"
    door_id="44444444-4444-4444-4444-444444444444"
    monkeypatch.setattr(api,"registry",lambda:[{"id":api.DEVICE_ID,"name":"Primary","sensor_types":["temperature","door_open"],"sensors":[{"id":temperature_id,"sensor_type":"temperature","label":"Temperature sensor 1"},{"id":door_id,"sensor_type":"door_open","label":"Door Open sensor 1"}]}])
    message=type("Message",(),{"topic":f"devices/{api.DEVICE_ID}/telemetry","payload":json.dumps({"device_id":api.DEVICE_ID,"timestamp":"2026-08-20T10:00:00+00:00","readings":{"temperature":35,"door_open":0},"sources":{"temperature":{"mode":"simulated","provider":"component-tester","sensor_id":temperature_id,"pin":4,"hardware_available":True},"door_open":{"mode":"simulated","provider":"component-tester","sensor_id":door_id,"pin":None,"hardware_available":False}},"health":{"source":"esp32-hardware"}}).encode()})()
    api.on_message(None,None,message)
    client=TestClient(api.app)
    device=client.get("/devices").json()[0]
    status=client.get(f"/status?device_id={api.DEVICE_ID}").json()
    assert temperature_id in device["hardware_sensor_ids"] and temperature_id in status["hardware_sensor_ids"]
    assert temperature_id not in device["active_hardware_sensor_ids"]
    assert door_id not in device["hardware_sensor_ids"]


def test_closed_loop_manual_cooling_changes_room_temperature():
    hot={**api.cooling_bucket("thermal-unit"),"mode":"manual","room_temperature_c":30.0,"ambient_temperature_c":30.0,"server_heat_kw":0.0,"cooling_power_percent":100.0}
    cooled=api.advance_cooling(hot,60)
    assert cooled["room_temperature_c"] < 30.0
    assert cooled["trend_c_per_min"] < 0
    uncooled=api.advance_cooling({**hot,"mode":"off"},60)
    assert uncooled["room_temperature_c"] >= 30.0


def test_ai_auto_controller_increases_output_for_hot_room_and_reduces_for_cold_room():
    hot={**api.cooling_bucket("auto-hot"),"mode":"auto","room_temperature_c":34.0,"ambient_temperature_c":38.0,"server_heat_kw":20.0,"cooling_power_percent":10.0}
    cooled=api.advance_cooling(hot,60)
    assert cooled["cooling_power_percent"] > 10
    cold={**api.cooling_bucket("auto-cold"),"mode":"auto","room_temperature_c":14.0,"ambient_temperature_c":16.0,"server_heat_kw":0.0,"cooling_power_percent":90.0}
    protected=api.advance_cooling(cold,60)
    assert protected["cooling_power_percent"] < 90
    assert protected["status"] == "critical_cold"


def test_cooling_step_publishes_modeled_temperature_to_real_pipeline(monkeypatch):
    published={}
    class CoolingMQTT:
        def publish(self,topic,payload,qos,retain=False):
            published.update(topic=topic,payload=json.loads(payload),qos=qos)
            return PublishResult()
    monkeypatch.setattr(api,"client",CoolingMQTT());monkeypatch.setattr(api,"connect",lambda:None)
    response=TestClient(api.app).post("/cooling/step",json={"device_id":api.DEVICE_ID,"seconds":60,"publish":True})
    assert response.status_code==200
    assert response.json()["next_stage"].startswith("MQTT")
    assert published["payload"]["sources"]["temperature"]["provider"]=="hvac-thermal-model"
    assert published["payload"]["health"]["cooling"]["thermal_status"] in {"safe","too_hot","critical_hot","too_cold","critical_cold"}
    assert isinstance(published["payload"]["readings"]["temperature"],float)