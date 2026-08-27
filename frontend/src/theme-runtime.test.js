import {describe,expect,it} from "vitest";
import {readFileSync} from "node:fs";
const source=readFileSync(new URL("./main.jsx",import.meta.url),"utf8");
describe("global theme runtime",()=>{
 it("initializes theme state before the App render uses it",()=>{
  const declaration=source.indexOf("const [theme,setTheme]=useState");
  const renderUse=source.indexOf("data-theme={theme}");
  expect(declaration).toBeGreaterThan(-1);
  expect(renderUse).toBeGreaterThan(declaration);
 });
 it("provides the persisted dark/light switch",()=>{
  expect(source).toContain('localStorage.getItem("vtab.theme")');
  expect(source).toContain('localStorage.setItem("vtab.theme",next)');
 });
});
