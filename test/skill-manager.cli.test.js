import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const cliPath = join(root, "skills", "bean-skill-manager", "scripts", "skill_manager_cli.mjs");
const hookPath = join(root, "hooks", "skill_manager_prompt_hook.mjs");

const createHome = () => mkdtempSync(join(tmpdir(), "manager-cli-"));
function runNode(path, args, home) {
  return spawnSync(process.execPath, [path, ...args], {
    encoding: "utf8",
    env: { ...process.env, HOME: home, USERPROFILE: home, CLAUDE_CONFIG_DIR: join(home, ".claude") },
  });
}
const runCli = (args, home) => JSON.parse(runNode(cliPath, args, home).stdout);
function writeConfig(home, body) {
  const directory = join(home, ".beantal-kit", "configs", "bean-skill-manager");
  mkdirSync(directory, { recursive: true });
  writeFileSync(join(directory, "config.json"), typeof body === "string" ? body : JSON.stringify(body));
}

test("status: 설정 없으면 not_configured", () => {
  const output = runCli(["status"], createHome());
  assert.equal(output.code, "not_configured");
  assert.ok(["ok", "code", "summary", "next"].every((key) => key in output));
});

test("status: 설정 있고 플러그인 없으면 not_installed", () => {
  const home = createHome();
  writeConfig(home, { "skill-manager": { repo_path: home, enabled: true } });
  assert.equal(runCli(["status"], home).code, "not_installed");
});

test("잘못된 하위 명령: ok false, 종료 코드 1", () => {
  const result = runNode(cliPath, ["no-such-command"], createHome());
  assert.equal(JSON.parse(result.stdout).ok, false);
  assert.equal(result.status, 1);
});

test("apply-cache: 플러그인 미설치면 not_installed", () => {
  const output = runCli(["apply-cache", "--skill", "bean-proposal", "--source", createHome()], createHome());
  assert.equal(output.code, "not_installed");
});

test("release-decision: auto-deploy.json 을 못 읽으면 배포하지 않음", () => {
  const home = createHome();
  const output = runCli(["release-decision", "--repo", join(home, "missing"), "--own-commits", "a", "--checks-passed", "true", "--verified", "true"], home);
  assert.equal(output.action, "push-only");
  assert.equal(output.reason, "remote_deploy_disabled");
});

test("queue-add, queue-list, queue-done, lock, unlock 왕복", () => {
  const home = createHome();
  const requestPath = join(home, "request.json");
  writeFileSync(requestPath, JSON.stringify({ summary: "표 넘침 수정" }));
  const added = runCli(["queue-add", "--request-file", requestPath], home);
  assert.equal(runCli(["queue-list"], home).pending.length, 1);
  runCli(["queue-done", "--id", added.id], home);
  assert.equal(runCli(["queue-list"], home).pending.length, 0);
  assert.equal(runCli(["lock"], home).code, "locked");
  assert.equal(runCli(["lock"], home).code, "busy");
  runCli(["unlock"], home);
  assert.equal(runCli(["lock"], home).code, "locked");
});

test("scan: 민감 용어 검출, 용어 원문은 출력하지 않음", () => {
  const home = createHome();
  mkdirSync(join(home, ".beantal-kit", "configs", "bean-proposal"), { recursive: true });
  writeFileSync(join(home, ".beantal-kit", "configs", "bean-proposal", "references.json"), JSON.stringify({ projects: [{ client: "테스트고객" }] }));
  const textPath = join(home, "text.md");
  writeFileSync(textPath, "테스트고객 제안서 표 넘침");
  const result = runNode(cliPath, ["scan", "--file", textPath], home);
  const output = JSON.parse(result.stdout);
  assert.equal(output.code, "sensitive_found");
  assert.equal(output.count, 1);
  assert.ok(!result.stdout.includes("테스트고객"));
});

test("hook: 미설정·깨진 설정이면 빈 출력, exit 0", () => {
  const unset = runNode(hookPath, [], createHome());
  assert.equal(unset.status, 0);
  assert.equal(unset.stdout, "");
  const home = createHome();
  writeConfig(home, "{ not json");
  const broken = runNode(hookPath, [], home);
  assert.equal(broken.status, 0);
  assert.equal(broken.stdout, "");
});

test("hook: 활성화되면 안내 주입", () => {
  const home = createHome();
  writeConfig(home, { "skill-manager": { repo_path: home, enabled: true } });
  const result = runNode(hookPath, [], home);
  const output = JSON.parse(result.stdout);
  assert.equal(output.hookSpecificOutput.hookEventName, "UserPromptSubmit");
  assert.match(output.hookSpecificOutput.additionalContext, /bean-skill-manager/);
});

test("hooks.json: UserPromptSubmit, CLAUDE_PLUGIN_ROOT 사용", () => {
  const hooks = JSON.parse(readFileSync(join(root, "hooks", "hooks.json"), "utf8"));
  const command = hooks.hooks.UserPromptSubmit[0].hooks[0].command;
  assert.match(command, /\$\{CLAUDE_PLUGIN_ROOT\}/);
  assert.match(command, /^node /);
});
