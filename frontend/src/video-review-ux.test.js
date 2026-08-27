import {describe,expect,it} from "vitest";
import {readFileSync} from "node:fs";
const main=readFileSync(new URL("./main.jsx",import.meta.url),"utf8");
const styles=readFileSync(new URL("./styles.css",import.meta.url),"utf8");
describe("bounded dashboard navigation",()=>{
 it("paginates telemetry, alerts and incidents",()=>{
  expect(main).toContain("function Pagination");
  expect(main).toContain("pageSize=15");
  expect(main).toContain("pageSize=onOpen?6:5");
  expect(main).toContain("pageSize=onViewAll?5:6");
 });
 it("keeps main content and the sidebar inside the viewport",()=>{
  expect(styles).toContain(".shell{height:100vh");
  expect(styles).toContain(".shell>main{height:100vh");
  expect(styles).toContain(".shell>aside{height:100vh");
 });
 it("prevents horizontal overflow in the Copilot",()=>{
  expect(styles).toContain(".assistant-drawer,.assistant-messages,.assistant-prompts{overflow-x:hidden}");
  expect(styles).toContain(".assistant-prompts{display:grid");
  expect(styles).toContain("@keyframes botFloat");
 });
});
