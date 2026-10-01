import { test } from "node:test";
import assert from "node:assert/strict";
import { claudeAdapter as a } from "../src/adapters/claude.js";
import { makeStubIo } from "./helpers.js";

const ID = "beantal-kit@beantal-kit-marketplace";
const listOf = (stdout) => (cmd, args) => (args[1] === "list" ? { stdout } : {});
const cmds = (io) => io.calls.map((c) => c.slice(1).join(" "));

test("CLI 없음: detect cliMissing, apply false, run 0회", () => {
  const io = makeStubIo({ missing: ["claude"] });
  assert.deepEqual(a.detect(io), { installed: false, cliMissing: true, note: "CLI 없음" });
  assert.equal(a.apply(io), false);
  assert.equal(io.calls.length, 0);
  assert.match(io.logs.join("\n"), /marketplace add Cassiiopeia\/beantal-kit/);
});

test("미설치: marketplace add 후 install", () => {
  const io = makeStubIo({ responder: listOf("[]") });
  assert.equal(a.apply(io), true);
  assert.ok(cmds(io).includes("plugin marketplace add Cassiiopeia/beantal-kit"));
  assert.ok(cmds(io).includes(`plugin install ${ID} --scope user`));
});

test("설치됨: update 만 호출", () => {
  const io = makeStubIo({ responder: listOf(JSON.stringify([{ name: ID, scope: "user" }])) });
  assert.equal(a.apply(io), true);
  assert.ok(cmds(io).includes(`plugin update ${ID} --scope user`));
  assert.ok(!cmds(io).some((c) => c.startsWith("plugin install")));
});

test("marketplace add 실패(이미 등록)여도 install 진행", () => {
  const io = makeStubIo({
    responder: (c, args) => (args[1] === "list" ? { stdout: "[]" } : args[1] === "marketplace" ? { code: 1 } : {}),
  });
  assert.equal(a.apply(io), true);
  assert.ok(cmds(io).includes(`plugin install ${ID} --scope user`));
});

test("install 실패: false + 수동 명령 로그", () => {
  const io = makeStubIo({
    responder: (c, args) => (args[1] === "list" ? { stdout: "[]" } : args[1] === "install" ? { code: 1 } : {}),
  });
  assert.equal(a.apply(io), false);
  assert.match(io.logs.join("\n"), /수동: claude plugin install/);
});

test("install 실패 시 stderr 첫 줄을 로그에 남긴다", () => {
  const io = makeStubIo({
    responder: (c, args) => (args[1] === "list" ? { stdout: "[]" } : args[1] === "install" ? { code: 1, stderr: "denied: private repo\nmore" } : {}),
  });
  a.apply(io);
  assert.match(io.logs.join("\n"), /denied: private repo/);
  assert.doesNotMatch(io.logs.join("\n"), /more/);
});

for (const bad of ["", "not json", '{"plugins":[]}', "null"]) {
  test(`list 출력 ${JSON.stringify(bad)} → 미설치, 예외 없음`, () => {
    const io = makeStubIo({ responder: listOf(bad) });
    assert.equal(a.detect(io).installed, false);
  });
}

test("remove: 설치됨 → uninstall, 미설치 → 호출 없음", () => {
  const io1 = makeStubIo({ responder: listOf(JSON.stringify({ plugins: [{ name: ID, scope: "project" }] })) });
  assert.equal(a.remove(io1), true);
  assert.ok(cmds(io1).includes(`plugin uninstall ${ID} --scope project`));
  const io2 = makeStubIo({ responder: listOf("[]") });
  assert.equal(a.remove(io2), true);
  assert.ok(!cmds(io2).some((c) => c.startsWith("plugin uninstall")));
});
