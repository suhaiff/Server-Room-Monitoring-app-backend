import {describe,expect,it} from "vitest";
import {readFileSync} from "node:fs";
const main=readFileSync(new URL("./main.jsx",import.meta.url),"utf8");
const styles=readFileSync(new URL("./styles.css",import.meta.url),"utf8");

describe("login viewport regression",()=>{
 it("contains the logo and brand inside a bounded login card",()=>{
  expect(main).toContain('className="login-card"');
  expect(main).toContain('className="login-brand"');
  expect(main).toContain('alt="VTAB Sentinel"');
  expect(styles).toContain(".login-card{flex:none;width:100%;max-width:420px");
  expect(styles).toContain(".login-brand img{display:block;flex:0 0 52px;width:52px!important;height:52px!important");
 });
 it("allows the login surface to scroll on short screens",()=>{
  expect(styles).toContain("height:100dvh;min-height:0");
  expect(styles).toContain("overflow-y:auto!important");
  expect(styles).toContain("@media(max-height:660px)");
 });
 it("keeps login fields accessible and browser-friendly",()=>{
  expect(main).toContain('autoComplete="username"');
  expect(main).toContain('autoComplete="current-password"');
  expect(main).toContain('type="submit"');
 });
});