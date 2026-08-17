"""Independent, production-safe VTAB software failure simulation console."""
import json, os, threading, time, uuid
from datetime import datetime, timezone
import paho.mqtt.client as mqtt
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

SCENARIOS = {
    "postgres": ("PostgreSQL / TimescaleDB", "critical", "Simulated database response timeout", "Check database health, connections and storage capacity."),
    "redis": ("Redis cache", "warning", "Simulated Redis connection failure", "Check Redis availability and background job retries."),
    "mqtt": ("Mosquitto MQTT", "critical", "Simulated MQTT message backlog", "Inspect broker connections, queue depth and ingestion worker."),
    "ai_baseline": ("AI baseline model", "critical", "Simulated AI baseline-learning model failure", "Inspect baseline history input and model execution logs."),
    "ai_anomaly": ("AI anomaly detector", "critical", "Simulated AI anomaly-detection model failure", "Inspect anomaly model inputs, score calculation and execution logs."),
    "ai_forecast": ("AI forecast model", "critical", "Simulated AI forecasting model failure", "Inspect time-series history, forecast horizon and execution logs."),
    "ai_risk": ("AI risk engine", "critical", "Simulated AI risk-scoring model failure", "Inspect sensor features, anomaly score and risk policy logs."),
    "ai_explanation": ("AI explanation model", "critical", "Simulated AI explanation model failure", "Inspect inference results and explanation-generation logs."),
    "minio": ("MinIO object storage", "warning", "Simulated object storage outage", "Check MinIO health, credentials and storage volume."),
    "backend": ("FastAPI backend", "critical", "Simulated elevated backend API error rate", "Inspect backend diagnostics, dependencies and recent logs."),
}
app = FastAPI(title="VTAB Software Test Console", version="1.0")
receipts, pending = {}, {}
state = {key: "normal" for key in SCENARIOS}
connected = False
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"software-lab-{uuid.uuid4().hex[:8]}")

def on_connect(c, userdata, flags, reason_code, properties):
    global connected
    connected = reason_code == 0
    c.subscribe("platform/faults/receipts/+", qos=1)

def on_disconnect(c, userdata, disconnect_flags, reason_code, properties):
    global connected
    connected = False

def on_message(c, userdata, message):
    try:
        data = json.loads(message.payload)
        correlation = data.get("correlation_id")
        if correlation:
            receipts[correlation] = data
            item = pending.get(correlation)
            if item: state[item[0]] = "active" if item[1] == "trigger" else "pending_closure"
    except Exception:
        pass

client.on_connect, client.on_disconnect, client.on_message = on_connect, on_disconnect, on_message

def mqtt_loop():
    while True:
        try:
            client.connect(os.getenv("MQTT_HOST", "mosquitto"), int(os.getenv("MQTT_PORT", "1883")), 60)
            client.loop_forever()
        except OSError:
            time.sleep(3)

@app.on_event("startup")
def startup(): threading.Thread(target=mqtt_loop, daemon=True).start()

@app.get("/health")
def health(): return {"status": "healthy" if connected else "waiting", "mqtt_connected": connected}

@app.get("/api/status")
def status():
    return {"mqtt_connected": connected, "components": [{"key": k, "label": v[0], "state": state[k]} for k,v in SCENARIOS.items()]}

@app.post("/api/faults/{key}/{action}")
def fault(key: str, action: str):
    if key not in SCENARIOS or action not in {"trigger", "recover"}: raise HTTPException(404, "Unknown test action")
    if not connected: raise HTTPException(503, "MQTT is not connected yet")
    label, severity, message, recommendation = SCENARIOS[key]
    correlation = str(uuid.uuid4())
    payload = {"component": key, "label": label, "severity": severity, "message": message,
               "recommendation": recommendation, "action": action, "correlation_id": correlation,
               "timestamp": datetime.now(timezone.utc).isoformat()}
    info = client.publish("platform/faults", json.dumps(payload), qos=1)
    info.wait_for_publish(timeout=3)
    pending[correlation] = (key, action)
    state[key] = "processing"
    return {"status": "published", "correlation_id": correlation, "action": action}

@app.get("/api/receipts/{correlation}")
def receipt(correlation: str):
    return receipts.get(correlation, {"status": "processing", "correlation_id": correlation})

HTML = r'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>VTAB Software Test Console</title>
<style>*{box-sizing:border-box}body{margin:0;background:#03111d;color:#eaf8ff;font:15px Inter,Segoe UI,sans-serif}.shell{max-width:1450px;margin:auto;padding:32px}.top{display:flex;justify-content:space-between;align-items:center}.eyebrow{color:#27e6e0;letter-spacing:3px;font-weight:800}h1{font-size:40px;margin:7px 0}.sub{color:#82a9c3}.badge{padding:13px 18px;border:1px solid #22506b;border-radius:14px;background:#081d2b}.badge.ok{color:#4ff0ca;border-color:#19795f}.pipeline{display:flex;align-items:center;justify-content:space-between;margin:30px 0;padding:22px;border:1px solid #17415b;border-radius:18px;background:#061a28}.step b{display:block;color:#fff}.step span{color:#729ab4;font-size:12px}.arrow{color:#1bd7e1;font-size:24px}.note{padding:15px 18px;border-left:4px solid #ffbb43;background:#30220d;border-radius:8px;color:#ffd885}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin-top:22px}.card{background:linear-gradient(145deg,#071d2c,#061622);border:1px solid #19445e;border-radius:18px;padding:22px;min-height:230px;position:relative;overflow:hidden}.card:before{content:'';position:absolute;inset:0 auto 0 0;width:4px;background:#25d5df}.card.active{border-color:#db435e;background:linear-gradient(145deg,#28111b,#101722)}.card.active:before{background:#ff526d}.card.pending_closure{border-color:#db9b2e}.card.pending_closure:before{background:#ffbd45}.icon{font-size:29px}h2{font-size:20px;margin:14px 0 8px}.state{text-transform:uppercase;font-size:11px;letter-spacing:1.4px;color:#4ff0ca;font-weight:800}.card.active .state{color:#ff7087}.card.pending_closure .state{color:#ffc75d}.desc{color:#86abc3;min-height:48px;line-height:1.5}.buttons{display:flex;gap:10px;margin-top:18px}button{border:0;border-radius:9px;padding:11px 14px;font-weight:800;cursor:pointer;background:#e43e5a;color:white}button.recover{background:#0d695b;color:#73ffe0}button:disabled{opacity:.45;cursor:not-allowed}.log{margin-top:24px;border:1px solid #17415b;background:#04121d;border-radius:16px;padding:18px}.log pre{white-space:pre-wrap;color:#7fded6;margin:8px 0 0}@media(max-width:900px){.grid{grid-template-columns:1fr}.pipeline{overflow:auto;gap:25px}.shell{padding:18px}}</style></head>
<style>html{scrollbar-width:thin;scrollbar-color:#2f7188 #03111d}html::-webkit-scrollbar{width:9px;height:9px}html::-webkit-scrollbar-track{background:#03111d}html::-webkit-scrollbar-thumb{background:linear-gradient(#278197,#205369);border:2px solid #03111d;border-radius:10px}html::-webkit-scrollbar-thumb:hover{background:#35bfd1}pre{scrollbar-width:thin;scrollbar-color:#2f7188 #04121d}</style>
<body><main class="shell"><header class="top"><div><div class="eyebrow">VTAB SENTINEL · UNIFIED SIMULATOR</div><h1>Software Reliability Test Console</h1><div class="sub">Controlled fault injection for named backend services and individual AI models</div></div><div id="mqtt" class="badge">MQTT CONNECTING</div></header>
<section class="pipeline"><div class="step"><b>01 Select fault</b><span>Developer console</span></div><div class="arrow">→</div><div class="step"><b>02 Publish test event</b><span>MQTT platform/faults</span></div><div class="arrow">→</div><div class="step"><b>03 Persist evidence</b><span>Database event + alert</span></div><div class="arrow">→</div><div class="step"><b>04 Operator response</b><span>Dashboard ticket + voice</span></div></section>
<div class="note">Safe simulation mode: these controls create realistic fault events and tickets, but never stop Docker containers or damage stored data.</div><section id="grid" class="grid"></section><section class="log"><b>Processing receipt</b><pre id="log">Waiting for a test...</pre></section></main>
<script>const icons={postgres:'DB',redis:'R',mqtt:'MQ',minio:'S3',backend:'API'};let labels={};
async function refresh(){let d=await fetch('api/status').then(r=>r.json());document.querySelector('#mqtt').textContent=d.mqtt_connected?'MQTT CONNECTED':'MQTT WAITING';document.querySelector('#mqtt').className='badge '+(d.mqtt_connected?'ok':'');let g=document.querySelector('#grid');g.innerHTML=d.components.map(x=>{labels[x.key]=x.label;let icon=icons[x.key]||(x.key.startsWith('ai_')?'AI':'SYS');return `<article class="card ${x.state}"><div class="icon">${icon}</div><div class="state">${x.state.replace('_',' ')}</div><h2>${x.label}</h2><div class="desc">Inject a controlled ${x.label} interruption. Its exact model or service name will appear in the alert, ticket, voice message and operations diagnostics.</div><div class="buttons"><button onclick="act('${x.key}','trigger')" ${x.state==='processing'?'disabled':''}>Simulate failure</button><button class="recover" onclick="act('${x.key}','recover')" ${x.state==='normal'||x.state==='processing'?'disabled':''}>Simulate recovery</button></div></article>`}).join('')}
async function act(key,action){let r=await fetch(`api/faults/${key}/${action}`,{method:'POST'});let d=await r.json();if(!r.ok){document.querySelector('#log').textContent=d.detail;return}document.querySelector('#log').textContent=`${labels[key]} ${action} published. Waiting for backend receipt...`;refresh();poll(d.correlation_id)}
async function poll(id){for(let i=0;i<20;i++){await new Promise(r=>setTimeout(r,750));let d=await fetch('api/receipts/'+id).then(r=>r.json());document.querySelector('#log').textContent=JSON.stringify(d,null,2);if(d.status!=='processing'){refresh();return}}document.querySelector('#log').textContent+='\nReceipt timeout: inspect MQTT worker logs.'}refresh();setInterval(refresh,4000)</script></body></html>'''

@app.get("/", response_class=HTMLResponse)
def index(): return HTML
