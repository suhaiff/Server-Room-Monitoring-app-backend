import {describe,expect,it} from "vitest";
import {readFileSync} from "node:fs";

const main=readFileSync(new URL("./main.jsx",import.meta.url),"utf8");
const styles=readFileSync(new URL("./styles.css",import.meta.url),"utf8");
const assistant=readFileSync(new URL("./components/AgentAssistant.jsx",import.meta.url),"utf8");

describe("final 12:56 video sign-off acceptance",()=>{
 it("restores the requested Overview flow and daily insights",()=>{
  const closure=main.indexOf('label="Incident closure rate"');
  const alerts=main.indexOf('label="Active alerts"');
  const tickets=main.indexOf('label="Open tickets"');
  const trend=main.indexOf('preferences.showTrend&&<LiveTrend');
  const latest=main.indexOf('LATEST ALERT');
  const today=main.indexOf("TODAY'S WORKFLOW");
  expect(closure).toBeGreaterThan(0);
  expect(closure).toBeLessThan(alerts);
  expect(alerts).toBeLessThan(tickets);
  expect(tickets).toBeLessThan(trend);
  expect(trend).toBeLessThan(latest);
  expect(latest).toBeLessThan(today);
 });
 it("provides checkbox-driven responsive Overview composition",()=>{
  expect(main).toContain('className="overview-option-grid"');
  expect(main.match(/<OverviewOption/g)?.length).toBeGreaterThanOrEqual(12);
  expect(main).toContain('updatePreference("showTodayTickets"');
  expect(styles).toContain('grid-template-columns:repeat(auto-fit,minmax(235px,1fr))');
 });
 it("adds ticket handling and AI performance trends to Reports",()=>{
  expect(main).toContain("Alert and ticket handling trend");
  expect(main).toContain("AI performance summary");
  expect(main).toContain('dataKey="opened"');
  expect(main).toContain('dataKey="runs"');
 });
 it("uses a circular centered Copilot with a working New chat action",()=>{
  expect(assistant).toContain('className="new-chat"');
  expect(assistant).toContain("setConversation(null)");
  expect(assistant).toContain('className="bot-orbit outer"');
  expect(styles).toContain('border-radius:50%!important');
  expect(styles).toContain('align-items:center!important;justify-content:center!important');
 });
 it("uses the fully rebuilt dimensional light palette",()=>{
  expect(styles).toContain("Entire light theme rebuilt for 2.3.0");
  expect(styles).toContain('radial-gradient(circle at 78% 0,#d1edf2');
  expect(styles).toContain('box-shadow:inset 0 1px #fff,0 14px 34px #244c6020');
  expect(styles).toContain('[data-theme="light"] .assistant-drawer');
  expect(styles).not.toContain("Entire white theme rebuilt from a blank semantic palette");
 });
});