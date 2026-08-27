const API=import.meta.env.VITE_API_URL||"http://localhost:8000/api/v1";
export async function login(email,password){const form=new URLSearchParams({username:email,password});const r=await fetch(`${API}/auth/token`,{method:"POST",body:form});if(!r.ok)throw new Error("Invalid credentials");const data=await r.json();localStorage.setItem("token",data.access_token);return data}
export async function api(path,options={}){const token=localStorage.getItem("token");const r=await fetch(`${API}${path}`,{...options,headers:{"Content-Type":"application/json",Authorization:`Bearer ${token}`,...options.headers}});if(r.status===401){localStorage.removeItem("token");location.reload()}if(!r.ok)throw new Error(await r.text());return r.json()}

