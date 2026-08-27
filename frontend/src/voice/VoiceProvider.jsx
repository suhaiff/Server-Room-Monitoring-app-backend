import React,{createContext,useCallback,useContext,useEffect,useRef,useState} from "react";

const VoiceContext=createContext(null);

export function VoiceProvider({children}){
 const [enabled,setEnabled]=useState(()=>localStorage.getItem("vtab.voice.enabled")==="true");
 const [speaking,setSpeaking]=useState(false),[lastMessage,setLastMessage]=useState("");
 const voiceRef=useRef(null),enabledRef=useRef(enabled),queueRef=useRef([]),activeRef=useRef(false),seenRef=useRef(new Set());
 enabledRef.current=enabled;

 useEffect(()=>{
  if(!("speechSynthesis" in window))return;
  const choose=()=>{const voices=window.speechSynthesis.getVoices();voiceRef.current=voices.find(v=>/Natural|Neural|Aria|Jenny|Samantha|Google UK English Female/i.test(v.name))||voices.find(v=>v.lang?.startsWith("en"))||voices[0]};
  choose();window.speechSynthesis.addEventListener("voiceschanged",choose);
  return()=>window.speechSynthesis.removeEventListener("voiceschanged",choose);
 },[]);

 const pump=useCallback(()=>{
  if(!enabledRef.current||activeRef.current||!("speechSynthesis" in window))return;
  const item=queueRef.current.shift();if(!item)return;
  activeRef.current=true;
  const speech=new SpeechSynthesisUtterance(item.message);
  speech.voice=voiceRef.current;speech.lang="en-US";speech.rate=item.priority==="critical"?.9:.97;speech.pitch=1.02;speech.volume=1;
  speech.onstart=()=>{setSpeaking(true);setLastMessage(item.message)};
  const finish=()=>{activeRef.current=false;setSpeaking(false);setTimeout(pump,250)};
  speech.onend=finish;speech.onerror=finish;
  window.speechSynthesis.speak(speech);
 },[]);

 const announce=useCallback((message,{priority="normal",id}={})=>{
  if(!enabledRef.current||!("speechSynthesis" in window)||!message)return;
  if(id&&seenRef.current.has(id))return;
  if(id){seenRef.current.add(id);if(seenRef.current.size>200)seenRef.current=new Set([...seenRef.current].slice(-120))}
  // A critical event supersedes queued informational speech, but it never
  // repeatedly cancels other alerts from the same compound incident.
  if(priority==="critical")queueRef.current=queueRef.current.filter(x=>x.priority==="critical");
  queueRef.current.push({message,priority,id});
  queueRef.current.sort((a,b)=>(b.priority==="critical")-(a.priority==="critical"));
  pump();
 },[pump]);

 const toggle=()=>{const next=!enabledRef.current;enabledRef.current=next;setEnabled(next);localStorage.setItem("vtab.voice.enabled",String(next));if(!next&&"speechSynthesis" in window){queueRef.current=[];activeRef.current=false;window.speechSynthesis.cancel();setSpeaking(false)}};
 return <VoiceContext.Provider value={{enabled,speaking,lastMessage,toggle,announce,supported:"speechSynthesis" in window}}>{children}</VoiceContext.Provider>
}

export function useVoice(){return useContext(VoiceContext)}
