import { test } from "node:test";
import assert from "node:assert/strict";
import { parseArgs, main } from "../src/cli.js";
import { runInstall } from "../src/commands/install.js";
import { makeStubIo } from "./helpers.js";

const fakeAdapter = (over = {}) => ({
  id: "fake", label: "Fake", order: 1, strategy: "marketplace",
  detect: () => ({ installed: false, cliMissing: false }),
  apply: () => true, remove: () => true, manualHint: () => "HINT",
  ...over,
});

test("parseArgs: 기본값과 옵션", () => {
  assert.deepEqual(parseArgs([]), { command: "install", only: null, dryRun: false, marketplaces: [] });
  const p = parseArgs(["status", "--only", "claude", "--dry-run", "--marketplace", "me/priv"]);
  assert.equal(p.command, "status");
  assert.deepEqual(p.only, ["claude"]);
  assert.equal(p.dryRun, true);
  assert.deepEqual(p.marketplaces, ["me/priv"]);
  assert.equal(parseArgs(["--help"]).command, "help");
  assert.equal(parseArgs(["bogus"]).command, "unknown");
});

test("install: CLI 없는 어댑터는 건너뛰고 hint 출력, 종료 코드 0", () => {
  const io = makeStubIo();
  const code = runInstall({ io, adapters: [fakeAdapter({ detect: () => ({ cliMissing: true }) }), fakeAdapter({ label: "Ok" })] });
  assert.equal(code, 0);
  const out = io.logs.join("\n");
  assert.match(out, /HINT/);
  assert.match(out, /성공 1 \/ 건너뜀 1 \/ 실패 0/);
});

test("install: 한 어댑터가 실패해도 다음은 실행, 종료 코드 1", () => {
  const io = makeStubIo();
  let ran = false;
  const code = runInstall({ io, adapters: [fakeAdapter({ apply: () => false }), fakeAdapter({ label: "Next", apply: () => { ran = true; return true; } })] });
  assert.equal(code, 1);
  assert.equal(ran, true);
});

test("main: 알 수 없는 --only 는 2, run 0회", () => {
  const io = makeStubIo();
  assert.equal(main(["--only", "nope"], io), 2);
  assert.equal(io.calls.length, 0);
  assert.match(io.logs.join("\n"), /알 수 없는 에이전트: nope/);
});

test("main: --dry-run 은 설치성 명령을 실행하지 않고 [dry-run] 로그", () => {
  const io = makeStubIo({ responder: (c, args) => (args.includes("list") ? { stdout: "[]" } : {}) });
  assert.equal(main(["--dry-run"], io), 0);
  const ran = io.calls.map((c) => c.join(" "));
  assert.ok(!ran.some((c) => /marketplace add|plugin install|upgrade/.test(c)));
  assert.match(io.logs.join("\n"), /\[dry-run\] claude plugin marketplace add/);
});

test("main: --marketplace 추가분도 등록된다", () => {
  const io = makeStubIo({ responder: (c, args) => (args.includes("list") ? { stdout: "[]" } : {}) });
  assert.equal(main(["--only", "claude", "--marketplace", "me/priv"], io), 0);
  const ran = io.calls.map((c) => c.join(" "));
  assert.ok(ran.includes("claude plugin marketplace add me/priv"));
  assert.ok(ran.includes("claude plugin install beantal-kit@priv-marketplace --scope user"));
});

test("main: --marketplace 는 codex 에도 반영된다 (upgrade 대상 포함)", () => {
  const io = makeStubIo({ responder: (c, args) => (args.includes("list") ? { stdout: "{}" } : {}) });
  assert.equal(main(["--only", "codex", "--marketplace", "me/priv"], io), 0);
  const ran = io.calls.map((c) => c.join(" "));
  assert.ok(ran.includes("codex plugin marketplace add me/priv"));
  assert.ok(ran.includes("codex plugin marketplace upgrade priv"));
  assert.ok(ran.includes("codex plugin add beantal-kit@priv"));
});

test("main: --only 빈 값은 2, 중복은 한 번만 실행", () => {
  assert.equal(main(["--only", ""], makeStubIo()), 2);
  const io = makeStubIo({ responder: (c, args) => (args.includes("list") ? { stdout: "[]" } : {}) });
  main(["--only", "claude,claude"], io);
  assert.equal(io.calls.filter((c) => c.join(" ").includes("marketplace add")).length, 1);
});

test("main: --marketplace 형식 오류는 2", () => {
  assert.equal(main(["--marketplace", "bad"], makeStubIo()), 2);
});

test("main: --help 는 0 과 사용법", () => {
  const io = makeStubIo();
  assert.equal(main(["--help"], io), 0);
  assert.match(io.logs.join("\n"), /사용법/);
});
