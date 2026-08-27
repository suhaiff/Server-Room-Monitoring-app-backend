import {readFileSync} from "node:fs";
import {describe,expect,it} from "vitest";

const source=readFileSync(new URL("./main.jsx",import.meta.url),"utf8");

describe("threshold mode controls",()=>{
 it("provides separately persisted Manual and Auto modes",()=>{
  expect(source).toContain('change(name,"mode","manual")');
  expect(source).toContain('change(name,"mode","auto")');
  expect(source).toContain('mode:rule.mode||"manual"');
  expect(source).toContain('"Uses exactly the configured value."');
  expect(source).toContain('"Using the learned normal baseline."');
 });
});

