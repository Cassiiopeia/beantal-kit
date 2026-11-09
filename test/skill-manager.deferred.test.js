import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { applyStagedSkillFiles, stageSkillFilesForNextConversation } from "../skills/bean-skill-manager/scripts/lib/plugin_cache.mjs";
import { enqueueRepair, listAwaitingRepairs, listPendingRepairs, markRepairAwaitingRelease } from "../skills/bean-skill-manager/scripts/lib/work_queue.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const cliPath = join(root, "skills", "bean-skill-manager", "scripts", "skill_manager_cli.mjs");
const sessionHookPath = join(root, "hooks", "skill_manager_session_hook.mjs");
const createDirectory = () => mkdtempSync(join(tmpdir(), "manager-deferred-"));
function writeFile(path, body) {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, body);
}
function createFixture() {
  const base = createDirectory();
  const sourceSkillDirectory = join(base, "source");
  const installPath = join(base, "install");
  writeFile(join(sourceSkillDirectory, "scripts", "run.py"), "new");
  writeFile(join(installPath, "skills", "bean-proposal", "scripts", "run.py"), "old");
  return { sourceSkillDirectory, installPath, stagingDirectory: join(base, "staging"), backupRootDirectory: join(base, "backup"), skillName: "bean-proposal", cacheFile: join(installPath, "skills", "bean-proposal", "scripts", "run.py") };
}

test("stage: 작업 중 캐시를 바꾸지 않음", () => {
  const fixture = createFixture();
  const outcome = stageSkillFilesForNextConversation({ ...fixture, relativeFiles: ["scripts/run.py"] });
  assert.deepEqual(outcome.stagedFiles, ["scripts/run.py"]);
  assert.equal(readFileSync(fixture.cacheFile, "utf8"), "old");
});

test("stage: ../ 와 자기 자신 거부", () => {
  const fixture = createFixture();
  assert.throws(() => stageSkillFilesForNextConversation({ ...fixture, relativeFiles: ["../evil.py"] }), /경로/);
  assert.throws(() => stageSkillFilesForNextConversation({ ...fixture, skillName: "bean-skill-manager", relativeFiles: null }), /대상/);
});

test("applyStaged: 반영 후 대기본 제거, 백업 존재", () => {
  const fixture = createFixture();
  stageSkillFilesForNextConversation({ ...fixture, relativeFiles: null });
  const outcome = applyStagedSkillFiles(fixture);
  assert.deepEqual(outcome.appliedSkills, ["bean-proposal"]);
  assert.equal(readFileSync(fixture.cacheFile, "utf8"), "new");
  assert.deepEqual(readdirSync(fixture.stagingDirectory), []);
  assert.deepEqual(readdirSync(join(fixture.backupRootDirectory, "bean-proposal")).length, 1);
});

test("applyStaged: 플러그인이 업데이트되어 경로가 다르면 덮어쓰지 않고 폐기", () => {
  const fixture = createFixture();
  stageSkillFilesForNextConversation({ ...fixture, relativeFiles: null });
  const newerInstallPath = join(dirname(fixture.installPath), "install-newer");
  const outcome = applyStagedSkillFiles({ ...fixture, installPath: newerInstallPath });
  assert.deepEqual(outcome.discardedSkills, ["bean-proposal"]);
  assert.ok(!existsSync(join(newerInstallPath, "skills", "bean-proposal")));
  assert.equal(readFileSync(fixture.cacheFile, "utf8"), "old");
});

test("applyStaged: 대기본 없음이면 아무 일도 안 함", () => {
  const fixture = createFixture();
  assert.deepEqual(applyStagedSkillFiles(fixture), { appliedSkills: [], discardedSkills: [] });
});

test("대기열: 배포 대기로 전환하면 pending 에서 빠지고 awaiting 에 표시", () => {
  const directory = createDirectory();
  const id = enqueueRepair(directory, { summary: "표 넘침" });
  markRepairAwaitingRelease(directory, id, { ownCommitHashes: ["abc"], issueNumber: "7", reason: "other_unreleased_commits" });
  assert.deepEqual(listPendingRepairs(directory), []);
  const [awaiting] = listAwaitingRepairs(directory);
  assert.deepEqual(awaiting.ownCommitHashes, ["abc"]);
  assert.equal(awaiting.reason, "other_unreleased_commits");
});

function runNode(path, args, home) {
  return spawnSync(process.execPath, [path, ...args], { encoding: "utf8", env: { ...process.env, HOME: home, USERPROFILE: home, CLAUDE_CONFIG_DIR: join(home, ".claude") } });
}
function createEnabledHome(installPath) {
  const home = createDirectory();
  writeFile(join(home, ".beantal-kit", "configs", "bean-skill-manager", "config.json"), JSON.stringify({ "skill-manager": { repo_path: home, enabled: true } }));
  writeFile(join(home, ".claude", "plugins", "installed_plugins.json"), JSON.stringify({ plugins: { "beantal-kit@beantal-kit-marketplace": [{ installPath }] } }));
  return home;
}
const managerDirectoryOf = (home) => join(home, ".beantal-kit", "configs", "bean-skill-manager");

test("session hook: 미설정이면 빈 출력, exit 0", () => {
  const result = runNode(sessionHookPath, [], createDirectory());
  assert.equal(result.status, 0);
  assert.equal(result.stdout, "");
});

test("session hook: 대기본 반영, 대기 건 있으면 재개 안내", () => {
  const fixture = createFixture();
  const home = createEnabledHome(fixture.installPath);
  stageSkillFilesForNextConversation({ ...fixture, stagingDirectory: join(managerDirectoryOf(home), "pending-cache"), relativeFiles: null });
  enqueueRepair(managerDirectoryOf(home), { summary: "표 넘침" });
  const result = runNode(sessionHookPath, [], home);
  assert.equal(readFileSync(fixture.cacheFile, "utf8"), "new");
  const output = JSON.parse(result.stdout);
  assert.equal(output.hookSpecificOutput.hookEventName, "SessionStart");
  assert.match(output.hookSpecificOutput.additionalContext, /background-procedure/);
});

test("session hook: 대기 건 없으면 출력 없음", () => {
  const fixture = createFixture();
  assert.equal(runNode(sessionHookPath, [], createEnabledHome(fixture.installPath)).stdout, "");
});

test("hooks.json: SessionStart 는 startup 에서만 (compact·resume 중 교체 방지)", () => {
  const hooks = JSON.parse(readFileSync(join(root, "hooks", "hooks.json"), "utf8"));
  assert.equal(hooks.hooks.SessionStart[0].matcher, "startup");
});

test("CLI apply-cache: 캐시를 바꾸지 않고 staged 반환", () => {
  const fixture = createFixture();
  const home = createEnabledHome(fixture.installPath);
  const output = JSON.parse(runNode(cliPath, ["apply-cache", "--skill", "bean-proposal", "--source", fixture.sourceSkillDirectory], home).stdout);
  assert.equal(output.code, "staged");
  assert.equal(readFileSync(fixture.cacheFile, "utf8"), "old");
});

test("CLI is-released: 레포를 못 읽으면 not_released", () => {
  const home = createDirectory();
  const output = JSON.parse(runNode(cliPath, ["is-released", "--repo", join(home, "missing"), "--own-commits", "abc"], home).stdout);
  assert.equal(output.code, "not_released");
});

test("PowerPoint 스크립트: 다른 프레젠테이션이 열려 있으면 종료하지 않음", () => {
  for (const name of ["drm_read_pptx.ps1", "snapshot_pptx.ps1", "edit_pptx.ps1"]) {
    const script = readFileSync(join(root, "skills", "bean-proposal", "scripts", name), "utf8");
    assert.match(script, /if \(\$app\.Presentations\.Count -eq 0\) \{ \$app\.Quit\(\) \}/, name);
  }
});

test("뒷단 문서: 사람 대기와 PowerPoint 경유 명령 금지", () => {
  const procedure = readFileSync(join(root, "skills", "bean-skill-manager", "references", "background-procedure.md"), "utf8");
  const verification = readFileSync(join(root, "skills", "bean-skill-manager", "references", "verify", "bean-proposal.md"), "utf8");
  assert.doesNotMatch(procedure, /확인필요/);
  assert.match(procedure, /실제로 한 번/);
  assert.match(verification, /render-check/);
  assert.doesNotMatch(verification, /^\d\. `(render|review|snapshot) /m);
});
