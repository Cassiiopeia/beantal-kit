import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { checkSkills } from "../scripts/check-skills.js";
import { createSkill } from "../scripts/new-skill.js";

const tmp = () => mkdtempSync(join(tmpdir(), "os-"));
const fm = (name) => `---\nname: ${name}\ndescription: "desc"\n---\n`;
function skill(root, rel, text, name = "bean-a") {
  mkdirSync(join(root, name, ...rel.split("/").slice(0, -1)), { recursive: true });
  if (!rel.includes("/") && rel === "SKILL.md") writeFileSync(join(root, name, rel), fm(name) + text);
  else {
    mkdirSync(join(root, name), { recursive: true });
    writeFileSync(join(root, name, "SKILL.md"), fm(name));
    writeFileSync(join(root, name, rel), text);
  }
}

for (const [label, text] of [
  ["Windows 드라이브 경로", "파일은 C:\\Users\\kim\\docs 에 있다"],
  ["Windows 드라이브 경로 (슬래시)", "열기: D:/work/제안서"],
  ["macOS 홈 절대 경로", "열기: /Users/kim/Documents/제안서.pptx"],
  ["Linux 홈 절대 경로", "복사: cp a /home/kim/b"],
]) {
  test(`OS 고정 절대 경로 금지: ${label} (SKILL.md)`, () => {
    const root = tmp();
    skill(root, "SKILL.md", text);
    const r = checkSkills(root);
    assert.equal(r.ok, false);
    assert.match(r.errors.join("\n"), /OS 고정 절대 경로/);
  });
}

test("OS 고정 절대 경로 금지는 스크립트 파일에도 적용된다", () => {
  const root = tmp();
  skill(root, "scripts/run.js", 'const p = "C:\\\\Users\\\\kim\\\\x";');
  const r = checkSkills(root);
  assert.equal(r.ok, false);
  assert.match(r.errors.join("\n"), /scripts\/run\.js/);
});

test("환경 기준 표기(~, $HOME, %USERPROFILE%, 상대 경로, URL)는 허용한다", () => {
  const root = tmp();
  skill(root, "SKILL.md", [
    "설정: `~/.beantal-kit/configs/bean-a/config.json`",
    "Windows: `%USERPROFILE%\\.beantal-kit\\configs\\bean-a\\config.json`",
    'POSIX: "$HOME/.beantal-kit"',
    "상대: ./references/a.md 와 ../shared/b.md",
    "주소: https://example.com/Users/profile 과 http://host:8080/home/x",
    "루트 슬래시 단독 설명: 경로 구분자는 / 이다",
  ].join("\n"));
  assert.deepEqual(checkSkills(root), { ok: true, errors: [] });
});

test("new-skill 뼈대에 OS 호환 섹션이 들어간다 (옵션 없이도)", () => {
  const root = tmp();
  const { path } = createSkill(root, "plain");
  const md = readFileSync(path, "utf8");
  assert.match(md, /## OS 호환/);
  assert.match(md, /macOS/);
  assert.match(md, /Windows/);
  assert.deepEqual(checkSkills(root), { ok: true, errors: [] });
});

test("CLAUDE.md 가 OS 호환 규칙을 명시한다", () => {
  const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
  const md = readFileSync(join(root, "CLAUDE.md"), "utf8");
  for (const s of ["macOS", "Windows", "OS 고정 절대 경로"]) assert.ok(md.includes(s), s);
});

test("교차 OS CI 워크플로우가 세 OS 를 모두 포함한다", () => {
  const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
  const y = readFileSync(join(root, ".github", "workflows", "BEANTAL-CI-MATRIX.yaml"), "utf8");
  for (const s of ["ubuntu-latest", "macos-latest", "windows-latest", "npm test", "npm run check"]) assert.ok(y.includes(s), s);
});
