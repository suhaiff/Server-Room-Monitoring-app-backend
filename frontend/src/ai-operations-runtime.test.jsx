import React from "react";
import {describe,expect,it} from "vitest";
import {renderToStaticMarkup} from "react-dom/server";
import {readFileSync} from "node:fs";
import {IntelligenceGovernance} from "./components/AgentAssistant";

const twinSource=readFileSync(new URL("./components/RoomDigitalTwin.jsx",import.meta.url),"utf8");
const terminalSource=readFileSync(new URL("./components/AITerminal.jsx",import.meta.url),"utf8");
describe("AI Operations and WebGL digital twin",()=>{
 it("renders predictive governance without an undefined icon crash",()=>{
  const html=renderToStaticMarkup(<IntelligenceGovernance/>);
  expect(html).toContain("Live predictive intelligence");
  expect(html).toContain("Governed action lifecycle");
 });
 it("uses a genuine interactive WebGL room with operational assets",()=>{
  expect(twinSource).toContain("<Canvas");
  expect(twinSource).toContain("<OrbitControls");
  expect(twinSource).toContain("enableZoom");
  expect(twinSource).toContain("enablePan");
  expect(twinSource).toContain("DHT22 climate sensor");
  expect(twinSource).toContain("MQ-2 smoke sensor");
  expect(twinSource).toContain("Water leak probe");
  expect(twinSource).toContain("Magnetic contact");
  expect(twinSource).toContain("Precision cooling unit");
 });
 it("separates crowded AI evidence into focused operation views",()=>{
  expect(terminalSource).toContain("ai-section-tabs");
  expect(terminalSource).toContain("Predictive intelligence");
  expect(terminalSource).toContain("Execution evidence");
  expect(terminalSource).toContain("LIVE MONITORING");
  expect(terminalSource).not.toContain("LIVE · 2.5 SEC");
 });
});
