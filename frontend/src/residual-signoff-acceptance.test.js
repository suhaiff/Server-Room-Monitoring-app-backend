import {describe,expect,it} from "vitest";
import {readFileSync} from "node:fs";
const main=readFileSync(new URL("./main.jsx",import.meta.url),"utf8");
const styles=readFileSync(new URL("./styles.css",import.meta.url),"utf8");

describe("13:24 residual acceptance corrections",()=>{
 it("replaces duplicate climate data with operational closure evidence",()=>{
  expect(main).toContain('label="Incident closure rate"');
  expect(main).toContain('updatePreference("showClosureMetric"');
  expect(main).not.toContain('label="Current temperature"');
 });
 it("allocates a dedicated Copilot row to each visible section",()=>{
  expect(styles).toContain('grid-template-rows:auto auto auto minmax(0,1fr) auto auto!important');
  expect(styles).toContain('.assistant-context{flex:none}');
 });
 it("stretches report panels to equal height",()=>{
  expect(styles).toContain('.report-workspace{align-items:stretch!important}');
  expect(styles).toContain('.report-workspace>.panel{height:100%;min-height:430px}');
 });
 it("targets the themed shell main canvas directly",()=>{
  expect(styles).toContain('[data-theme="light"]>main{background:');
  expect(styles).toContain('[data-theme="light"]>main>header{background:');
  expect(styles).toContain('[data-theme="light"] .ai-section-tabs button.active');
  expect(styles).toContain('[data-theme="light"] .pipeline-node{background:');
 });
});