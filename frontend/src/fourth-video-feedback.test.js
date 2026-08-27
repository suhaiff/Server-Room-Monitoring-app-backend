import {describe,expect,it} from "vitest";
import {readFileSync} from "node:fs";
const main=readFileSync(new URL("./main.jsx",import.meta.url),"utf8");
const styles=readFileSync(new URL("./styles.css",import.meta.url),"utf8");
const twin=readFileSync(new URL("./components/RoomDigitalTwin.jsx",import.meta.url),"utf8");
const ai=readFileSync(new URL("./components/AITerminal.jsx",import.meta.url),"utf8");
const assistant=readFileSync(new URL("./components/AgentAssistant.jsx",import.meta.url),"utf8");

describe("fourth video feedback acceptance",()=>{
 it("uses an illuminated, enclosed and editable WebGL room",()=>{
  expect(twin).toContain("ROOM LAYOUT EDITOR");
  expect(twin).toContain("vtab.room-layout.v2");
  expect(twin).toContain("position:[6.36,0,1.4]");
  expect(twin).toContain("toneMappingExposure=1.12");
  expect(twin).toContain('dpr={[1,1.25]}');
  expect(twin).toContain('resolution={256} frames={1}');
  expect(twin).toContain("<RoomShell/>");
  expect(twin).toContain("Edit room layout");
 });
 it("keeps the five-model pipeline visible above the three useful views",()=>{
  expect(ai).toContain("<Pipeline status={status}/>");
  expect(ai).toContain("ALWAYS-ON MODEL FLOW");
  expect(ai).toContain('["overview","System health"');
  expect(ai).not.toContain('["models","Model pipeline"');
  expect(styles).toContain(".ai-section-tabs{grid-template-columns:repeat(3,1fr)}");
 });
 it("makes predictive evidence readable",()=>{
  expect(styles).toContain(".live-intelligence article{gap:10px;min-height:150px");
  expect(styles).toContain(".live-intelligence article strong{font-size:18px");
 });
 it("uses one compact Copilot control",()=>{
  expect(assistant).toContain('className="new-chat"');
  expect(assistant).not.toContain("<em>AI COPILOT</em>");
  expect(styles).toContain("border-radius:50%!important");
  expect(styles).toContain(".assistant-logo{display:none!important}");
 });
 it("shows actionable climate meaning and keeps all navigation accessible",()=>{
  expect(assistant).toContain("safetyMargin");
  expect(assistant).toContain("Active limit");
  expect(main).toContain('className="sidebar-navigation"');
  expect(main).not.toContain('className="sidebar-status"');
  expect(styles).toContain(".sidebar-navigation{flex:1;min-height:0;overflow-y:auto");
 });
});