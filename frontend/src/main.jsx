import React,{useEffect,useRef,useState} from "react";
import {createRoot} from "react-dom/client";
import {Activity,AlertTriangle,BellRing,BrainCircuit,CheckCircle,CheckCircle2,ChevronRight,ClipboardCheck,Clock,Cpu,DoorOpen,Droplets,ExternalLink,FileBarChart,Globe,LayoutDashboard,Layers,LockKeyhole,LogOut,Mail,MapPin,Menu,Paperclip,RefreshCw,Send,Server,Settings,ShieldCheck,SlidersHorizontal,Sun,Moon,Volume2,VolumeX,X,Eye,EyeOff,Box,Zap} from "lucide-react";
import {Area,AreaChart,Bar,BarChart,CartesianGrid,Legend,Line,LineChart,ReferenceLine,ResponsiveContainer,Tooltip,XAxis,YAxis} from "recharts";
import {API_URL,api,login,register as registerApi,verify as verifyApi} from "./api";
import AITerminal from "./components/AITerminal";
import {VoiceProvider,useVoice} from "./voice/VoiceProvider";
import {AgentAssistant,ClimateStatus} from "./components/AgentAssistant";
const RoomDigitalTwin=React.lazy(()=>import("./components/RoomDigitalTwin"));
import "./styles.css";

const SIMULATOR_URL=import.meta.env.VITE_SIMULATOR_URL || "";
if(!SIMULATOR_URL) console.warn("VITE_SIMULATOR_URL is required. Set it in the project .env file before building the frontend.");

const navigation=[
 {section:"OPERATIONS",items:[{name:"Overview",icon:LayoutDashboard},{name:"Devices",icon:Server},{name:"Telemetry",icon:Activity},{name:"Alerts",icon:AlertTriangle},{name:"Incidents",icon:ClipboardCheck},{name:"AI Operations",icon:BrainCircuit},{name:"3D Room",icon:Box}]},
 {section:"MANAGE",items:[{name:"Reports",icon:FileBarChart},{name:"Settings",icon:Settings},{name:"Administration",icon:ShieldCheck},{name:"Support",icon:ExternalLink}]},
];

const defaultPreferences={voiceRepeatSeconds:10,showClimate:true,showClosureMetric:true,showDeviceMetric:true,showTelemetryMetric:true,showAlertMetric:true,showTicketMetric:true,showTrend:true,showAlertFeed:true,showTodayTickets:true,showHardware:false,showTickets:false,showAiSummary:false,reportLifecycle:true,reportAiPerformance:true,reportSeverity:true,reportHealth:true,reportFindings:true};
function savedPreferences(){try{return {...defaultPreferences,...JSON.parse(localStorage.getItem("vtab.preferences")||"{}")} }catch{return defaultPreferences}}

function Login(){
 const [error,setError]=useState("");
 const [isRegister,setIsRegister]=useState(false);
 const [showPassword,setShowPassword]=useState(false);
 const [isVerifying,setIsVerifying]=useState(false);
 const [pendingEmail,setPendingEmail]=useState("");
 
 async function submit(e){
  e.preventDefault();
  const f=new FormData(e.currentTarget);
  setError("");
  try{
   if(isRegister){
    await registerApi(f.get("name")||"New User", f.get("email"), f.get("password"));
    setPendingEmail(f.get("email"));
    setIsVerifying(true);
   }else{
    await login(f.get("email"),f.get("password"));
    location.reload();
   }
  }catch(x){
   let msg = x.message;
   try { msg = JSON.parse(x.message).detail || x.message; } catch {}
   setError(msg);
  }
 }
 
 async function handleVerify(e){
  e.preventDefault();
  const f=new FormData(e.currentTarget);
  setError("");
  try{
   await verifyApi(pendingEmail, f.get("code"));
   location.reload();
  }catch(x){
   let msg = x.message;
   try { msg = JSON.parse(x.message).detail || x.message; } catch {}
   setError(msg);
  }
 }
 return <main className="login auth-landscape-page">
   <div className="auth-landscape-card">
    <div className="auth-left">
     <div className="login-brand"><img src="/vtab-sentinel-logo.svg" alt="VTAB Sentinel"/><span><b>VTAB Sentinel</b><small>SENSE · REASON · RESOLVE</small></span></div>
     <div className="login-heading">
      <small>AI SERVER ROOM MONITORING</small>
      <h1>{isRegister ? "Join the Network" : "Server room intelligence"}</h1>
      <p>{isRegister ? "Create an account for secure operator access to monitoring systems." : "Secure operator access to real-time telemetry and AI operations."}</p>
     </div>
    </div>
    <form className={`auth-right ${isRegister ? 'is-registering' : ''}`} onSubmit={submit}>
     <h2>{isRegister ? "Create Account" : "Sign In"}</h2>
     {isRegister && <label className="slide-down auth-label">Full Name<input name="name" type="text" placeholder="John Doe" required={isRegister} className="auth-input"/></label>}
     <label className="auth-label">Email<input name="email" type="email" autoComplete="username" defaultValue={!isRegister?"admin@vtab.local":""} placeholder="operator@vtab.local" required className="auth-input"/></label>
     <label className="auth-label">Password
       <div className="password-wrapper">
         <input name="password" type={showPassword?"text":"password"} autoComplete="current-password" defaultValue={!isRegister?"Admin123!":""} placeholder="Enter your password" required minLength="8" className="auth-input"/>
         <button type="button" className="password-toggle" onClick={()=>setShowPassword(!showPassword)}>
           {showPassword ? <EyeOff size={16}/> : <Eye size={16}/>}
         </button>
       </div>
     </label>
     {error&&<div className="error alert-bounce" role="alert">{error}</div>}
     <button type="submit" className="auth-btn">{isRegister?"Create Account":"Sign In"}</button>
     <button type="button" className="auth-toggle-btn" onClick={()=>setIsRegister(!isRegister)}>{isRegister?"Already have an account? Sign in":"Need an account? Register"}</button>
    </form>
   </div>
   {isVerifying && (
      <div className="verify-overlay">
        <div className="verify-modal alert-bounce">
          <ShieldCheck size={48} className="verify-icon"/>
          <h3>Verify Your Email</h3>
          <p>We've sent a 6-digit verification code to <b>{pendingEmail}</b>.</p>
          <form onSubmit={handleVerify}>
            <input type="text" name="code" placeholder="Enter 6-digit code" maxLength="6" required className="auth-input verify-input"/>
            {error && <div className="error alert-bounce" role="alert">{error}</div>}
            <button type="submit" className="auth-btn">Verify & Sign In</button>
            <button type="button" className="auth-toggle-btn" onClick={()=>setIsVerifying(false)}>Cancel</button>
          </form>
        </div>
      </div>
    )}
  </main>
}

function UserManagement() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  
  async function loadUsers() {
    try { setUsers(await api("/auth/users")); } catch(e) { console.error(e); } finally { setLoading(false); }
  }
  useEffect(() => { loadUsers(); }, []);
  
  async function changeRole(id, role) {
    await api(`/auth/users/${id}/role`, { method: "PUT", body: JSON.stringify({ role_name: role }) });
    loadUsers();
  }
  async function deleteUser(id) {
    if(confirm("Delete this user?")) {
      await api(`/auth/users/${id}`, { method: "DELETE" });
      loadUsers();
    }
  }

  return (
    <div className="panel user-management-panel">
      <h2><LockKeyhole/> User Management</h2>
      <p>Manage system access and roles.</p>
      {loading ? <p>Loading users...</p> : (
        <div style={{overflowX:"auto"}}><table className="data-table">
          <thead><tr><th>User</th><th>Email</th><th>Role</th><th>Actions</th></tr></thead>
          <tbody>
            {users.map(u => (
              <tr key={u.id}>
                <td>{u.full_name}</td>
                <td>{u.email}</td>
                <td>
                  <select value={u.role} onChange={(e) => changeRole(u.id, e.target.value)} className="role-select">
                    <option value="viewer">Viewer</option>
                    <option value="engineer">Engineer</option>
                    <option value="facility_manager">Facility Manager</option>
                    <option value="admin">Admin</option>
                  </select>
                </td>
                <td>
                  <button onClick={() => deleteUser(u.id)} className="danger-button small-button">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table></div>
      )}
    </div>
  );
}

function App(){
 const [theme,setTheme]=useState(()=>localStorage.getItem("vtab.theme")||"dark");
 const [currentUser, setCurrentUser] = useState(null);
 const [page,setPage]=useState("Overview"),[summary,setSummary]=useState({}),[telemetry,setTelemetry]=useState([]),[alerts,setAlerts]=useState([]),[incidents,setIncidents]=useState([]),[devices,setDevices]=useState([]),[sensors,setSensors]=useState([]),[loading,setLoading]=useState(false),[menu,setMenu]=useState(false),[lastSync,setLastSync]=useState(null),[preferences,setPreferences]=useState(savedPreferences),[thresholds,setThresholds]=useState([]);
 const {enabled,speaking,lastMessage,toggle,announce,supported}=useVoice();const spoken=useRef(new Set(JSON.parse(sessionStorage.getItem("spokenAlerts")||"[]"))),incidentRef=useRef(incidents),summaryRef=useRef(summary),previousState=useRef(null);incidentRef.current=incidents;summaryRef.current=summary;
 async function loadThresholds(){try{setThresholds(await api("/settings/thresholds"))}catch(e){console.error(e)}}
 async function load(){setLoading(true);try{const [s,t,a,i,d,se]=await Promise.all([api("/reports/summary"),api("/telemetry/latest?limit=250"),api("/alerts"),api("/incidents"),api("/devices"),api("/master/sensors")]);setSummary(s);setTelemetry(t);setAlerts(a);setIncidents(i);setDevices(d);setSensors(se);setLastSync(new Date());const cutoff=Date.now()-45000;const fresh=a.filter(x=>new Date(x.event_timestamp||x.created_at).getTime()>=cutoff&&!spoken.current.has(x.id));const groups=Object.values(fresh.reduce((acc,x)=>{const key=x.core_event_id||x.id;(acc[key]??=[]).push(x);return acc},{}));groups.forEach(group=>{group.forEach(x=>spoken.current.add(x.id));const critical=group.some(x=>x.severity==="critical");const messages=[...new Set(group.map(x=>x.message||x.alert_type.replaceAll("_"," ")))];const actions=[...new Set(group.map(x=>x.recommendation).filter(Boolean))].slice(0,2);announce(`${critical?"Critical server-room incident":"Server-room attention required"}. ${messages.join(" ")} ${actions.length?`Recommended action: ${actions.join(" ")}`:""}`,{priority:critical?"critical":"normal",id:`event-${group[0].core_event_id||group[0].id}`})});sessionStorage.setItem("spokenAlerts",JSON.stringify([...spoken.current].slice(-200)))}catch(e){console.error(e)}finally{setLoading(false)}}
 useEffect(()=>{api("/auth/me").then(setCurrentUser).catch(()=>console.error("Failed to load user"));load();loadThresholds();const timer=setInterval(load,3000);const navigate=e=>setPage(e.detail);window.addEventListener("vtab:navigate",navigate);return()=>{clearInterval(timer);window.removeEventListener("vtab:navigate",navigate)}},[announce]);
 useEffect(()=>{
  const active=incidents.filter(x=>["open","assigned","acknowledged"].includes(x.status));
  const names=[...new Set(active.map(x=>(x.message||x.alert_type||"monitored incident").replace(/^Simulated\s+/i,"").replace(/\.$/,"")))];
  const current={alerts:summary.open_alerts||0,tickets:summary.open_incidents||0},previous=previousState.current;
  const incidentName=previous?.names?.[0]||"The monitored incident";
  if(previous&&current.alerts===0&&previous.alerts>0){
   announce(current.tickets?`${incidentName} has normalized. Automatic recovery verification is now running, and I will close the ticket when the checks pass.`:`${incidentName} has normalized, so I am closing the related ticket now. Recovery checks passed and monitoring continues normally.`,{id:`recovery-${Date.now()}`})
  }else if(previous&&current.alerts===0&&current.tickets===0&&previous.tickets>0){
   announce(`${incidentName} has normalized, so I am closing the related ticket now. The recovery is verified and the system is healthy.`,{id:`workflow-clear-${Date.now()}`})
  }
  previousState.current={...current,names};
 },[summary.open_alerts,summary.open_incidents,incidents,announce]);
 useEffect(()=>{const seconds=Number(preferences.voiceRepeatSeconds);if(!enabled||!seconds)return;const remind=()=>{const active=incidentRef.current.filter(x=>["open","assigned","acknowledged"].includes(x.status));if(!active.length)return;const environmentNormalized=(summaryRef.current.open_alerts||0)===0;if(environmentNormalized){announce(`The monitored incident is normal. Automatic recovery verification is in progress. Eligible internal tickets will close automatically; hardware and L3 tickets still require human approval.`,{id:`normalized-reminder-${Date.now()}`});return}const critical=active.some(x=>x.severity==="critical"),messages=[...new Set(active.slice(0,3).map(x=>x.message))];announce(`${critical?"Critical reminder":"Attention reminder"}. ${messages.join(" ")} ${active.length} active ticket${active.length===1?"":"s"} require operator action.`,{priority:critical?"critical":"normal",id:`ticket-reminder-${Date.now()}`})};const timer=setInterval(remind,seconds*1000);return()=>clearInterval(timer)},[enabled,preferences.voiceRepeatSeconds,announce]);
 function updatePreference(key,value){setPreferences(current=>{const next={...current,[key]:value};localStorage.setItem("vtab.preferences",JSON.stringify(next));return next})}
 const chart=telemetry.filter(x=>x.measurement_type==="temperature").slice().reverse().map(x=>({time:new Date(x.measurement_timestamp).toLocaleTimeString([], {hour:"2-digit",minute:"2-digit",second:"2-digit"}),value:x.value_numeric}));
 function navigate(name){setPage(name);setMenu(false)}
 async function closeTicket(id){if(!confirm("Close this ticket as successfully handled?"))return;await api(`/incidents/${id}`,{method:"PATCH",body:JSON.stringify({action:"close",note:"Closed by operator after successful verification"})});await load()}
 async function resetData(){if(!confirm("Delete all telemetry, alerts, tickets and AI test history? Devices and users will be preserved."))return;await api("/admin/test-data/reset",{method:"POST"});sessionStorage.removeItem("spokenAlerts");spoken.current.clear();await load();alert("Test data cleared. The next records will come from the simulator or hardware.")}
 function switchTheme(){const next=theme==="dark"?"light":"dark";setTheme(next);localStorage.setItem("vtab.theme",next)}
 const state=summary.system_state||((summary.open_alerts||0)>0?"alert":(summary.open_incidents||0)>0?"pending":"healthy");
 return <div data-theme={theme} className={`shell system-${state}`}><aside className={menu?"open":""}><button className="mobile-close" onClick={()=>setMenu(false)}><X/></button><div className="brand"><div><img src="/vtab-sentinel-logo.svg"/></div><b>VTAB <span>SENTINEL</span></b><small>SENSE · REASON · RESOLVE</small></div><nav>
    {navigation.map(sec=>
     <div key={sec.section}>
      <span>{sec.section}</span>
      {sec.items.filter(item => item.name !== "Administration" || currentUser?.role === "admin").map(item=><button key={item.name} className={page===item.name?"active":""} onClick={()=>setPage(item.name)}><item.icon size={17}/><span>{item.name}</span></button>)}
     </div>
    )}
   </nav><button className="logout" onClick={()=>{localStorage.clear();location.reload()}}><LogOut size={16}/> Sign out</button></aside><main><header><button className="mobile-menu" onClick={()=>setMenu(true)}><Menu/></button><div><small>AI SERVER ROOM MONITORING</small><h1>{page}</h1></div><div className="header-actions"><button className="theme-toggle" onClick={switchTheme} title={theme==="dark"?"Switch to light theme":"Switch to dark theme"} aria-label={theme==="dark"?"Switch to light theme":"Switch to dark theme"}>{theme==="dark"?<Sun/>:<Moon/>}<span>{theme==="dark"?"Light":"Dark"}</span></button><button title="Global setting: applies to every VTAB page" className={`voice-toggle ${enabled?"enabled":""} ${speaking?"speaking":""}`} onClick={toggle}>{enabled?<Volume2 size={17}/>:<VolumeX size={17}/>}<span><b>Voice intelligence</b><small>{!supported?"Not supported":speaking?"Speaking now":enabled?"Enabled system-wide":"Muted system-wide"}</small></span></button><button className="refresh" onClick={load}><RefreshCw size={16} className={loading?"spin":""}/> Refresh</button></div></header><section className={`system-banner ${state}`}>{state==="healthy"?<CheckCircle2/>:<AlertTriangle/>}<div><b>{state==="healthy"?"All monitored conditions are healthy":"Active server-room attention required"}</b><span>{state==="healthy"?"No open alerts or tickets. Monitoring continues in real time.":`${summary.open_incidents||0} open ticket(s) and ${summary.open_alerts||0} active alert(s).`}</span></div></section>
 {speaking&&<div className="voice-now"><div className="voice-wave"><i/><i/><i/><i/></div><div><b>VTAB voice intelligence</b><span>{lastMessage}</span></div><button onClick={toggle}><VolumeX/> Mute globally</button></div>}
 {page==="Overview"&&<OverviewCommandCenter summary={summary} devices={devices} telemetry={telemetry} alerts={alerts} incidents={incidents} chart={chart} thresholds={thresholds} lastSync={lastSync} preferences={preferences} navigate={setPage}/> }
 {page==="Devices"&&<DeviceInventory devices={devices} sensors={sensors} telemetry={telemetry} thresholds={thresholds} onRegistered={load}/>} 
 {page==="Telemetry"&&<TelemetryDashboard telemetry={telemetry} thresholds={thresholds}/>} 
 {page==="Alerts"&&<AlertFeed title="Alerts and recommended actions" rows={alerts}/>} 
 {page==="Incidents"&&<IncidentCenter incidents={incidents} onClose={closeTicket}/>} 
 {page==="AI Operations"&&<AITerminal/>}
 {page==="3D Room"&&<React.Suspense fallback={<section className="panel twin-loading"><Activity/><b>Loading interactive 3D room…</b></section>}><RoomDigitalTwin devices={devices} sensors={sensors} telemetry={telemetry} thresholds={thresholds} alerts={alerts} incidents={incidents}/></React.Suspense>}
 {page==="Reports"&&<OperationalReports summary={summary} alerts={alerts} incidents={incidents} preferences={preferences}/>} 
 {page==="Settings"&&<ApplicationSettings preferences={preferences} updatePreference={updatePreference} thresholds={thresholds} onSaved={loadThresholds}/>} 
 {page==="Support"&&<VTabSquarePromotional/>}
 {page==="Administration"&&<section className="admin-column-layout">
  {currentUser?.role === "admin" && <UserManagement />}
  <div className="panel clean-workspace-card"><Settings/><h2>Clean test workspace</h2><p>Remove telemetry, alerts, tickets and AI results while preserving users, devices and configuration.</p><button className="danger-button" onClick={resetData}><RefreshCw/> Clear all test data</button></div>
 </section>}
 </main><AgentAssistant/></div>
}

function thresholdRule(thresholds,name){return thresholds.find(r=>r.measurement_type===name&&r.enabled)}
function thresholdValue(thresholds,name,fallback){const rule=thresholdRule(thresholds,name);return Number(rule?.effective_threshold??rule?.threshold??fallback)}
function readingTriggered(value,rule){if(!rule)return false;const v=Number(value),t=Number(rule.effective_threshold??rule.threshold);if(rule.measurement_type==="temperature"&&v<Number(rule.effective_lower_threshold??18))return true;return rule.operator==="gt"?v>t:rule.operator==="gte"?v>=t:rule.operator==="lt"?v<t:rule.operator==="lte"?v<=t:v===t}
function OverviewMetric({icon,label,value,tone="normal",detail}){return <article className={`overview-metric ${tone}`}><i>{icon}</i><span><small>{label}</small><strong>{value}</strong><em>{detail}</em></span></article>}
function OverviewCommandCenter({summary,devices,telemetry,alerts,incidents,chart,thresholds,lastSync,preferences,navigate}){
 const activeTickets=incidents.filter(x=>["open","assigned","acknowledged"].includes(x.status)),closedTickets=incidents.filter(x=>["closed","resolved"].includes(x.status)),critical=activeTickets.filter(x=>x.severity==="critical"),latest=latestByType(telemetry),latestEvent=alerts[0],lastReading=telemetry[0],online=devices.filter(x=>["online","active","healthy"].includes((x.status||"").toLowerCase())).length,todayStart=new Date().setHours(0,0,0,0),openedToday=incidents.filter(x=>new Date(x.created_at||x.event_timestamp).getTime()>=todayStart).length,closedToday=incidents.filter(x=>["closed","resolved"].includes(x.status)&&new Date(x.closed_at||x.resolved_at||x.updated_at||x.created_at).getTime()>=todayStart).length,closureRate=incidents.length?Math.round(closedTickets.length/incidents.length*100):100;
 return <div className="overview-workspace">
  {preferences.showClimate&&<ClimateStatus/>}
  <section className="overview-metrics overview-primary-metrics">
   {preferences.showClosureMetric&&<OverviewMetric icon={<CheckCircle2/>} label="Incident closure rate" value={`${closureRate}%`} tone={activeTickets.length?"normal":"healthy"} detail={`${closedTickets.length} verified closure${closedTickets.length===1?"":"s"}`}/>} 
   {preferences.showAlertMetric&&<OverviewMetric icon={<AlertTriangle/>} label="Active alerts" value={summary.open_alerts||0} tone={(summary.open_alerts||0)?"warning":"healthy"} detail={(summary.open_alerts||0)?"Review required":"No active breach"}/>} 
   {preferences.showTicketMetric&&<OverviewMetric icon={<ClipboardCheck/>} label="Open tickets" value={activeTickets.length} tone={activeTickets.length?"warning":"healthy"} detail={`${closedTickets.length} closed overall`}/>} 
   {preferences.showDeviceMetric&&<OverviewMetric icon={<Server/>} label="Device fleet" value={summary.devices||devices.length} detail={`${online||devices.length} reporting`}/>} 
   {preferences.showTelemetryMetric&&<OverviewMetric icon={<Activity/>} label="Telemetry points" value={summary.telemetry_points||0} detail={lastReading?`Latest ${relativeTime(lastReading.measurement_timestamp)}`:"Waiting for data"}/>} 
  </section>
  {preferences.showTrend&&<LiveTrend chart={chart} lastSync={lastSync} thresholds={thresholds}/>} 
  {(preferences.showAlertFeed||preferences.showTodayTickets)&&<section className="overview-insight-grid">
   {preferences.showAlertFeed&&<article className={`overview-insight latest ${latestEvent?latestEvent.severity:"healthy"}`}><header><div><BellRing/><span><small>LATEST ALERT</small><h3>{latestEvent?latestEvent.alert_type.replaceAll("_"," "):"No alert recorded"}</h3></span></div><button onClick={()=>navigate("Alerts")}>Open alerts</button></header>{latestEvent?<><p>{latestEvent.message||latestEvent.recommendation}</p><footer><b>{(latestEvent.incident_status||latestEvent.status||"open").toUpperCase()}</b><span>{relativeTime(latestEvent.event_timestamp||latestEvent.created_at)}</span></footer></>:<div className="module-empty"><CheckCircle2/><b>Environment remains clear</b><span>The next validated alert will appear here.</span></div>}</article>}
   {preferences.showTodayTickets&&<article className={`overview-insight today ${openedToday?"attention":"healthy"}`}><header><div><ClipboardCheck/><span><small>TODAY'S WORKFLOW</small><h3>Ticket activity</h3></span></div><button onClick={()=>navigate("Incidents")}>Open incidents</button></header><div className="today-ticket-kpis"><span><b>{openedToday}</b><small>opened today</small></span><span className="closed"><b>{closedToday}</b><small>closed today</small></span><span><b>{critical.length}</b><small>critical open</small></span></div><footer>{activeTickets.length?`${activeTickets.length} ticket(s) still require action`:"All current tickets are complete"}</footer></article>}
  </section>}
  {(preferences.showHardware||preferences.showTickets||preferences.showAiSummary)&&<section className="overview-secondary-grid">
   {preferences.showHardware&&<article className="overview-module fleet"><header><div><Server/><span><small>FLEET & INGESTION</small><h3>Hardware status</h3></span></div><button onClick={()=>navigate("Devices")}>Open devices</button></header><div className="module-kpis"><span><b>{devices.length}</b> registered controllers</span><span><b>{telemetry.length}</b> recent records loaded</span><span><b>{latest.temperature?.value_numeric??"—"}°C</b> current temperature</span></div><footer>{lastReading?`Last database write ${relativeTime(lastReading.measurement_timestamp)}`:"Awaiting the first validated sensor packet"}</footer></article>}
   {preferences.showTickets&&<article className={`overview-module incidents ${activeTickets.length?"attention":"healthy"}`}><header><div><ClipboardCheck/><span><small>INCIDENT WORKFLOW</small><h3>Ticket posture</h3></span></div><button onClick={()=>navigate("Incidents")}>Open incidents</button></header><div className="module-kpis"><span><b>{activeTickets.length}</b> currently open</span><span><b>{critical.length}</b> critical priority</span><span><b>{closedTickets.length}</b> completed lifecycle</span></div><footer>{activeTickets[0]?`${activeTickets[0].message||activeTickets[0].alert_type} · ${relativeTime(activeTickets[0].created_at)}`:"No tickets require operator action"}</footer></article>}
   {preferences.showAiSummary&&<article className="overview-module ai"><header><div><BrainCircuit/><span><small>AI OPERATIONS</small><h3>Reasoning pipeline</h3></span></div><button onClick={()=>navigate("AI Operations")}>Open AI Operations</button></header><div className="ai-stage-mini">{["Baseline","Anomaly","Forecast","Risk","Explain"].map(x=><span key={x}><i/><b>{x}</b></span>)}</div><footer>Five-stage model flow, diagnostics and governed recovery evidence</footer></article>}
  </section>}
 </div>
}function LiveTrend({chart,lastSync,thresholds}){const limit=thresholdValue(thresholds,"temperature",30),danger=readingTriggered(chart.at(-1)?.value,thresholdRule(thresholds,"temperature")),color=danger?"#ff5d74":"#2ee6c5";return <section className={`panel live-trend ${danger?"danger":"healthy"}`}><div className="section-heading"><div><Activity/><div><h3>Live temperature trend</h3><p>{thresholdRule(thresholds,"temperature")?.mode==="auto"?"Auto":"Manual"} operating limit: {limit}°C · mode and safety ceiling are visible in Settings</p></div></div><span className={`live-pill ${danger?"down":""}`}><i/> {danger?"HAZARD":"LIVE"} · {lastSync?lastSync.toLocaleTimeString():"connecting"}</span></div>{chart.length?<div className="chart"><ResponsiveContainer><AreaChart data={chart}><defs><linearGradient id="temperatureFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={color} stopOpacity={.4}/><stop offset="100%" stopColor={color} stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="#143247" strokeDasharray="4 5"/><XAxis dataKey="time" minTickGap={30} stroke="#638298" fontSize={10}/><YAxis domain={[10,55]} stroke="#638298" fontSize={10} unit="°"/><Tooltip contentStyle={{background:"#081422",border:`1px solid ${color}`}}/><ReferenceLine y={limit} stroke="#ffbd5a" strokeDasharray="5 4" label={{value:`Alert ${limit}°C`,fill:"#ffbd5a",fontSize:10}}/><Area type="monotone" dataKey="value" name="Temperature °C" stroke={color} fill="url(#temperatureFill)" strokeWidth={3} dot={chart.length<4?{r:6,fill:color}:false} activeDot={{r:7,fill:color}} isAnimationActive/></AreaChart></ResponsiveContainer></div>:<div className="chart-empty"><span className="pulse-ring"><Activity/></span><b>Waiting for the first ESP32 transmission</b></div>}</section>}

const hardwareMap={temperature:"DHT22 / AM2302",humidity:"DHT22 / AM2302",water_leak:"HW-038 water probe",door_open:"MC-38 magnetic contact",smoke:"MQ-2 smoke sensor"};
function latestByType(rows){return rows.reduce((out,row)=>{if(!out[row.measurement_type])out[row.measurement_type]=row;return out},{})}
function DeviceInventory({devices,sensors,telemetry,thresholds,onRegistered}){
 const sensorTypes=["temperature","humidity","water_leak","door_open","smoke"],[showAdd,setShowAdd]=useState(false),[saving,setSaving]=useState(false),[result,setResult]=useState(""),[componentTarget,setComponentTarget]=useState(""),[componentType,setComponentType]=useState("water_leak"),[componentQty,setComponentQty]=useState(1);
 const [draft,setDraft]=useState({name:"ESP32 Sentinel 02",hardware_type:"ESP32-WROOM-32",sensor_types:["temperature","humidity"]});
 function toggleSensor(name){setDraft(d=>({...d,sensor_types:d.sensor_types.includes(name)?d.sensor_types.filter(x=>x!==name):[...d.sensor_types,name]}))}
 async function addComponent(e,device){e.preventDefault();setSaving(true);setResult("");try{const response=await api(`/devices/${device.id}/components`,{method:"POST",body:JSON.stringify({sensor_type:componentType,quantity:Number(componentQty)})});setResult(`${response.created.length} ${componentType.replaceAll("_"," ")} component(s) added to ${device.name}. They are available in Test Lab using simulation fallback.`);setComponentTarget("");await onRegistered()}catch(error){setResult(error.message)}finally{setSaving(false)}} async function register(e){e.preventDefault();if(!draft.sensor_types.length){setResult("Select at least one component");return}setSaving(true);setResult("");try{const device=await api("/devices/register",{method:"POST",body:JSON.stringify(draft)});setResult(`${device.name} registered. It is now available in Test Lab using simulation fallback.`);setShowAdd(false);setDraft({name:`ESP32 Sentinel ${String(devices.length+2).padStart(2,"0")}`,hardware_type:"ESP32-WROOM-32",sensor_types:["temperature","humidity"]});await onRegistered()}catch(error){setResult(error.message)}finally{setSaving(false)}}
 return <><section className="panel equipment-head fleet-head"><div><Cpu/><div><h2>Registered device fleet</h2><p>Every controller has independent components, MQTT identity and hardware/simulation state</p></div></div><div><span className="live-pill"><i/> {devices.length} DEVICE{devices.length===1?"":"S"}</span><button className="primary" onClick={()=>setShowAdd(v=>!v)}>{showAdd?"Cancel":"Add device"}</button></div></section>{showAdd&&<form className="panel device-registration" onSubmit={register}><div><small>NEW DEVICE</small><h3>Register a device and its components</h3><p>The device appears automatically in Test Lab. Until its first physical MQTT packet, simulation is selected by default.</p></div><label>Device name<input value={draft.name} onChange={e=>setDraft(d=>({...d,name:e.target.value}))}/></label><label>Board profile<select value={draft.hardware_type} onChange={e=>setDraft(d=>({...d,hardware_type:e.target.value}))}><option>ESP32-WROOM-32</option><option>ESP32 DevKit V1</option><option>ESP32-S3 DevKitC</option><option>ESP32-C3 DevKitM</option></select></label><fieldset><legend>Installed components</legend>{sensorTypes.map(type=><label key={type}><input type="checkbox" checked={draft.sensor_types.includes(type)} onChange={()=>toggleSensor(type)}/><span>{type.replaceAll("_"," ")}<small>{hardwareMap[type]}</small></span></label>)}</fieldset><button className="primary" disabled={saving}>{saving?"Registering…":"Register device"}</button></form>}{result&&<div className={`device-result ${result.includes("registered")?"ok":""}`}>{result}</div>}<section className="device-fleet">{devices.map(device=>{const online=device.last_seen_at&&(Date.now()-new Date(device.last_seen_at).getTime()<20000),assigned=sensors.filter(s=>s.device_id===device.id),deviceRows=telemetry.filter(t=>t.device_id===device.id),latest=latestByType(deviceRows);return <article className={`device-unit ${online?"online":"simulated"}`} key={device.id}><header><Cpu/><div><small>EDGE CONTROLLER · {device.id.slice(0,8)}</small><h3>{device.name}</h3><span>{device.hardware_type} · firmware {device.firmware_version||"not reported"}</span></div><em>{online?"HARDWARE ONLINE":"SIMULATION FALLBACK"}</em></header><div className="device-identity"><span>Firmware DEVICE_ID</span><code>{device.id}</code><small>Copy this UUID into the matching ESP32 firmware configuration.</small><button onClick={()=>setComponentTarget(componentTarget===device.id?"":device.id)}>+ Add component to this controller</button></div>{componentTarget===device.id&&<form className="component-registration" onSubmit={e=>addComponent(e,device)}><label>Component<select value={componentType} onChange={e=>setComponentType(e.target.value)}>{sensorTypes.map(type=><option value={type} key={type}>{type.replaceAll("_"," ")} · {hardwareMap[type]}</option>)}</select></label><label>Quantity<input type="number" min="1" max="10" value={componentQty} onChange={e=>setComponentQty(e.target.value)}/></label><button className="primary" disabled={saving}>{saving?"Adding…":"Add to existing circuit"}</button><small>Each new component receives a unique sensor ID and starts in simulation until physically reported.</small></form>}<div className="device-components">{assigned.length?assigned.map(sensor=>{const type=sensor.sensor_type,row=deviceRows.find(item=>item.sensor_id===sensor.id),rule=thresholdRule(thresholds,type),triggered=row&&readingTriggered(row.value_numeric,rule),number=assigned.filter(item=>item.sensor_type===type).findIndex(item=>item.id===sensor.id)+1;return <div className={triggered?"triggered":""} key={sensor.id}><Activity/><span><b>{type.replaceAll("_"," ")} sensor {number}</b><small>{hardwareMap[type]} · {row?.source_mode||"simulated"}</small></span><strong>{row?`${row.value_numeric} ${row.unit||""}`:"—"}</strong></div>}):<div className="empty-state">No components assigned</div>}</div><footer><span>Last physical/telemetry packet: {relativeTime(device.last_seen_at)}</span><a href={SIMULATOR_URL} target="_blank" rel="noreferrer">Open in Test Lab</a></footer></article>})}</section></>
}

function TelemetryDashboard({telemetry,thresholds}){
 const latest=latestByType(telemetry),series={};telemetry.slice().reverse().forEach(r=>{const key=r.measurement_timestamp;(series[key]??={time:new Date(key).toLocaleTimeString([], {hour:"2-digit",minute:"2-digit",second:"2-digit"})})[r.measurement_type]=r.value_numeric;if(r.measurement_type==="water_leak"&&r.raw_adc!=null)series[key].water_adc=r.raw_adc;if(r.measurement_type==="smoke"&&r.raw_adc!=null)series[key].mq2_adc=r.raw_adc});const chart=Object.values(series).slice(-60),tempLimit=thresholdValue(thresholds,"temperature",30),tempMinimum=Number(thresholdRule(thresholds,"temperature")?.effective_lower_threshold??18),humidityLimit=thresholdValue(thresholds,"humidity",70);
 return <><section className="sensor-kpis">{["temperature","humidity","water_leak","door_open","smoke"].map(type=>{const row=latest[type],active=row&&readingTriggered(row.value_numeric,thresholdRule(thresholds,type));return <article className={active?"active":""} key={type}><small>{type.replaceAll("_"," ")}</small><strong>{row?`${row.value_numeric} ${row.unit||""}`:"—"}</strong>{row?.raw_adc!=null&&<b>ADC raw {row.raw_adc}</b>}<span>{row?`${row.source_mode||"unknown"} · ${relativeTime(row.measurement_timestamp)}`:"Awaiting data"}</span></article>})}</section>
 <section className="panel"><div className="section-heading"><div><Activity/><div><h3>Temperature and humidity</h3><p>Active safe band: temperature {tempMinimum}–{tempLimit}°C ({thresholdRule(thresholds,"temperature")?.mode||"manual"}) and humidity {humidityLimit}% RH ({thresholdRule(thresholds,"humidity")?.mode||"manual"})</p></div></div></div>{chart.length?<div className="chart large"><ResponsiveContainer><LineChart data={chart}><CartesianGrid stroke="#143247" strokeDasharray="4 5"/><XAxis dataKey="time" minTickGap={35} stroke="#638298" fontSize={10}/><YAxis domain={[0,100]} stroke="#638298" fontSize={10}/><Tooltip contentStyle={{background:"#081422",border:"1px solid #244565"}}/><Legend/><ReferenceLine y={humidityLimit} stroke="#ffbd5a" strokeDasharray="4 4" label={{value:`Humidity ${humidityLimit}%`,fill:"#ffbd5a",fontSize:9}}/><ReferenceLine y={tempMinimum} stroke="#37e1ed" strokeDasharray="4 4" label={{value:`Minimum ${tempMinimum}°C`,fill:"#37e1ed",fontSize:9}}/><ReferenceLine y={tempLimit} stroke="#ff6e83" strokeDasharray="4 4" label={{value:`Maximum ${tempLimit}°C`,fill:"#ff6e83",fontSize:9}}/><Line type="monotone" dataKey="temperature" name="Temperature °C" stroke="#ff6e83" strokeWidth={3} connectNulls dot={false}/><Line type="monotone" dataKey="humidity" name="Humidity % RH" stroke="#37e1ed" strokeWidth={3} connectNulls dot={false}/></LineChart></ResponsiveContainer></div>:<div className="chart-empty"><Activity/><b>No telemetry received yet</b></div>}</section>
 <section className="panel"><div className="section-heading"><div><Droplets/><div><h3>Water and MQ-2 analog evidence</h3><p>Exact ESP32 ADC readings, separate from normalized 0/1 alert values</p></div></div></div>{chart.some(x=>x.water_adc!=null||x.mq2_adc!=null)?<div className="chart large"><ResponsiveContainer><LineChart data={chart}><CartesianGrid stroke="#143247" strokeDasharray="4 5"/><XAxis dataKey="time" minTickGap={35} stroke="#638298" fontSize={10}/><YAxis domain={[0,4095]} stroke="#638298" fontSize={10}/><Tooltip contentStyle={{background:"#081422",border:"1px solid #244565"}}/><Legend/><Line type="monotone" dataKey="water_adc" name="Water sensor raw ADC" stroke="#37e1ed" strokeWidth={3} connectNulls dot={false}/><Line type="monotone" dataKey="mq2_adc" name="MQ-2 raw ADC" stroke="#ff6e83" strokeWidth={3} connectNulls dot={false}/></LineChart></ResponsiveContainer></div>:<div className="chart-empty"><Droplets/><b>Waiting for ESP32 raw ADC metadata</b><p>Upload firmware 4.4.1 or newer.</p></div>}</section>
 <section className="panel"><div className="section-heading"><div><DoorOpen/><div><h3>Door access state</h3><p>Dedicated open/closed event history</p></div></div></div>{chart.length?<div className="chart binary-chart"><ResponsiveContainer><LineChart data={chart}><CartesianGrid stroke="#143247" strokeDasharray="4 5"/><XAxis dataKey="time" minTickGap={35} stroke="#638298" fontSize={10}/><YAxis domain={[0,1]} ticks={[0,1]} tickFormatter={v=>v?"OPEN":"CLOSED"} width={65} stroke="#638298" fontSize={9}/><Tooltip formatter={v=>v?"OPEN":"CLOSED"} contentStyle={{background:"#081422",border:"1px solid #244565"}}/><Line type="stepAfter" dataKey="door_open" name="Door contact" stroke="#ffbd5a" strokeWidth={3} connectNulls dot/></LineChart></ResponsiveContainer></div>:<div className="chart-empty"><DoorOpen/><b>No door events yet</b></div>}</section><Table title="Validated telemetry records" rows={telemetry} columns={["measurement_type","value_numeric","raw_adc","source_mode","unit","quality_status","measurement_timestamp"]}/></>}

function diagnosticText(value){if(value===null||value===undefined)return "No details";if(typeof value!=="object")return String(value);return Object.entries(value).map(([key,item])=>`${key.replaceAll("_"," ")}: ${item}`).join(" · ")}
function OperationalReports({summary,alerts,incidents,preferences}){
 const [diagnostics,setDiagnostics]=useState(null),[ai,setAi]=useState([]),[error,setError]=useState("");
 useEffect(()=>{Promise.all([api("/system/diagnostics"),api("/ai/results?limit=100")]).then(([d,a])=>{setDiagnostics(d);setAi(a);setError("")}).catch(e=>setError(e.message))},[summary.telemetry_points]);
 const severity=["critical","warning","info"].map(name=>({name,count:alerts.filter(a=>a.severity===name).length})),components=diagnostics?.components||[],closed=incidents.filter(i=>["closed","resolved"].includes(i.status)).length,open=incidents.filter(i=>!["closed","resolved"].includes(i.status)).length,closureRate=incidents.length?Math.round(closed/incidents.length*100):100,healthyServices=components.filter(c=>c.status==="healthy").length,backlog=diagnostics?.evidence?.ai_processing_backlog||0;
 const dateKey=value=>{const d=new Date(value);return Number.isNaN(d.getTime())?"":`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`},days=Array.from({length:7},(_,index)=>{const d=new Date();d.setHours(0,0,0,0);d.setDate(d.getDate()-(6-index));return {key:dateKey(d),label:d.toLocaleDateString([], {weekday:"short"})}}),lifecycleTrend=days.map(day=>({...day,opened:incidents.filter(x=>dateKey(x.created_at||x.event_timestamp)===day.key).length,closed:incidents.filter(x=>["closed","resolved"].includes(x.status)&&dateKey(x.closed_at||x.resolved_at||x.updated_at||x.created_at)===day.key).length})),aiTrend=days.map(day=>({...day,runs:ai.filter(x=>dateKey(x.analysis_timestamp)===day.key).length,elevated:ai.filter(x=>dateKey(x.analysis_timestamp)===day.key&&["high","critical"].includes((x.risk?.level||"").toLowerCase())).length})),completedAI=ai.filter(x=>["completed","success","healthy"].includes((x.status||"").toLowerCase())).length,aiCompletion=ai.length?Math.round(completedAI/ai.length*100):100,anomalies=ai.filter(x=>x.anomaly?.is_anomaly||Number(x.anomaly?.score)>=3).length,highRisk=ai.filter(x=>["high","critical"].includes((x.risk?.level||"").toLowerCase())).length;
 return <><section className="report-hero modern-report"><div><FileBarChart/><span><small>EXECUTIVE + ENGINEERING REPORT</small><h2>Operational intelligence report</h2><p>Trends, ticket outcomes, AI performance and platform evidence in one decision workspace.</p></span></div><b className={diagnostics?.status||"collecting"}>{diagnostics?.status||"collecting"}</b></section>{error&&<div className="terminal-error"><AlertTriangle/>Unable to load diagnostics: {error}</div>}
 <section className="report-overview-band"><article><Activity/><span><small>STORED READINGS</small><b>{summary.telemetry_points||0}</b><em>Timescale evidence</em></span></article><article><AlertTriangle/><span><small>ACTIVE ALERTS</small><b>{summary.open_alerts||0}</b><em>Current risk posture</em></span></article><article><ClipboardCheck/><span><small>OPEN / CLOSED</small><b>{open} / {closed}</b><em>{closureRate}% closure rate</em></span></article><article><BrainCircuit/><span><small>AI COMPLETION</small><b>{aiCompletion}%</b><em>{ai.length} persisted analyses</em></span></article><article><ShieldCheck/><span><small>SERVICE HEALTH</small><b>{healthyServices}/{components.length||"—"}</b><em>{backlog} AI backlog</em></span></article></section>
 <section className="report-trend-grid">
  {preferences.reportLifecycle&&<article className="panel report-trend lifecycle"><div className="section-heading"><div><ClipboardCheck/><div><h3>Alert and ticket handling trend</h3><p>Tickets opened versus verified closures during the last seven days</p></div></div><span>{closureRate}% CLOSED</span></div><div className="report-trend-chart"><ResponsiveContainer><BarChart data={lifecycleTrend} margin={{top:12,right:12,left:-24,bottom:0}}><CartesianGrid stroke="#143247" strokeDasharray="4 5"/><XAxis dataKey="label" stroke="#638298"/><YAxis allowDecimals={false} stroke="#638298"/><Tooltip contentStyle={{background:"#081422",border:"1px solid #244565"}}/><Legend/><Bar dataKey="opened" name="Tickets opened" fill="#ffb24a" radius={[5,5,0,0]}/><Bar dataKey="closed" name="Tickets closed" fill="#2ee6c5" radius={[5,5,0,0]}/></BarChart></ResponsiveContainer></div><footer><span><b>{open}</b> require action</span><span><b>{closed}</b> completed</span><span><b>{incidents.length}</b> total workflows</span></footer></article>}
  {preferences.reportAiPerformance&&<article className="panel report-trend ai-performance"><div className="section-heading"><div><BrainCircuit/><div><h3>AI performance summary</h3><p>Analysis throughput, elevated-risk decisions and processing health</p></div></div><span className={backlog?"attention":"healthy"}>{backlog?`${backlog} BACKLOG`:"PIPELINE CLEAR"}</span></div><div className="ai-performance-kpis"><span><b>{aiCompletion}%</b><small>completed</small></span><span><b>{anomalies}</b><small>anomalies</small></span><span><b>{highRisk}</b><small>high risk</small></span><span><b>{backlog}</b><small>backlog</small></span></div><div className="report-trend-chart compact"><ResponsiveContainer><LineChart data={aiTrend} margin={{top:10,right:14,left:-24,bottom:0}}><CartesianGrid stroke="#143247" strokeDasharray="4 5"/><XAxis dataKey="label" stroke="#638298"/><YAxis allowDecimals={false} stroke="#638298"/><Tooltip contentStyle={{background:"#081422",border:"1px solid #244565"}}/><Legend/><Line type="monotone" dataKey="runs" name="AI analyses" stroke="#37e1ed" strokeWidth={3} dot/><Line type="monotone" dataKey="elevated" name="Elevated risk" stroke="#ff6e83" strokeWidth={2} dot/></LineChart></ResponsiveContainer></div></article>}
 </section>
 <div className="report-workspace">{preferences.reportSeverity&&<section className="panel report-visual"><div className="section-heading"><div><AlertTriangle/><div><h3>Alert severity distribution</h3><p>Risk mix across the retained operational record</p></div></div><span>{alerts.length} TOTAL</span></div><div className="report-chart"><ResponsiveContainer><BarChart data={severity} margin={{top:10,right:8,left:-18,bottom:0}}><CartesianGrid stroke="#143247" strokeDasharray="4 5"/><XAxis dataKey="name" stroke="#638298"/><YAxis allowDecimals={false} stroke="#638298"/><Tooltip contentStyle={{background:"#081422",border:"1px solid #244565"}}/><Bar dataKey="count" fill="#37e1ed" radius={[7,7,0,0]}/></BarChart></ResponsiveContainer></div></section>}{preferences.reportHealth&&<section className="panel report-services"><div className="section-heading"><div><ShieldCheck/><div><h3>Backend and service health</h3><p>Live diagnostic result and response evidence</p></div></div><span>{healthyServices} HEALTHY</span></div><div className="health-list dense">{components.length?components.map((c,i)=><article key={c.name||i}><i className={c.status==="healthy"?"ok":"bad"}/><span><b>{c.name||c.component}</b><small>{diagnosticText(c.detail||c.message||c.status)}</small></span><em>{c.status}</em></article>):<div className="empty-state">Collecting diagnostic evidence…</div>}</div></section>}</div>
 {preferences.reportFindings&&<section className="panel report-findings"><div className="section-heading"><div><BrainCircuit/><div><h3>Decision-ready findings</h3><p>Concise operational outcomes for managers and engineers</p></div></div></div><div className="findings"><p className={open?"attention":"healthy"}><b>{open}</b><span>tickets require action</span><small>{open?"Investigation workflow remains open":"All known tickets are complete"}</small></p><p><b>{closureRate}%</b><span>alerts handled</span><small>{closed} verified ticket closures</small></p><p><b>{aiCompletion}%</b><span>AI analysis completion</span><small>{ai.length} database-linked runs evaluated</small></p><p className={backlog?"attention":"healthy"}><b>{backlog}</b><span>AI processing backlog</span><small>{backlog?"Engineering review recommended":"No telemetry is waiting for AI"}</small></p></div></section>}</>
}async function downloadSystemLog(){const token=localStorage.getItem("token"),response=await fetch(`${API_URL}/admin/logs/export`,{headers:{Authorization:`Bearer ${token}`}});if(!response.ok)throw new Error("Unable to export system log");const blob=await response.blob(),link=document.createElement("a"),disposition=response.headers.get("Content-Disposition")||"";link.href=URL.createObjectURL(blob);link.download=disposition.match(/filename="?([^";]+)"?/)?.[1]||`vtab-sentinel-system-log-${new Date().toISOString().slice(0,10)}.csv`;link.click();URL.revokeObjectURL(link.href)}
function ApplicationSettings({preferences,updatePreference,thresholds,onSaved}){
 const [exportMessage,setExportMessage]=useState(""),[draft,setDraft]=useState({}),[saving,setSaving]=useState(""),[results,setResults]=useState({});
 useEffect(()=>setDraft(Object.fromEntries(thresholds.map(r=>[r.measurement_type,{...r}]))),[thresholds]);
 async function download(){try{setExportMessage("Preparing CSV...");await downloadSystemLog();setExportMessage("CSV downloaded successfully")}catch(error){setExportMessage(error.message)}}
 function change(name,key,value){setDraft(d=>({...d,[name]:{...d[name],[key]:value}}));setResults(r=>({...r,[name]:""}))}
 function adjust(name,amount){const current=Number(draft[name]?.threshold||0);change(name,"threshold",String(Math.round((current+amount)*10)/10))}
 async function save(name){const rule=draft[name],value=Number(rule.threshold);if(!Number.isFinite(value)){setResults(r=>({...r,[name]:"Enter a valid number"}));return}setSaving(name);setResults(r=>({...r,[name]:""}));try{await api(`/settings/thresholds/${name}`,{method:"PUT",body:JSON.stringify({measurement_type:name,operator:rule.operator,threshold:value,severity:rule.severity,enabled:rule.enabled,mode:rule.mode||"manual"})});setResults(r=>({...r,[name]:`Saved: ${name.replaceAll("_"," ")} ${rule.operator} ${value}`}));await onSaved()}catch(error){setResults(r=>({...r,[name]:`Save failed: ${error.message}`}))}finally{setSaving("")}}
 return <><section className="settings-hero"><SlidersHorizontal/><div><small>CONFIGURATION WORKSPACE</small><h2>Monitoring, experience and recovery policy</h2><p>Organized controls for sensor rules, operator preferences, AI safeguards and evidence export.</p></div></section><nav className="settings-index" aria-label="Settings sections"><a href="#monitoring-rules"><AlertTriangle/><span><b>Monitoring rules</b><small>Thresholds and sensor modes</small></span></a><a href="#operator-experience"><LayoutDashboard/><span><b>Operator experience</b><small>Voice and Overview content</small></span></a><a href="#automation-policy"><BrainCircuit/><span><b>Automation policy</b><small>AI recovery safeguards</small></span></a><a href="#data-tools"><FileBarChart/><span><b>Data and logs</b><small>Export system evidence</small></span></a></nav>
 <section id="monitoring-rules" className="settings-group"><header><div><AlertTriangle/><span><small>01 · MONITORING RULES</small><h3>Sensor alert thresholds</h3><p>Manual or adaptive limits are saved independently for every sensor channel.</p></span></div><em>{Object.keys(draft).length} RULES</em></header><div className="threshold-grid">{Object.keys(draft).map(name=>{const r=draft[name],step=["water_leak","door_open","smoke"].includes(name)?1:.5;return <article key={name}><div className="threshold-card-title"><b>{name.replaceAll("_"," ")}</b><span className={r.enabled?"enabled":"disabled"}>{r.enabled?"ACTIVE":"DISABLED"}</span></div>{["temperature","humidity"].includes(name)&&<div className="adaptive-policy"><span>THRESHOLD MODE</span><div className="mode-choice"><button type="button" className={(r.mode||"manual")==="manual"?"active":""} onClick={()=>change(name,"mode","manual")}>Manual</button><button type="button" className={r.mode==="auto"?"active":""} onClick={()=>change(name,"mode","auto")}>Auto</button></div><small>{r.mode==="auto"?(r.learning_status==="active"?"Using the learned normal baseline.":`Learning ${r.sample_count||0}/8 valid readings.`):"Uses exactly the configured value."}</small><small>Active limit <strong>{r.effective_threshold??r.threshold}</strong>{r.mode==="auto"&&r.baseline!=null?<> · baseline <strong>{r.baseline}</strong></>:null}</small>{r.effective_lower_threshold!=null&&<small>Temperature safe band <strong>{r.effective_lower_threshold}–{r.effective_threshold??r.threshold}</strong> · critical floor <strong>{r.hard_safety_floor??15}</strong></small>}{r.hard_safety_ceiling!=null&&<small>Safety ceiling <strong>{r.hard_safety_ceiling}</strong></small>}</div>}<div className="threshold-fields"><label>Condition<select value={r.operator} onChange={e=>change(name,"operator",e.target.value)}><option value="gt">Above</option><option value="gte">At or above</option><option value="eq">Equals</option><option value="lt">Below</option><option value="lte">At or below</option></select></label><label>{r.mode==="auto"?"Minimum / fallback":"Trigger value"}<div className="threshold-stepper"><button type="button" onClick={()=>adjust(name,-step)} aria-label={`Decrease ${name}`}>−</button><input type="text" inputMode="decimal" value={r.threshold} onChange={e=>change(name,"threshold",e.target.value.replace(/[^0-9.-]/g,""))}/><button type="button" onClick={()=>adjust(name,step)} aria-label={`Increase ${name}`}>+</button></div></label><label>Severity<select value={r.severity} onChange={e=>change(name,"severity",e.target.value)}><option value="warning">Warning</option><option value="critical">Critical</option></select></label></div><SettingToggle label="Rule enabled" value={r.enabled} onChange={v=>change(name,"enabled",v)}/><button className="primary threshold-save" disabled={saving===name} onClick={()=>save(name)}>{saving===name?"Saving…":"Save threshold"}</button>{results[name]&&<small className={results[name].startsWith("Saved")?"save-result ok":"save-result error"}>{results[name]}</small>}</article>})}</div></section>
 <section id="operator-experience" className="settings-group overview-composer"><header><div><LayoutDashboard/><span><small>02 · OPERATOR EXPERIENCE</small><h3>Dashboard composition and operator behavior</h3><p>Tick the modules operators need. Overview automatically reflows and aligns the selected content.</p></span></div><em>LIVE LAYOUT</em></header><div className="composer-summary"><div><LayoutDashboard/><span><b>Overview layout composer</b><small>Changes are saved in this browser and applied immediately without a reload.</small></span></div><p><CheckCircle2/><span><b>Automatic spacing</b><small>Cards resize from desktop to mobile</small></span></p><p><ShieldCheck/><span><b>No data loss</b><small>Hidden modules continue collecting evidence</small></span></p></div><div className="overview-option-grid">
  <OverviewOption icon={Activity} label="Climate safety banner" description="Temperature, humidity and active safety margins" value={preferences.showClimate} onChange={v=>updatePreference("showClimate",v)}/>
  <OverviewOption icon={CheckCircle2} label="Closure-rate card" description="Verified incident completion percentage" value={preferences.showClosureMetric} onChange={v=>updatePreference("showClosureMetric",v)}/>
  <OverviewOption icon={AlertTriangle} label="Active-alert card" description="Current alert count and risk posture" value={preferences.showAlertMetric} onChange={v=>updatePreference("showAlertMetric",v)}/>
  <OverviewOption icon={ClipboardCheck} label="Open-ticket card" description="Current tickets and completed total" value={preferences.showTicketMetric} onChange={v=>updatePreference("showTicketMetric",v)}/>
  <OverviewOption icon={Server} label="Device card" description="Registered and reporting controllers" value={preferences.showDeviceMetric} onChange={v=>updatePreference("showDeviceMetric",v)}/>
  <OverviewOption icon={Activity} label="Telemetry card" description="Stored points and most recent write" value={preferences.showTelemetryMetric} onChange={v=>updatePreference("showTelemetryMetric",v)}/>
  <OverviewOption icon={Activity} label="Live temperature trend" description="Real-time chart with active threshold" value={preferences.showTrend} onChange={v=>updatePreference("showTrend",v)}/>
  <OverviewOption icon={BellRing} label="Latest alert" description="Compact latest alert after the trend" value={preferences.showAlertFeed} onChange={v=>updatePreference("showAlertFeed",v)}/>
  <OverviewOption icon={ClipboardCheck} label="Today's ticket activity" description="Opened, closed and critical today" value={preferences.showTodayTickets} onChange={v=>updatePreference("showTodayTickets",v)}/>
  <OverviewOption icon={Cpu} label="Hardware detail" description="Expanded fleet and ingestion evidence" value={preferences.showHardware} onChange={v=>updatePreference("showHardware",v)}/>
  <OverviewOption icon={ClipboardCheck} label="Ticket posture detail" description="Expanded incident workflow summary" value={preferences.showTickets} onChange={v=>updatePreference("showTickets",v)}/>
  <OverviewOption icon={BrainCircuit} label="AI pipeline summary" description="Compact five-stage reasoning overview" value={preferences.showAiSummary} onChange={v=>updatePreference("showAiSummary",v)}/>
 </div><div className="operator-preference-grid"><article className="settings-card voice-preference"><Volume2/><div><h3>Voice intelligence reminders</h3><p>Repeat announcements only while a condition remains unsafe.</p></div><label>Reminder interval<select value={preferences.voiceRepeatSeconds} onChange={e=>updatePreference("voiceRepeatSeconds",Number(e.target.value))}><option value={0}>Do not repeat</option><option value={10}>Every 10 seconds</option><option value={30}>Every 30 seconds</option><option value={60}>Every 60 seconds</option></select></label></article><article className="settings-card report-preference"><FileBarChart/><div><h3>Report composition</h3><p>Select the decision views displayed in Operational Reports.</p></div><SettingToggle label="Ticket handling trend" value={preferences.reportLifecycle} onChange={v=>updatePreference("reportLifecycle",v)}/><SettingToggle label="AI performance trend" value={preferences.reportAiPerformance} onChange={v=>updatePreference("reportAiPerformance",v)}/><SettingToggle label="Severity distribution" value={preferences.reportSeverity} onChange={v=>updatePreference("reportSeverity",v)}/><SettingToggle label="Service health" value={preferences.reportHealth} onChange={v=>updatePreference("reportHealth",v)}/><SettingToggle label="Decision findings" value={preferences.reportFindings} onChange={v=>updatePreference("reportFindings",v)}/></article></div></section> <section className="settings-two-column"><article id="automation-policy" className="settings-group compact"><header><div><BrainCircuit/><span><small>03 · AUTOMATION POLICY</small><h3>AI recovery safeguards</h3></span></div></header><p>Automatic recovery closes a ticket only after three consecutive safe readings. Every decision remains linked to the triggering event and action timeline.</p><div className="policy-proof"><CheckCircle2/><span><b>Evidence-gated closure</b><small>Three safe readings required</small></span></div><div className="policy-proof"><ShieldCheck/><span><b>Auditable execution</b><small>Model, action and ticket history retained</small></span></div></article><article id="data-tools" className="settings-group compact"><header><div><FileBarChart/><span><small>04 · DATA AND LOGS</small><h3>System evidence export</h3></span></div></header><p>Download events, alerts, tickets, automatic recovery actions and AI analyses as one engineering CSV.</p><button className="primary export-button" onClick={download}><FileBarChart/> Download current CSV</button>{exportMessage&&<small className="export-message">{exportMessage}</small>}</article></section></>
}
function OverviewOption({icon:Icon,label,description,value,onChange}){return <label className={`overview-option ${value?"selected":""}`}><input type="checkbox" checked={value} onChange={e=>onChange(e.target.checked)}/><i>{value?<CheckCircle2/>:<Icon/>}</i><span><b>{label}</b><small>{description}</small></span><em>{value?"SHOWN":"HIDDEN"}</em></label>}
function SettingToggle({label,value,onChange}){return <label className="preference-toggle"><span>{label}</span><input type="checkbox" checked={value} onChange={e=>onChange(e.target.checked)}/><i/></label>}

function IncidentCenter({incidents,onClose}){
 const [range,setRange]=useState("all"),[sort,setSort]=useState("desc"),now=Date.now(),todayStart=new Date().setHours(0,0,0,0),days={"3m":90,"6m":180,"1y":365};
 const isClosed=item=>["closed","resolved"].includes(item.status),isToday=value=>value&&new Date(value).getTime()>=todayStart;
 const rows=incidents.filter(item=>{if(range==="all")return true;const stamp=new Date(item.created_at||item.event_timestamp).getTime();return range==="today"?stamp>=todayStart:now-stamp<=days[range]*86400000}).slice().sort((a,b)=>(new Date(a.created_at)-new Date(b.created_at))*(sort==="asc"?1:-1));
 const openedToday=incidents.filter(x=>isToday(x.created_at||x.event_timestamp)).length,closedToday=incidents.filter(x=>isClosed(x)&&isToday(x.closed_at||x.resolved_at||x.updated_at||x.created_at)).length,open=incidents.filter(x=>!isClosed(x)).length,closed=incidents.filter(isClosed).length,critical=incidents.filter(x=>!isClosed(x)&&x.severity==="critical").length;
 return <><section className="incident-summary"><article className={open?"attention":"healthy"}><ClipboardCheck/><span><small>OPEN NOW</small><b>{open}</b><em>Tickets requiring action</em></span></article><article><Activity/><span><small>OPENED TODAY</small><b>{openedToday}</b><em>New lifecycle records</em></span></article><article className="closed"><CheckCircle2/><span><small>CLOSED TODAY</small><b>{closedToday}</b><em>Verified completions</em></span></article><article className="closed"><ShieldCheck/><span><small>CLOSED OVERALL</small><b>{closed}</b><em>Completed workflows</em></span></article><article className={critical?"critical":"healthy"}><AlertTriangle/><span><small>CRITICAL OPEN</small><b>{critical}</b><em>Priority investigations</em></span></article></section><section className="incident-toolbar"><div><ClipboardCheck/><span><b>Incident investigation</b><small>Filter and sort database-backed ticket history</small></span></div><label>Date range<select value={range} onChange={e=>setRange(e.target.value)}><option value="today">Today</option><option value="3m">Last 3 months</option><option value="6m">Last 6 months</option><option value="1y">Last year</option><option value="all">All history</option></select></label><label>Date order<select value={sort} onChange={e=>setSort(e.target.value)}><option value="desc">Newest first</option><option value="asc">Oldest first</option></select></label><em>{rows.length} tickets</em></section><TicketQueue title="Incident and ticket workflow" rows={rows} onClose={onClose}/></>
}
function Card({icon,label,value,warn}){return <div className={`card ${warn?"warn":""}`}><div className="icon">{icon}</div><div><span>{label}</span><strong>{value}</strong></div></div>}
function relativeTime(value){if(!value)return "-";const seconds=Math.max(0,Math.floor((Date.now()-new Date(value).getTime())/1000));if(seconds<5)return "just now";if(seconds<60)return `${seconds}s ago`;if(seconds<3600)return `${Math.floor(seconds/60)}m ago`;return new Date(value).toLocaleString()}
function Pagination({page,setPage,total,pageSize=10}){const pages=Math.max(1,Math.ceil(total/pageSize)),start=total?((page-1)*pageSize)+1:0,end=Math.min(page*pageSize,total);useEffect(()=>{if(page>pages)setPage(pages)},[page,pages,setPage]);if(total<=pageSize)return null;return <nav className="pagination" aria-label="Result pages"><span>Showing {start}–{end} of {total}</span><div><button disabled={page===1} onClick={()=>setPage(p=>p-1)}>Previous</button>{Array.from({length:pages},(_,i)=>i+1).filter(n=>n===1||n===pages||Math.abs(n-page)<=1).map((n,i,list)=><React.Fragment key={n}>{i>0&&n-list[i-1]>1&&<em>…</em>}<button className={page===n?"active":""} onClick={()=>setPage(n)}>{n}</button></React.Fragment>)}<button disabled={page===pages} onClick={()=>setPage(p=>p+1)}>Next</button></div></nav>}
function TicketQueue({title,rows,onClose,onViewAll}){
 const [page,setPage]=useState(1),pageSize=onViewAll?5:6,active=rows.filter(x=>["open","assigned","acknowledged"].includes(x.status)).length,paged=rows.slice((page-1)*pageSize,page*pageSize);useEffect(()=>setPage(1),[rows.length,title]);
 return <section className="panel ticket-panel"><div className="section-heading"><div><ClipboardCheck/><div><h3>{title}</h3><p>Every ticket is recorded with its database-backed action history</p></div></div><div className="ticket-heading-actions"><span>{active} ACTIVE</span>{onViewAll&&<button className="refresh" onClick={onViewAll}>Open incident center</button>}</div></div><div className={`ticket-list ${paged.length===1?"single":""}`}>{paged.length?paged.map(ticket=>{const closed=["closed","resolved"].includes(ticket.status);return <article className={`ticket ${ticket.status} ${closed?"completed":"in-progress"}`} key={ticket.id}><div className="ticket-title-row"><div><span className={`severity ${ticket.severity}`}>{ticket.severity}</span><small>#{ticket.id.slice(0,8)} · {relativeTime(ticket.event_timestamp||ticket.created_at)}</small></div><span className={`ticket-state ${closed?"closed":"active"}`}>{closed?<><CheckCircle2/> CLOSED</>:<>IN PROGRESS</>}</span></div><h4>{ticket.message||ticket.alert_type}</h4><p>{ticket.recommendation}</p><div className="ticket-metadata"><span>Raised</span><b>{new Date(ticket.created_at||ticket.event_timestamp).toLocaleString()}</b><span>Current status</span><b className={closed?"closed-text":""}>{ticket.status}</b></div><details className="ticket-history"><summary>View database action history ({(ticket.history?.length||0)+1})</summary><div><article><i/><span><b>Ticket created</b><small>{new Date(ticket.created_at||ticket.event_timestamp).toLocaleString()} · alert engine</small></span></article>{ticket.history?.map(item=><article key={item.id}><i/><span><b>{item.action_type.replaceAll("_"," ")}</b><small>{new Date(item.timestamp).toLocaleString()} · {item.description}{item.note?` · ${item.note}`:""}</small></span></article>)}</div></details><footer><span>{ticket.room_name} · {ticket.device_name} · <b>{ticket.status}</b></span>{!closed&&<button onClick={()=>onClose(ticket.id)}><CheckCircle2/> Mark handled and close</button>}{closed&&<span className="completion-proof"><CheckCircle2/> Lifecycle verified and closed</span>}</footer></article>}):<div className="empty-state ticket-empty"><CheckCircle2/><b>No tickets require action</b><span>The monitored environment is healthy. New incidents will appear here automatically.</span>{onViewAll&&<button className="refresh" onClick={onViewAll}>View incident history</button>}</div>}</div><Pagination page={page} setPage={setPage} total={rows.length} pageSize={pageSize}/></section>
}
function AlertFeed({title,rows,onOpen}){const [page,setPage]=useState(1),pageSize=onOpen?6:5,paged=rows.slice((page-1)*pageSize,page*pageSize);useEffect(()=>setPage(1),[rows.length,title]);return <section className="panel"><div className="section-heading"><div><BellRing/><div><h3>{title}</h3><p>Complete ticket lifecycle from detection through closure</p></div></div>{onOpen&&<button className="refresh" onClick={onOpen}>View all</button>}</div><div className="alert-feed lifecycle-feed">{paged.length?paged.map(a=>{const steps=[{id:`raised-${a.id}`,action_type:"alert_raised",description:a.message||a.alert_type.replaceAll("_"," "),note:a.recommendation,timestamp:a.event_timestamp||a.created_at},...(a.history||[])],closed=["closed","resolved"].includes(a.incident_status||a.status);return <article className={`alert-lifecycle ${a.severity} ${closed?"closed":"active"}`} key={a.id}><header><div className="alert-symbol"><AlertTriangle/></div><div><strong>{a.message||a.alert_type.replaceAll("_"," ")}</strong><small>{a.room_name||"Server Room"} · {a.device_name||"Platform Services"} · #{(a.incident_id||a.id).slice(0,8)}</small></div><span className={`lifecycle-status ${closed?"closed":"active"}`}>{closed?"CLOSED":a.incident_status||a.status}</span></header><ol className="lifecycle-steps">{steps.map((step,index)=><li className={index===steps.length-1?"latest":""} key={step.id||`${a.id}-${index}`}><i>{index+1}</i><div><b>{step.action_type.replaceAll("_"," ")}</b><p>{step.description}</p>{step.note&&<small>{step.note}</small>}<time>{new Date(step.timestamp).toLocaleString()}</time></div></li>)}</ol><footer><span>Started {relativeTime(a.event_timestamp||a.created_at)}</span><b>{closed?"Lifecycle complete — ticket closed":"Lifecycle active — monitoring continues"}</b></footer></article>}):<div className="empty-state">No alerts yet. Use Test Lab to generate a live event.</div>}</div><Pagination page={page} setPage={setPage} total={rows.length} pageSize={pageSize}/></section>}
function Table({title,rows,columns}){const [page,setPage]=useState(1),pageSize=15,paged=rows.slice((page-1)*pageSize,page*pageSize);useEffect(()=>setPage(1),[rows.length,title]);return <section className="panel paged-table"><div className="section-heading"><div><Activity/><div><h3>{title}</h3><p>Latest validated records · paginated for a stable workspace</p></div></div></div><div className="table-wrap"><table><thead><tr>{columns.map(c=><th key={c}>{c.replaceAll("_"," ")}</th>)}</tr></thead><tbody>{paged.length?paged.map((r,i)=><tr key={r.id||i}>{columns.map(c=><td key={c}>{r[c]===null||r[c]===undefined?"-":c.includes("timestamp")||c.endsWith("_at")?relativeTime(r[c]):String(r[c])}</td>)}</tr>):<tr><td colSpan={columns.length}>No data yet. Use Test Lab to generate sensor readings.</td></tr>}</tbody></table></div><Pagination page={page} setPage={setPage} total={rows.length} pageSize={pageSize}/></section>}

class ErrorBoundary extends React.Component{constructor(props){super(props);this.state={error:null}}static getDerivedStateFromError(error){return{error}}render(){if(this.state.error)return <main className="page-crash"><AlertTriangle/><h1>This view could not be displayed</h1><p>{this.state.error.message}</p><button className="primary" onClick={()=>{this.setState({error:null});location.reload()}}><RefreshCw/> Reload dashboard</button></main>;return this.props.children}}

function VTabSquarePromotional() {
  const [message, setMessage] = useState('');
  const [attachment, setAttachment] = useState(null);
  const [queryStatus, setQueryStatus] = useState(null);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) {
      setAttachment(null);
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      alert("Attachment must be smaller than 5MB");
      return;
    }
    const reader = new FileReader();
    reader.onload = (event) => {
      setAttachment({ name: file.name, b64: event.target.result });
    };
    reader.readAsDataURL(file);
  };

  const handleQuerySubmit = async (e) => {
    e.preventDefault();
    if (!message.trim()) return;
    setQueryStatus('sending');
    try {
      const res = await fetch(`${API_URL}/auth/support-query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: message.trim(),
          attachment_name: attachment?.name,
          attachment_b64: attachment?.b64
        })
      });
      if (!res.ok) throw new Error('Failed');
      setQueryStatus('success');
      setMessage('');
      setAttachment(null);
      setTimeout(() => setQueryStatus(null), 5000);
    } catch {
      setQueryStatus('error');
      setTimeout(() => setQueryStatus(null), 4000);
    }
  };

  return (
    <section className="vsq-page">
      <div className="vsq-bg-orb vsq-orb-1"></div>
      <div className="vsq-bg-orb vsq-orb-2"></div>
      <div className="vsq-bg-orb vsq-orb-3"></div>

      {/* Hero */}
      <div className="vsq-hero">
        <div className="vsq-hero-badge">Enterprise AI Innovation</div>
        <div className="vsq-hero-brand">
          <div className="vsq-logo-mark"><BrainCircuit size={28}/></div>
          <div>
            <h1 className="vsq-hero-title">VTab Square</h1>
            <p className="vsq-hero-tagline">Sense · Reason · Resolve</p>
          </div>
        </div>
        <p className="vsq-hero-desc">We build enterprise-grade AI solutions that transform raw telemetry into actionable insights — empowering organizations to proactively manage critical infrastructure at scale.</p>
        <div className="vsq-hero-actions">
          <a href="https://vtabsquare.com/" target="_blank" rel="noopener noreferrer" className="vsq-cta-primary">
            <ExternalLink size={14}/> Visit Website
          </a>
          <div className="vsq-hero-tags">
            <span>AI Solutions</span>
            <span>Digital Twins</span>
            <span>IoT Monitoring</span>
          </div>
        </div>
      </div>

      {/* Contact + Query */}
      <div className="vsq-bottom-grid">
        {/* Contact info */}
        <div className="vsq-contact-card">
          <div className="vsq-section-label" style={{marginBottom:'20px'}}><MapPin size={13}/> Contact Us</div>
          <div className="vsq-contact-items">
            <div className="vsq-contact-item">
              <div className="vsq-contact-icon"><MapPin size={15}/></div>
              <div><b>Headquarters</b><span>Tamil Nadu, India</span></div>
            </div>
            <div className="vsq-contact-item">
              <div className="vsq-contact-icon"><Mail size={15}/></div>
              <div><b>Email</b><a href="mailto:vitabsquare@gmail.com">vitabsquare@gmail.com</a></div>
            </div>
            <div className="vsq-contact-item">
              <div className="vsq-contact-icon"><Globe size={15}/></div>
              <div><b>Website</b><a href="https://vtabsquare.com/" target="_blank" rel="noopener noreferrer">vtabsquare.com</a></div>
            </div>
            <div className="vsq-contact-item">
              <div className="vsq-contact-icon"><Clock size={15}/></div>
              <div><b>Support Hours</b><span>Mon – Fri, 9 AM – 6 PM IST</span></div>
            </div>
          </div>
        </div>

        {/* Query form - message only */}
        <div className="vsq-query-card">
          <div className="vsq-section-label" style={{marginBottom:'20px'}}><Send size={13}/> Send a Query</div>
          {queryStatus === 'success' ? (
            <div className="vsq-success-msg">
              <CheckCircle size={36}/>
              <h4>Message Sent!</h4>
              <p>Thank you for reaching out. The VTab Square team will get back to you shortly.</p>
            </div>
          ) : (
            <form className="vsq-form" onSubmit={handleQuerySubmit}>
              <div className="vsq-form-group" style={{flex:1}}>
                <label>Your Message</label>
                <textarea
                  placeholder="Describe your query, project requirements, or how VTab Square can help your organization..."
                  rows={7}
                  required
                  value={message}
                  onChange={e => setMessage(e.target.value)}
                  style={{height:'100%', minHeight:'160px'}}
                ></textarea>
                <label className="vsq-file-upload">
                  <input type="file" accept="image/*,.pdf,.doc,.docx" onChange={handleFileChange} />
                  <Paperclip size={14}/>
                  {attachment ? (
                    <span className="vsq-file-name">{attachment.name}</span>
                  ) : (
                    <span>Attach screenshot or file (Max 5MB)</span>
                  )}
                </label>
              </div>
              <button type="submit" className="vsq-submit-btn" disabled={queryStatus === 'sending'}>
                {queryStatus === 'sending' ? <><RefreshCw size={14} className="spin"/> Sending…</> : <><Send size={14}/> Send Message</>}
              </button>
              {queryStatus === 'error' && <p style={{color:'#ff8b9a',fontSize:'11px',textAlign:'center',margin:'8px 0 0'}}>Failed to send. Please try again or email us directly.</p>}
            </form>
          )}
        </div>
      </div>
    </section>
  );
}

createRoot(document.getElementById("root")).render(<ErrorBoundary>{localStorage.getItem("token")?<VoiceProvider><App/></VoiceProvider>:<Login/>}</ErrorBoundary>);

