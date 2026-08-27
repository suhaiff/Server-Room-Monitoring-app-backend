import {describe,expect,it} from "vitest";
import {readFileSync} from "node:fs";

const main=readFileSync(new URL("./main.jsx",import.meta.url),"utf8");
const styles=readFileSync(new URL("./styles.css",import.meta.url),"utf8");
const twin=readFileSync(new URL("./components/RoomDigitalTwin.jsx",import.meta.url),"utf8");
const assistant=readFileSync(new URL("./components/AgentAssistant.jsx",import.meta.url),"utf8");

describe("fifth video acceptance redesign",()=>{
 it("uses a concise cross-system Overview and lifecycle counters",()=>{
  expect(main).toContain("OverviewCommandCenter");
  expect(main).toContain("OPENED TODAY");
  expect(main).toContain("CLOSED TODAY");
  expect(main).toContain("Lifecycle verified and closed");
 });
 it("provides structured Reports and Settings workspaces",()=>{
  expect(main).toContain('className="report-overview-band"');
  expect(main).toContain('className="settings-index"');
  expect(main).toContain("Decision-ready findings");
 });
 it("turns Copilot prompts into guided, actionable workflows",()=>{
  expect(assistant).toContain('<i>1</i>Ask');
  expect(assistant).toContain('<i>2</i>Verify evidence');
  expect(assistant).toContain('<i>3</i>Open workflow');
  expect(assistant).toContain("suggested_actions");
  expect(assistant).toContain('window.dispatchEvent(new CustomEvent("vtab:navigate"');
 });
 it("uses performant danger-aware room illumination",()=>{
  expect(twin).toContain('danger?"#ff183c":"#46efbb"');
  expect(twin).toContain('dpr={[1,1.25]}');
  expect(twin).toContain('resolution={256} frames={1}');
 });
 it("contains the rebuilt light palette and theme-aware scrollbars",()=>{
  expect(styles).toContain("2.2.0 acceptance redesign");
  expect(styles).toContain("scrollbar-color:#6d9eaa #e2edf1");
  expect(styles).toContain('[data-theme="light"]{--bg:#e7f0f4');
  expect(styles).not.toContain('--bg:#e9f3f8');
 });
});