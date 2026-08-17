"""Long-running MQTT consumer. Topic: devices/{device_uuid}/telemetry."""
import json, logging, time
from datetime import datetime, timezone
import paho.mqtt.client as mqtt
from app.core.config import settings
from app.core.database import SessionLocal
from app.schemas import TelemetryIn
from app.services.alerts import evaluate
from app.services.telemetry import ingest
from app.services.ai_pipeline import analyze_and_persist
from app.services.platform_faults import process_platform_fault

logging.basicConfig(level=logging.INFO); log = logging.getLogger("vtab.mqtt")

def on_connect(client, userdata, flags, reason_code, properties):
    log.info("Connected to MQTT with code %s", reason_code)
    client.subscribe(settings.mqtt_topic, qos=1)
    client.subscribe("platform/faults", qos=1)

def on_message(client, userdata, message):
    try:
        data = json.loads(message.payload.decode())
        if message.topic == "platform/faults":
            with SessionLocal() as db:
                result = process_platform_fault(db, data)
            correlation_id = data.get("correlation_id")
            if correlation_id:
                result.update({"correlation_id": correlation_id, "processed_at": datetime.now(timezone.utc).isoformat()})
                client.publish(f"platform/faults/receipts/{correlation_id}", json.dumps(result), qos=1)
            log.info("Processed software fault %s: %s", data.get("component"), result.get("status"))
            return
        payload = TelemetryIn(device_id=data.get("device_id", message.topic.split("/")[1]), timestamp=data.get("timestamp"), readings=data["readings"], health=data.get("health", {}))
        with SessionLocal() as db:
            result = ingest(db, payload)
            alert_ids = evaluate(db, result["core_event_id"], payload.readings)
            ai_result = analyze_and_persist(db, result["core_event_id"], result["telemetry_header_id"], payload.readings)
        correlation_id = data.get("correlation_id")
        if correlation_id:
            receipt = {"status":"complete","correlation_id":correlation_id,"core_event_id":result["core_event_id"],"telemetry_header_id":result["telemetry_header_id"],"database":"committed","alerts_created":len(alert_ids),"alert_ids":alert_ids,"ai_status":ai_result.get("status"),"ai_analysis_id":ai_result.get("ai_analysis_id"),"processed_at":datetime.now(timezone.utc).isoformat()}
            client.publish(f"devices/{payload.device_id}/receipts/{correlation_id}", json.dumps(receipt), qos=1)
        log.info("Ingested event %s (AI: %s)", result["core_event_id"], ai_result.get("status"))
    except Exception:
        log.exception("Rejected MQTT message on %s", message.topic)

def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="vtab-ingestion", clean_session=False)
    client.on_connect = on_connect; client.on_message = on_message
    while True:
        try:
            client.connect(settings.mqtt_host, settings.mqtt_port, keepalive=60)
            client.loop_forever()
        except OSError:
            log.warning("MQTT unavailable; retrying in 5 seconds")
            time.sleep(5)

if __name__ == "__main__":
    main()
