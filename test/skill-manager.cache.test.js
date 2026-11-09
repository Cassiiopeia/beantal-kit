import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { applySkillFilesToCache, findPluginInstallPath, resolveClaudeConfigDirectory } from "../skills/bean-skill-manager/scripts/lib/plugin_cache.mjs";

const createDirectory = () => mkdtempSync(join(tmpdir(), "manager-cache-"));
function writeFile(path, body) {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, body);
}
function createFixture() {
  const root = createDirectory();
  const sourceSkillDirectory = join(root, "source");
  const installPath = join(root, "install");
  const backupDirectory = join(root, "backup");
  writeFile(join(sourceSkillDirectory, "SKILL.md"), "new-skill");
  writeFile(join(sourceSkillDirectory, "references", "guide.md"), "new-guide");
  writeFile(join(installPath, "skills", "bean-proposal", "SKILL.md"), "old-skill");
  writeFile(join(installPath, "skills", "bean-proposal", "references", "guide.md"), "old-guide");
  writeFile(join(installPath, "skills", "bean-proposal", "only-in-cache.md"), "keep");
  return { sourceSkillDirectory, installPath, backupDirectory, skillName: "bean-proposal", cacheSkill: join(installPath, "skills", "bean-proposal") };
}

test("applySkillFilesToCache: 지정 파일만 복사, 덮어쓰기 전 백업", () => {
  const fixture = createFixture();
  const { cacheSkill, ...input } = fixture;
  const outcome = applySkillFilesToCache({ ...input, relativeFiles: ["SKILL.md"] });
  assert.deepEqual(outcome.copiedFiles, ["SKILL.md"]);
  assert.equal(readFileSync(join(cacheSkill, "SKILL.md"), "utf8"), "new-skill");
  assert.equal(readFileSync(join(cacheSkill, "references", "guide.md"), "utf8"), "old-guide");
  assert.equal(readFileSync(join(fixture.backupDirectory, "SKILL.md"), "utf8"), "old-skill");
});

test("applySkillFilesToCache: null 이면 폴더 전체, 캐시의 기존 파일은 유지", () => {
  const { cacheSkill, ...input } = createFixture();
  const outcome = applySkillFilesToCache({ ...input, relativeFiles: null });
  assert.equal(outcome.copiedFiles.length, 2);
  assert.equal(readFileSync(join(cacheSkill, "references", "guide.md"), "utf8"), "new-guide");
  assert.ok(existsSync(join(cacheSkill, "only-in-cache.md")));
});

test("applySkillFilesToCache: 새 skill 폴더 생성", () => {
  const { cacheSkill, ...input } = createFixture();
  applySkillFilesToCache({ ...input, skillName: "bean-new-tool", relativeFiles: null });
  assert.equal(readFileSync(join(input.installPath, "skills", "bean-new-tool", "SKILL.md"), "utf8"), "new-skill");
});

for (const badPath of ["../evil.md", "references/../../evil.md", "/etc/evil.md"]) {
  test(`applySkillFilesToCache: 경로 ${badPath} 거부, 대상 무변경`, () => {
    const { cacheSkill, ...input } = createFixture();
    assert.throws(() => applySkillFilesToCache({ ...input, relativeFiles: ["SKILL.md", badPath] }), /경로/);
    assert.equal(readFileSync(join(cacheSkill, "SKILL.md"), "utf8"), "old-skill");
  });
}

test("applySkillFilesToCache: 원본에 없는 파일이면 아무것도 복사하지 않음", () => {
  const { cacheSkill, ...input } = createFixture();
  assert.throws(() => applySkillFilesToCache({ ...input, relativeFiles: ["SKILL.md", "missing.md"] }), /없습니다/);
  assert.equal(readFileSync(join(cacheSkill, "SKILL.md"), "utf8"), "old-skill");
});

for (const skillName of ["bean-skill-manager", "../bean-proposal", "other-skill"]) {
  test(`applySkillFilesToCache: 대상 ${skillName} 거부`, () => {
    const { cacheSkill, ...input } = createFixture();
    assert.throws(() => applySkillFilesToCache({ ...input, skillName, relativeFiles: null }), /대상/);
  });
}

test("findPluginInstallPath: 설치 기록에서 경로 조회", () => {
  const directory = createDirectory();
  writeFile(join(directory, "plugins", "installed_plugins.json"), JSON.stringify({ version: 2, plugins: { "beantal-kit@beantal-kit-marketplace": [{ scope: "user", installPath: "/cache/0.10.0" }] } }));
  assert.equal(findPluginInstallPath(directory), "/cache/0.10.0");
});

test("findPluginInstallPath: 기록 없음·깨진 파일이면 null", () => {
  const missing = createDirectory();
  assert.equal(findPluginInstallPath(missing), null);
  const broken = createDirectory();
  writeFile(join(broken, "plugins", "installed_plugins.json"), "{ not json");
  assert.equal(findPluginInstallPath(broken), null);
  const other = createDirectory();
  writeFile(join(other, "plugins", "installed_plugins.json"), JSON.stringify({ plugins: {} }));
  assert.equal(findPluginInstallPath(other), null);
});

test("resolveClaudeConfigDirectory: CLAUDE_CONFIG_DIR 우선, 없으면 ~/.claude", () => {
  assert.equal(resolveClaudeConfigDirectory({ CLAUDE_CONFIG_DIR: "/custom" }, "/base"), "/custom");
  assert.equal(resolveClaudeConfigDirectory({}, "/base"), join("/base", ".claude"));
});
