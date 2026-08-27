"""Evidence-first VTAB Sentinel 2.0 operations agent."""
from datetime import datetime, timezone
from math import sqrt
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session
from app import models
from app.services.alerts import adaptive_rule_details

def _iso(v): return v.isoformat() if v else None

def live_evidence(db:Session,org:str):
    alerts=db.scalar(select(func.count()).select_from(models.AlertHeader).join(models.CoreEvent).where(models.CoreEvent.organization_id==org,models.AlertHeader.status=="open")) or 0
    tickets=db.scalar(select(func.count()).select_from(models.IncidentHeader).join(models.CoreEvent).where(models.CoreEvent.organization_id==org,models.IncidentHeader.status.in_(["open","assigned","acknowledged"]))) or 0
    devices=db.scalar(select(func.count()).select_from(models.DimDevice).join(models.DimRoom).join(models.DimSite).where(models.DimSite.organization_id==org)) or 0
    rows=db.execute(select(models.TelemetryDetail,models.TelemetryHeader).join(models.TelemetryHeader).join(models.CoreEvent).where(models.CoreEvent.organization_id==org).order_by(desc(models.TelemetryDetail.measurement_timestamp)).limit(12)).all()
    readings=[{"type":d.measurement_type,"value":d.value_numeric,"unit":d.unit,"device_id":h.device_id,"timestamp":_iso(d.measurement_timestamp)} for d,h in rows]
    return {"open_alerts":alerts,"open_incidents":tickets,"devices":devices,"recent_readings":readings,"observed_at":datetime.now(timezone.utc).isoformat()}

def answer(db:Session,user,message:str,conversation_id=None):
    """Answer from persisted evidence and return UI actions that open the relevant workflow."""
    e=live_evidence(db,user.organization_id)
    if not conversation_id:
        c=models.AgentConversation(organization_id=user.organization_id,user_id=user.id,title=message[:80]);db.add(c);db.flush();conversation_id=c.id
    db.add(models.AgentMessage(conversation_id=conversation_id,role="user",content=message,confidence=1))
    q=message.lower();latest=e["recent_readings"];cites=[];suggested=[]
    if any(x in q for x in ("forecast","predict","trend","future")):
        predictions=intelligence(db,user.organization_id)
        if predictions:
            parts=[f"{p['measurement_type'].replace('_',' ')} is {p['current_value']} and forecasts {p['forecast_value']} ({p['status'].replace('_',' ')}, trust {p['trust_score']}%)" for p in predictions[:5]]
            breaches=[p["measurement_type"].replace("_"," ") for p in predictions if p["forecast_breach"]]
            text="Forecast evidence: "+"; ".join(parts)+(". Predicted threshold attention: "+", ".join(breaches)+"." if breaches else ". No forecast threshold breach is currently identified.")
            cites.append({"source":"sensor_intelligence","label":f"{len(predictions)} live forecast result(s)","observed_at":e["observed_at"]})
        else:text="The forecast pipeline is ready, but it needs validated telemetry samples before it can calculate a trend."
        suggested=[{"label":"Open predictive intelligence","page":"AI Operations"},{"label":"Inspect telemetry","page":"Telemetry"}]
    elif any(x in q for x in ("recovery","action","resolved","closed","workflow")):
        actions=db.scalars(select(models.AgentAction).where(models.AgentAction.organization_id==user.organization_id).order_by(desc(models.AgentAction.created_at)).limit(5)).all()
        if actions:
            a=actions[0];timeline=a.execution_log or [];stages=" → ".join(str(step.get("state","recorded")).replace("_"," ") for step in timeline)
            text=f"Latest recovery workflow: {a.action_type.replace('_',' ')} is {a.status.replace('_',' ')} at risk level {a.risk_level}. Reason: {a.rationale or 'policy-based operational recovery'}. Execution stages: {stages or 'no execution stages recorded yet'}."
            cites.append({"source":"agent_actions","label":f"Recovery action {a.id[:8]} with {len(timeline)} stage(s)","observed_at":_iso(a.completed_at or a.created_at)})
        else:text="No automated recovery action has been recorded yet. The workflow will appear after a threshold breach or controlled software-fault test."
        suggested=[{"label":"Open AI action evidence","page":"AI Operations"},{"label":"Open incident lifecycle","page":"Incidents"}]
    elif any(x in q for x in ("incident","ticket","priority")):
        tickets=db.scalars(select(models.IncidentHeader).join(models.CoreEvent).where(models.CoreEvent.organization_id==user.organization_id).order_by(desc(models.IncidentHeader.created_at)).limit(8)).all()
        open_rows=[t for t in tickets if t.status in {"open","assigned","acknowledged"}];critical=sum(1 for t in open_rows if t.severity=="critical")
        text=f"Incident evidence: {len(open_rows)} of the latest {len(tickets)} ticket(s) remain open, including {critical} critical ticket(s). " + (f"The newest open ticket is {open_rows[0].severity} priority and currently {open_rows[0].status}." if open_rows else "All tickets in the latest evidence set are closed.")
        cites.append({"source":"incident_headers","label":f"{len(tickets)} latest ticket lifecycle record(s)","observed_at":e["observed_at"]})
        suggested=[{"label":"Open incident center","page":"Incidents"},{"label":"Review alert lifecycles","page":"Alerts"}]
    elif any(x in q for x in ("health","status","attention","problem")):
        text="The monitored environment is healthy." if not e["open_alerts"] and not e["open_incidents"] else f"Attention is required: {e['open_alerts']} active alert(s) and {e['open_incidents']} open ticket(s). Open the incident center to review priority and closure evidence."
        cites.append({"source":"operations_database","label":"Current alert and incident state","observed_at":e["observed_at"]})
        suggested=[{"label":"Open incident center","page":"Incidents"},{"label":"Open system health","page":"AI Operations"}]
    elif any(x in q for x in ("temperature","humidity","smoke","water","door","sensor","climate")):
        wanted=next((x for x in ("temperature","humidity","smoke","water","door") if x in q),None);selected=[r for r in latest if not wanted or wanted in r["type"]]
        text="Latest sensor evidence: "+("; ".join(f"{r['type'].replace('_',' ')} {r['value']} {r['unit']} at {r['timestamp']}" for r in selected[:5]) if selected else "no matching telemetry has arrived yet.")
        cites.append({"source":"telemetry_details","label":f"{len(selected)} matching live reading(s)","timestamp":selected[0]["timestamp"] if selected else None})
        suggested=[{"label":"Open telemetry charts","page":"Telemetry"},{"label":"Review threshold settings","page":"Settings"}]
    else:
        text=f"I checked the live operations database: {e['devices']} device(s), {e['open_alerts']} active alert(s), and {e['open_incidents']} open ticket(s). Ask about attention, incidents, a sensor, forecasts or recovery workflows for evidence-linked detail."
        cites.append({"source":"operations_database","label":"Live operational snapshot","observed_at":e["observed_at"]})
        suggested=[{"label":"Open Overview","page":"Overview"},{"label":"Open AI Operations","page":"AI Operations"}]
    if latest and not any(c.get("source")=="telemetry_details" for c in cites):cites.append({"source":"telemetry_details","label":"Latest sensor readings","timestamp":latest[0]["timestamp"]})
    db.add(models.AgentMessage(conversation_id=conversation_id,role="assistant",content=text,evidence=cites,confidence=.96));db.commit()
    return {"conversation_id":conversation_id,"message":text,"confidence":.96,"evidence":cites,"snapshot":e,"suggested_actions":suggested}
def intelligence(db:Session,org:str):
    output=[]
    for name in db.scalars(select(models.TelemetryDetail.measurement_type).join(models.TelemetryHeader).join(models.CoreEvent).where(models.CoreEvent.organization_id==org).distinct()).all():
        rows=db.scalars(select(models.TelemetryDetail).join(models.TelemetryHeader).join(models.CoreEvent).where(models.CoreEvent.organization_id==org,models.TelemetryDetail.measurement_type==name,models.TelemetryDetail.value_numeric.is_not(None)).order_by(desc(models.TelemetryDetail.measurement_timestamp)).limit(30)).all(); vals=[float(r.value_numeric) for r in reversed(rows)]; n=len(vals)
        if not n:continue
        mean=sum(vals)/n;sd=sqrt(sum((v-mean)**2 for v in vals)/n);slope=(vals[-1]-vals[0])/max(n-1,1);score=min(abs(vals[-1]-mean)/(sd or 1),10)
        rule=adaptive_rule_details(db,org,name);forecast=vals[-1]+slope*5;threshold=rule["effective_threshold"] if rule else None;operator=rule["operator"] if rule else None
        upper_breach=bool(rule and {"gt":forecast>threshold,"gte":forecast>=threshold,"lt":forecast<threshold,"lte":forecast<=threshold,"eq":forecast==threshold}.get(operator,False));lower_threshold=rule.get("effective_lower_threshold") if rule else None;lower_breach=bool(name=="temperature" and lower_threshold is not None and forecast<float(lower_threshold));forecast_breach=upper_breach or lower_breach
        forecast_status="forecast_cold_breach" if lower_breach else "forecast_breach" if upper_breach else "anomaly" if score>=3 else "watch" if abs(slope)>.8 else "stable"
        output.append({"measurement_type":name,"current_value":round(vals[-1],2),"forecast_value":round(forecast,2),"trend_per_sample":round(slope,3),"anomaly_score":round(score,2),"trust_score":round(max(0,min(100,35+n*2.1)-(15 if n<5 else 0)),1),"status":forecast_status,"sample_count":n,"threshold":threshold,"lower_threshold":lower_threshold,"operator":operator,"forecast_breach":forecast_breach,"upper_forecast_breach":upper_breach,"lower_forecast_breach":lower_breach,"threshold_mode":rule["mode"] if rule else "none","configured_threshold":rule["configured_threshold"] if rule else None,"baseline":rule["baseline"] if rule else None,"hard_safety_ceiling":rule["hard_safety_ceiling"] if rule else None,"hard_safety_floor":rule.get("hard_safety_floor") if rule else None})
    return output

def digital_twin(db:Session,org:str):
    sites=[]
    for site in db.scalars(select(models.DimSite).where(models.DimSite.organization_id==org)).all():
        rooms=[]
        for room in db.scalars(select(models.DimRoom).where(models.DimRoom.site_id==site.id)).all():
            devices=[]
            for d in db.scalars(select(models.DimDevice).where(models.DimDevice.room_id==room.id)).all(): devices.append({"id":d.id,"name":d.name,"hardware_type":d.hardware_type,"status":d.status,"last_seen_at":_iso(d.last_seen_at),"sensors":[{"id":s.id,"type":s.sensor_type,"unit":s.unit} for s in db.scalars(select(models.DimSensor).where(models.DimSensor.device_id==d.id)).all()]})
            rooms.append({"id":room.id,"name":room.name,"devices":devices})
        sites.append({"id":site.id,"name":site.name,"location":site.location,"rooms":rooms})
    return {"organization_id":org,"sites":sites,"generated_at":datetime.now(timezone.utc).isoformat()}



