"""Small, transparent implementations of the five AI blocks in the PDF."""
from dataclasses import dataclass
import numpy as np

@dataclass
class Baseline:
    mean: float
    std: float

def learn_baseline(values: list[float]) -> Baseline:
    array=np.asarray(values,dtype=float)
    return Baseline(float(array.mean()), max(float(array.std()), 0.1))

def anomaly(values: list[float], baseline: Baseline) -> dict:
    latest=float(values[-1]); z=abs(latest-baseline.mean)/baseline.std
    return {"is_anomaly":z>=3,"anomaly_score":round(min(z/5,1),4),"z_score":round(z,4)}

def forecast(values: list[float], horizon: int=5) -> dict:
    x=np.arange(len(values),dtype=float); slope,intercept=np.polyfit(x,np.asarray(values),1)
    future=[round(float(intercept+slope*(len(values)+i)),3) for i in range(horizon)]
    return {"trend":"rising" if slope>.05 else "falling" if slope<-.05 else "stable","slope":round(float(slope),4),"forecast":future}

def risk_score(readings: dict[str,float], anomaly_score: float) -> dict:
    temp=max(0,(readings.get("temperature",24)-25)/15); humidity=max(0,(readings.get("humidity",50)-60)/40)
    hazards=max(float(readings.get("water_leak",0)),float(readings.get("smoke",0)))
    access=float(readings.get("door_open",0))
    score=round(min(100,100*(.30*temp+.15*humidity+.30*hazards+.10*access+.15*anomaly_score)),1)
    return {"score":score,"level":"critical" if score>=75 else "high" if score>=50 else "medium" if score>=25 else "low"}

def explain(readings: dict, anomaly_result: dict, risk: dict) -> str:
    factors=[]
    if readings.get("temperature",0)>30: factors.append("high temperature")
    if readings.get("humidity",0)>70: factors.append("high humidity")
    if readings.get("water_leak"): factors.append("water leak detected")
    if readings.get("smoke"): factors.append("smoke detected")
    if readings.get("door_open"): factors.append("server-room door open")
    if anomaly_result["is_anomaly"]: factors.append("statistical deviation from the learned baseline")
    reason=", ".join(factors) or "normal operating conditions"
    return f"Risk is {risk['level']} ({risk['score']}/100) due to {reason}. Inspect critical sensors when risk is high or critical."
