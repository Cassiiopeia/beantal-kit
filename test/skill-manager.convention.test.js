import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, readdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { checkSkills } from "../scripts/check-skills.js";
import { createSkill } from "../scripts/new-skill.js";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const skillsDirectory = join(root, "skills");

for (const skillName of readdirSync(skillsDirectory)) {
  test(`${skillName}: 개인 취향 파일 규약 언급`, () => {
    assert.match(readFileSync(join(skillsDirectory, skillName, "SKILL.md"), "utf8"), /preferences\.md/);
  });
}

test("new-skill 뼈대: 개인 취향 파일 규약 포함, check 통과", () => {
  const directory = mkdtempSync(join(tmpdir(), "manager-convention-"));
  const { path } = createSkill(directory, "my-tool");
  assert.match(readFileSync(path, "utf8"), /~\/\.beantal-kit\/configs\/bean-my-tool\/preferences\.md/);
  assert.deepEqual(checkSkills(directory), { ok: true, errors: [] });
});

test("라벨 파일에 자동수리 존재", () => {
  const labels = readFileSync(join(root, ".github", "config", "issue-labels.yml"), "utf8");
  assert.ok(labels.includes("name: 자동수리"));
});

test("CLAUDE.md: hook 과 skill 폴더 수정 범위 명시", () => {
  const rules = readFileSync(join(root, "CLAUDE.md"), "utf8");
  assert.ok(rules.includes("`hooks/`"));
  assert.ok(rules.includes("`skills/bean-<이름>/` 폴더"));
});

test("자동 배포 스위치 기본값은 켜짐", () => {
  assert.equal(JSON.parse(readFileSync(join(skillsDirectory, "bean-skill-manager", "auto-deploy.json"), "utf8")).enabled, true);
});
