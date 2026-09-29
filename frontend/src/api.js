export const API_URL=import.meta.env.VITE_API_URL;
if(!API_URL)throw new Error("VITE_API_URL is required. Set it in the project .env file before building the frontend.");
export async function login(email,password){
  const form=new URLSearchParams({username:email,password});
  const r=await fetch(`${API_URL}/auth/token`,{method:"POST",body:form});
  if(r.status===403){
    const d=await r.json();
    if(d.detail?.error==="mfa_required") return { mfa_required: true, mfa_token: d.detail.temp_token };
  }
  if(!r.ok)throw new Error("Invalid credentials");
  const data=await r.json();
  localStorage.setItem("token",data.access_token);
  return data;
}
export async function mfaLogin(tempToken, code) {
  const r = await fetch(`${API_URL}/auth/mfa/login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ temp_token: tempToken, code }) });
  if (!r.ok) throw new Error(await r.text());
  const data = await r.json();
  localStorage.setItem("token", data.access_token);
  return data;
}
export async function setupMFA() {
  const r = await fetch(`${API_URL}/auth/mfa/setup`, { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${localStorage.getItem("token")}` } });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
export async function verifyMFA(code) {
  const r = await fetch(`${API_URL}/auth/mfa/verify-setup`, { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${localStorage.getItem("token")}` }, body: JSON.stringify({ code }) });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
export async function register(name, email, password) {
  const r = await fetch(`${API_URL}/auth/register`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ full_name: name, email, password, organization_id: "00000000-0000-0000-0000-000000000001", role_name: "viewer" }) });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
export async function verify(email, code) {
  const r = await fetch(`${API_URL}/auth/verify`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, code }) });
  if (!r.ok) throw new Error(await r.text());
  const data = await r.json();
  if(data.access_token) localStorage.setItem("token", data.access_token);
  return data;
}
export async function api(path,options={}){const token=localStorage.getItem("token");const isGet=!options.method||options.method.toUpperCase()==="GET";const cacheBust=isGet?(path.includes("?")?`&_t=${Date.now()}`:`?_t=${Date.now()}`):"";const r=await fetch(`${API_URL}${path}${cacheBust}`,{...options,headers:{"Content-Type":"application/json",Authorization:`Bearer ${token}`,...options.headers}});if(r.status===401){localStorage.removeItem("token");location.reload()}if(!r.ok)throw new Error(await r.text());return r.json()}
