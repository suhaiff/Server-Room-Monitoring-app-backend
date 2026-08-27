"""Multi-device ESP32 test gateway with automatic simulation fallback."""
import json, os, time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4
import httpx
import paho.mqtt.client as mqtt
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

MQTT_HOST=os.getenv("MQTT_HOST","mosquitto"); MQTT_PORT=int(os.getenv("MQTT_PORT","1883"))
DEVICE_ID=os.getenv("DEVICE_ID","00000000-0000-0000-0000-000000000101")
BACKEND_URL=os.getenv("BACKEND_URL","http://backend:8000/api/v1")
SENSORS=("temperature","humidity","water_leak","door_open","smoke")
client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id="vtab-multi-device-tester")
state={"connected":False,"connecting":False,"last_publish_at":None,"published":0,"last_payload":None,"last_hardware_at":None,"latest_hardware_payload":None}
device_state={}; cooling_state={}; receipts={}; lock=Lock()

MIN_SAFE_TEMPERATURE_C=18.0
CRITICAL_LOW_TEMPERATURE_C=15.0
MAX_SAFE_TEMPERATURE_C=30.0
CRITICAL_HIGH_TEMPERATURE_C=40.0

def bucket(device_id):
 return device_state.setdefault(device_id,{"last_publish_at":None,"published":0,"last_payload":None,"last_hardware_at":None,"latest_hardware_payload":None})

class Readings(BaseModel):
 temperature:float|None=Field(None,ge=-20,le=100); humidity:float|None=Field(None,ge=0,le=100); water_leak:int|None=Field(None,ge=0,le=1); door_open:int|None=Field(None,ge=0,le=1); smoke:int|None=Field(None,ge=0,le=1)
class PublishRequest(BaseModel):
 device_id:str|None=None; readings:Readings; board:str="ESP32 DevKit V1"; firmware:str="sentinel-component-tester-5.0"; rssi:int=Field(-42,ge=-100,le=0); sources:dict[str,dict]=Field(default_factory=dict)
 @field_validator("board")
 @classmethod
 def esp_only(cls,v):
  if "ESP32" not in v: raise ValueError("Only ESP32 board profiles are supported")
  return v
class ComponentSetting(BaseModel):
 mode:str=Field(pattern="^(hardware|simulated)$"); simulated_value:float|int|None=None
class ComponentConfig(BaseModel):
 device_id:str|None=None; components:dict[str,ComponentSetting]
 @field_validator("components")
 @classmethod
 def known(cls,v):
  unknown=sorted(set(v)-set(SENSORS))
  if unknown: raise ValueError(f"Unknown component(s): {', '.join(unknown)}")
  return v

class CoolingConfig(BaseModel):
 device_id:str|None=None
 mode:str=Field("manual",pattern="^(off|manual|auto)$")
 cooling_power_percent:float=Field(45,ge=0,le=100)
 ambient_temperature_c:float=Field(32,ge=5,le=55)
 server_heat_kw:float=Field(12,ge=0,le=50)
 target_temperature_c:float=Field(22,ge=18,le=27)

class CoolingStepRequest(BaseModel):
 device_id:str|None=None
 seconds:int=Field(60,ge=1,le=600)
 publish:bool=True

class CoolingResetRequest(BaseModel):
 device_id:str|None=None
 room_temperature_c:float=Field(24,ge=5,le=55)

def cooling_bucket(device_id):
 return cooling_state.setdefault(device_id,{"mode":"manual","cooling_power_percent":45.0,"ambient_temperature_c":32.0,"server_heat_kw":12.0,"target_temperature_c":22.0,"room_temperature_c":24.0,"trend_c_per_min":0.0,"recommended_power_percent":48.0,"simulated_minutes":0.0,"last_step_at":None,"last_correlation_id":None,"status":"safe","safe_band":{"minimum_c":18.0,"maximum_c":30.0,"critical_low_c":15.0,"critical_high_c":40.0},"recommendation":"Maintain the current cooling output while the temperature remains inside the safe band."})

def thermal_status(temperature):
 if temperature<=CRITICAL_LOW_TEMPERATURE_C:return "critical_cold"
 if temperature<MIN_SAFE_TEMPERATURE_C:return "too_cold"
 if temperature>=CRITICAL_HIGH_TEMPERATURE_C:return "critical_hot"
 if temperature>MAX_SAFE_TEMPERATURE_C:return "too_hot"
 return "safe"

def cooling_recommendation(status, power):
 if status=="critical_cold":return "Stop cooling immediately and inspect the thermostat, condensation and rack inlet temperatures."
 if status=="too_cold":return "Reduce cooling output until the room returns to the 18-30 C safe band."
 if status=="critical_hot":return "Maximum cooling is required; verify airflow and prepare an operator escalation."
 if status=="too_hot":return "Increase cooling output and monitor the temperature recovery trend."
 return f"Maintain approximately {power:.0f}% cooling while the temperature remains inside the safe band."

def advance_cooling(current,seconds):
 """Advance a deterministic room thermal model and return a fresh state dictionary."""
 next_state=dict(current);room=float(next_state["room_temperature_c"]);ambient=float(next_state["ambient_temperature_c"]);heat=float(next_state["server_heat_kw"]);target=float(next_state["target_temperature_c"]);mode=next_state["mode"]
 passive_gain=heat*.032+(ambient-room)*.015
 required_power=max(0,min(100,(passive_gain/1.05)*100+(room-target)*10))
 power=0.0 if mode=="off" else float(next_state["cooling_power_percent"])
 if mode=="auto":
  delta=max(-12,min(12,required_power-power));power=max(0,min(100,power+delta));next_state["cooling_power_percent"]=round(power,1)
 trend=passive_gain-(power/100)*1.05
 room=max(5,min(55,room+trend*(seconds/60)))
 status=thermal_status(room)
 next_state.update({"room_temperature_c":round(room,2),"trend_c_per_min":round(trend,3),"recommended_power_percent":round(required_power,1),"simulated_minutes":round(float(next_state.get("simulated_minutes",0))+seconds/60,1),"last_step_at":datetime.now(timezone.utc).isoformat(),"status":status,"safe_band":{"minimum_c":MIN_SAFE_TEMPERATURE_C,"maximum_c":MAX_SAFE_TEMPERATURE_C,"critical_low_c":CRITICAL_LOW_TEMPERATURE_C,"critical_high_c":CRITICAL_HIGH_TEMPERATURE_C},"recommendation":cooling_recommendation(status,required_power)})
 return next_state
def on_connect(c,_u,_f,reason,_p):
 state["connected"]=not getattr(reason,"is_failure",bool(reason)); state["connecting"]=False
 if state["connected"]:
  c.subscribe("devices/+/receipts/+",qos=1);c.subscribe("devices/+/telemetry",qos=1)
def on_disconnect(_c,_u,_f,_r,_p): state["connected"]=False;state["connecting"]=False
def on_message(_c,_u,message):
 try:
  data=json.loads(message.payload.decode());topic=getattr(message,"topic","");parts=topic.split("/");device_id=data.get("device_id") or (parts[1] if len(parts)>1 else DEVICE_ID)
  if topic.endswith("/telemetry"):
   if data.get("health",{}).get("source")=="esp32-hardware":
    stamp=data.get("timestamp") or datetime.now(timezone.utc).isoformat()
    with lock:
     current=bucket(device_id);current["last_hardware_at"]=stamp;current["latest_hardware_payload"]=data
     if device_id==DEVICE_ID: state["last_hardware_at"]=stamp;state["latest_hardware_payload"]=data
   return
  with lock: receipts[data["correlation_id"]]=data
 except (ValueError,KeyError): return

def connect(raise_error=True):
 if state["connected"] or state["connecting"]: return
 try:
  state["connecting"]=True;client.connect(MQTT_HOST,MQTT_PORT,keepalive=60);client.loop_start();deadline=time.time()+3
  while not state["connected"] and time.time()<deadline:time.sleep(.05)
 except OSError as exc:
  state["connecting"]=False
  if raise_error:raise HTTPException(503,f"MQTT broker unavailable: {exc}") from exc

def send(topic,payload,retain=False):
 connect()
 try:info=client.publish(topic,json.dumps(payload),qos=1,retain=retain)
 except TypeError:info=client.publish(topic,json.dumps(payload),qos=1)
 info.wait_for_publish(timeout=5)
 if info.rc!=mqtt.MQTT_ERR_SUCCESS:raise HTTPException(503,"MQTT publish was not acknowledged")
 return info

def registry():
 try:
  response=httpx.get(f"{BACKEND_URL}/simulator/device-registry",timeout=3);response.raise_for_status();return response.json()
 except Exception:
  return [{"id":DEVICE_ID,"name":"ESP32 Sentinel 01","hardware_type":"ESP32 WiFi","firmware_version":"unknown","sensor_types":list(SENSORS),"sensors":[{"id":f"legacy-{name}","sensor_type":name,"label":f"{name.replace('_',' ').title()} sensor 1"} for name in SENSORS],"hardware_online":False,"status":"offline","effective_mode":"simulated"}]

def is_online(stamp):
 if not stamp:return False
 try:return (datetime.now(timezone.utc)-datetime.fromisoformat(stamp.replace("Z","+00:00"))).total_seconds()<20
 except ValueError:return False

def hardware_capable(source):
 if source.get("sensor_error"):return False
 if "hardware_available" in source:return bool(source["hardware_available"])
 if source.get("mode")=="hardware":return True
 return source.get("pin") is not None

@asynccontextmanager
async def lifespan(_app):
 connect(False);yield;client.loop_stop();client.disconnect()
app=FastAPI(title="VTAB Multi-device Component Tester",version="5.1.0",lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:5174"],allow_credentials=False,allow_methods=["GET","POST"],allow_headers=["Content-Type"])
client.on_connect=on_connect;client.on_disconnect=on_disconnect;client.on_message=on_message

@app.get("/health")
def health():
 state["connected"]=bool(client.is_connected())
 if not state["connected"]:connect(False)
 return {"status":"healthy" if state["connected"] else "waiting-for-mqtt","mqtt_connected":state["connected"],"device_id":DEVICE_ID}
@app.get("/devices")
def devices():
 values=registry()
 for item in values:
  current=bucket(item["id"]);online=is_online(current["last_hardware_at"]);packet=current.get("latest_hardware_payload") or {};sources=packet.get("sources") or {}
  hardware_sensor_ids=[]
  active_hardware_sensor_ids=[]
  for sensor_type,source in sources.items():
   if hardware_capable(source):
    sensor_id=source.get("sensor_id") or next((sensor["id"] for sensor in item.get("sensors",[]) if sensor["sensor_type"]==sensor_type),None)
    if sensor_id:
     hardware_sensor_ids.append(sensor_id)
     if source.get("mode")=="hardware":active_hardware_sensor_ids.append(sensor_id)
  item.update({"hardware_online":online,"status":"online" if online else "offline","effective_mode":"hardware" if online else "simulated",
               "last_hardware_at":current["last_hardware_at"],"hardware_sensor_ids":hardware_sensor_ids,"active_hardware_sensor_ids":active_hardware_sensor_ids})
 return values
@app.get("/status")
def status(device_id:str=Query(default=DEVICE_ID)):
 state["connected"]=bool(client.is_connected());current=bucket(device_id);online=is_online(current["last_hardware_at"])
 packet=current.get("latest_hardware_payload") or {};sources=packet.get("sources") or {}
 hardware_types=[name for name,source in sources.items() if hardware_capable(source)]
 registered=next((item for item in registry() if item["id"]==device_id),{})
 hardware_sensor_ids=[]
 active_hardware_sensor_ids=[]
 for sensor_type,source in sources.items():
  if hardware_capable(source):
   sensor_id=source.get("sensor_id") or next((sensor["id"] for sensor in registered.get("sensors",[]) if sensor["sensor_type"]==sensor_type),None)
   if sensor_id:
    hardware_sensor_ids.append(sensor_id)
    if source.get("mode")=="hardware":active_hardware_sensor_ids.append(sensor_id)
 return {**state,**current,"device_id":device_id,"mqtt_host":MQTT_HOST,"mqtt_port":MQTT_PORT,"hardware_online":online,
         "hardware_sensor_ids":hardware_sensor_ids,"active_hardware_sensor_ids":active_hardware_sensor_ids,"hardware_types":hardware_types,
         "effective_mode":"hardware" if online else "simulated","config_topic":f"devices/{device_id}/config/sources"}
@app.post("/components/configure")
def configure(body:ComponentConfig):
 device_id=body.device_id or DEVICE_ID;config={k:v.model_dump() for k,v in body.components.items()};topic=f"devices/{device_id}/config/sources"
 send(topic,{"device_id":device_id,"components":config,"updated_at":datetime.now(timezone.utc).isoformat()},True)
 return {"status":"configured","device_id":device_id,"topic":topic,"components":config}
@app.post("/publish")
def publish(body:PublishRequest):
 device_id=body.device_id or DEVICE_ID;known={item["id"] for item in registry()}
 if device_id not in known:raise HTTPException(404,"Device is not registered in the backend")
 timestamp=datetime.now(timezone.utc).isoformat();correlation=str(uuid4())
 sources=body.sources or {n:{"mode":"simulated","provider":"component-tester"} for n in SENSORS}
 payload={"device_id":device_id,"timestamp":timestamp,"correlation_id":correlation,"readings":body.readings.model_dump(exclude_none=True),"sources":sources,
          "health":{"rssi":body.rssi,"uptime_seconds":int(time.monotonic()),"firmware":body.firmware,"board":body.board,"source":"component-tester-virtual"}}
 info=send(f"devices/{device_id}/telemetry",payload)
 with lock:
  current=bucket(device_id);current["last_publish_at"]=timestamp;current["published"]+=1;current["last_payload"]=payload
  state["connected"]=True;state["last_publish_at"]=timestamp;state["published"]+=1;state["last_payload"]=payload
 return {"status":"published","device_id":device_id,"message_id":info.mid,"correlation_id":correlation,
         "topic":f"devices/{device_id}/telemetry","timestamp":timestamp,"next_stage":"mqtt-worker -> database -> alerts -> AI"}
@app.get("/cooling/status")
def cooling_status(device_id:str=Query(default=DEVICE_ID)):
 return {"device_id":device_id,**cooling_bucket(device_id),"mqtt_topic":f"devices/{device_id}/telemetry"}

@app.post("/cooling/configure")
def configure_cooling(body:CoolingConfig):
 device_id=body.device_id or DEVICE_ID
 if device_id not in {item["id"] for item in registry()}:raise HTTPException(404,"Device is not registered in the backend")
 with lock:
  current=cooling_bucket(device_id);current.update(body.model_dump(exclude={"device_id"}))
  current["status"]=thermal_status(current["room_temperature_c"]);current["recommendation"]=cooling_recommendation(current["status"],current["recommended_power_percent"])
 return {"status":"configured","device_id":device_id,**current}

@app.post("/cooling/reset")
def reset_cooling(body:CoolingResetRequest):
 device_id=body.device_id or DEVICE_ID
 with lock:
  cooling_state[device_id]={"mode":"manual","cooling_power_percent":45.0,"ambient_temperature_c":32.0,"server_heat_kw":12.0,"target_temperature_c":22.0,"room_temperature_c":body.room_temperature_c,"trend_c_per_min":0.0,"recommended_power_percent":48.0,"simulated_minutes":0.0,"last_step_at":None,"last_correlation_id":None,"status":thermal_status(body.room_temperature_c),"safe_band":{"minimum_c":MIN_SAFE_TEMPERATURE_C,"maximum_c":MAX_SAFE_TEMPERATURE_C,"critical_low_c":CRITICAL_LOW_TEMPERATURE_C,"critical_high_c":CRITICAL_HIGH_TEMPERATURE_C},"recommendation":"Cooling model reset. Start or step the model to generate telemetry."}
 return {"status":"reset","device_id":device_id,**cooling_state[device_id]}

@app.post("/cooling/step")
def step_cooling(body:CoolingStepRequest):
 device_id=body.device_id or DEVICE_ID
 if device_id not in {item["id"] for item in registry()}:raise HTTPException(404,"Device is not registered in the backend")
 with lock:
  next_state=advance_cooling(cooling_bucket(device_id),body.seconds);cooling_state[device_id]=next_state
 correlation=None
 if body.publish:
  timestamp=datetime.now(timezone.utc).isoformat();correlation=str(uuid4())
  health={"source":"hvac-thermal-simulator","cooling":{"mode":next_state["mode"],"output_percent":next_state["cooling_power_percent"],"ambient_temperature_c":next_state["ambient_temperature_c"],"server_heat_kw":next_state["server_heat_kw"],"target_temperature_c":next_state["target_temperature_c"],"trend_c_per_min":next_state["trend_c_per_min"],"thermal_status":next_state["status"]}}
  payload={"device_id":device_id,"timestamp":timestamp,"correlation_id":correlation,"readings":{"temperature":next_state["room_temperature_c"]},"sources":{"temperature":{"mode":"simulated","provider":"hvac-thermal-model"}},"health":health}
  info=send(f"devices/{device_id}/telemetry",payload)
  with lock:
   next_state["last_correlation_id"]=correlation;current=bucket(device_id);current["last_publish_at"]=timestamp;current["published"]+=1;current["last_payload"]=payload
   state["connected"]=True;state["last_publish_at"]=timestamp;state["published"]+=1;state["last_payload"]=payload
 return {"status":"advanced","device_id":device_id,"published":body.publish,"correlation_id":correlation,**next_state,"next_stage":"MQTT -> database -> adaptive thresholds -> alerts -> AI"}
@app.get("/receipts/{correlation_id}")
def receipt(correlation_id:str):return receipts.get(correlation_id,{"status":"processing","correlation_id":correlation_id})