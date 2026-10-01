import { test } from "node:test";
import assert from "node:assert/strict";
import { codexAdapter as a } from "../src/adapters/codex.js";
import { makeStubIo } from "./helpers.js";

const cmds = (io) => io.calls.map((c) => c.slice(1).join(" "));
const LIST = "plugin list --json";
const listOf = (obj) => (c, args) => (args[1] === "list" ? { stdout: JSON.stringify(obj) } : {});

test("CLI 없음: cliMissing, apply false, run 0회", () => {
  const io = makeStubIo({ missing: ["codex"] });
  assert.equal(a.detect(io).cliMissing, true);
  assert.equal(a.apply(io), false);
  assert.equal(io.calls.length, 0);
});

test("detect: list 의 installed 에 있으면 installed, 비JSON 이면 미설치", () => {
  const yes = makeStubIo({ responder: listOf({ installed: [{ name: "beantal-kit", marketplace: "beantal-kit" }], available: [] }) });
  assert.equal(a.detect(yes).installed, true);
  for (const bad of ["", "not json", "null", '{"installed":null}']) {
    const io = makeStubIo({ responder: () => ({ stdout: bad }) });
    assert.equal(a.detect(io).installed, false);
  }
});

test("미설치: marketplace add, upgrade, plugin add 순서", () => {
  const io = makeStubIo({ responder: listOf({ installed: [], available: [] }) });
  assert.equal(a.apply(io), true);
  assert.deepEqual(cmds(io).filter((c) => c !== LIST), [
    "plugin marketplace add Cassiiopeia/beantal-kit",
    "plugin marketplace upgrade beantal-kit",
    "plugin add beantal-kit@beantal-kit",
  ]);
});

test("이미 설치: plugin add 없이 upgrade 만", () => {
  const io = makeStubIo({ responder: listOf({ installed: [{ id: "beantal-kit@beantal-kit" }] }) });
  assert.equal(a.apply(io), true);
  assert.ok(!cmds(io).some((c) => c.startsWith("plugin add")));
  assert.ok(cmds(io).includes("plugin marketplace upgrade beantal-kit"));
});

test("marketplace add 실패(이미 등록)여도 끝까지 진행해 true", () => {
  const io = makeStubIo({
    responder: (c, args) => (args[1] === "list" ? { stdout: '{"installed":[]}' } : args[1] === "marketplace" && args[2] === "add" ? { code: 1 } : {}),
  });
  assert.equal(a.apply(io), true);
  assert.ok(cmds(io).includes("plugin add beantal-kit@beantal-kit"));
});

test("plugin add 실패: false, stderr 첫 줄과 수동 명령을 로그", () => {
  const io = makeStubIo({
    responder: (c, args) => (args[1] === "list" ? { stdout: '{"installed":[]}' } : args[1] === "add" ? { code: 1, stderr: "boom: no such plugin\nstack" } : {}),
  });
  assert.equal(a.apply(io), false);
  const out = io.logs.join("\n");
  assert.match(out, /boom: no such plugin/);
  assert.doesNotMatch(out, /stack/);
  assert.match(out, /수동: codex plugin add beantal-kit@beantal-kit/);
});

test("추가 마켓플레이스(codexName)로 upgrade/add 한다", () => {
  const io = makeStubIo({ responder: listOf({ installed: [] }) });
  const mps = [{ source: "me/priv", name: "priv-marketplace", codexName: "priv" }];
  assert.equal(a.apply(io, mps), true);
  assert.ok(cmds(io).includes("plugin marketplace add me/priv"));
  assert.ok(cmds(io).includes("plugin marketplace upgrade priv"));
  assert.ok(cmds(io).includes("plugin add beantal-kit@priv"));
});

test("remove: 설치돼 있으면 plugin remove 후 marketplace remove", () => {
  const io = makeStubIo({ responder: listOf({ installed: [{ id: "beantal-kit@beantal-kit" }] }) });
  assert.equal(a.remove(io), true);
  assert.deepEqual(cmds(io).filter((c) => c !== LIST), [
    "plugin remove beantal-kit@beantal-kit",
    "plugin marketplace remove beantal-kit",
  ]);
});

test("remove: 명령이 실패해도 true, 수동 안내", () => {
  const io = makeStubIo({ responder: () => ({ code: 1, stdout: "" }) });
  assert.equal(a.remove(io), true);
  assert.match(io.logs.join("\n"), /codex plugin marketplace remove beantal-kit/);
});
