import { test } from "node:test";
import assert from "node:assert/strict";
import { which, run, defaultIo } from "../src/runner.js";

test("which: 존재하는 명령은 경로, 없는 명령은 null", () => {
  assert.equal(typeof which("node"), "string");
  assert.equal(which("definitely-not-a-cmd-xyz"), null);
});

test("run: 성공 출력과 종료 코드", () => {
  const r = run("node", ["-e", "process.stdout.write('ok')"]);
  assert.equal(r.code, 0);
  assert.equal(r.stdout, "ok");
});

test("run: 없는 명령은 code 127", () => {
  assert.equal(run("definitely-not-a-cmd-xyz").code, 127);
});

test("run: 공백·따옴표·특수문자 인자가 그대로 전달된다", () => {
  for (const arg of ["a b'c", 'a b"c', "a b+", "x*y", "dir with space\\"]) {
    const r = run("node", ["-e", "process.stdout.write(process.argv[1])", arg]);
    assert.equal(r.stdout, arg);
  }
});

test("defaultIo: 계약 필드", () => {
  const io = defaultIo();
  for (const k of ["which", "run", "home", "log"]) assert.equal(typeof io[k], "function");
});
