import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, readdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { checkSkills } from "../scripts/check-skills.js";
import { createSkill } from "../scripts/new-skill.js";
import { parseFrontmatter } from "../scripts/lib/frontmatter.js";

const tmp = () => mkdtempSync(join(tmpdir(), "bean-"));
const put = (root, folder, content) => {
  mkdirSync(join(root, folder), { recursive: true });
  writeFileSync(join(root, folder, "SKILL.md"), content);
};
const good = (name) => `---\nname: ${name}\ndescription: "desc"\n---\n본문\n`;

test("checkSkills: 정상 skill 은 ok", () => {
  const root = tmp();
  put(root, "bean-a", good("bean-a"));
  assert.deepEqual(checkSkills(root), { ok: true, errors: [] });
});

test("checkSkills: CRLF 파일도 ok", () => {
  const root = tmp();
  put(root, "bean-a", good("bean-a").replace(/\n/g, "\r\n"));
  assert.equal(checkSkills(root).ok, true);
});

for (const [label, folder, content, re] of [
  ["frontmatter 없음", "bean-a", "그냥 본문", /frontmatter/],
  ["name 불일치", "bean-a", good("bean-b"), /폴더명과 다릅니다/],
  ["접두사 위반", "foo-x", good("foo-x"), /bean-/],
  ["description 누락", "bean-a", "---\nname: bean-a\n---\n", /description/],
]) {
  test(`checkSkills: ${label} → 오류`, () => {
    const root = tmp();
    put(root, folder, content);
    const r = checkSkills(root);
    assert.equal(r.ok, false);
    assert.match(r.errors.join("\n"), re);
  });
}

for (const file of ["제안서.pptx", "a.PPT", "x/y.pdf", "data.zip", "r.docx", "t.xlsx", "h.hwp"]) {
  test(`checkSkills: 문서 파일 ${JSON.stringify(file)} 이 skills 안에 있으면 실패`, () => {
    const root = tmp();
    put(root, "bean-a", good("bean-a"));
    const target = join(root, "bean-a", file);
    mkdirSync(dirname(target), { recursive: true });
    writeFileSync(target, "x");
    const r = checkSkills(root);
    assert.equal(r.ok, false);
    assert.match(r.errors.join("\n"), /민감|문서 파일/);
  });
}

test("checkSkills: 확장자가 아닌 이름 끝(mypdf, zip-helper)은 문서 파일로 오인하지 않는다", () => {
  const root = tmp();
  put(root, "bean-a", good("bean-a"));
  writeFileSync(join(root, "bean-a", "mypdf"), "x");
  writeFileSync(join(root, "bean-a", "unzip"), "x");
  assert.equal(checkSkills(root).ok, true);
});

test("checkSkills: md, js, json 같은 일반 파일은 허용", () => {
  const root = tmp();
  put(root, "bean-a", good("bean-a"));
  mkdirSync(join(root, "bean-a", "scripts"), { recursive: true });
  writeFileSync(join(root, "bean-a", "scripts", "run.js"), "x");
  writeFileSync(join(root, "bean-a", "template.example.yaml"), "x");
  assert.equal(checkSkills(root).ok, true);
});

test("createSkill: 접두사 자동/중복 방지, check 통과, 재생성 거부", () => {
  const root = tmp();
  createSkill(root, "my-tool");
  assert.equal(checkSkills(root).ok, true);
  assert.throws(() => createSkill(root, "bean-my-tool"), /이미 존재/);
  createSkill(root, "bean-other");
  assert.deepEqual(readdirSync(root).sort(), ["bean-my-tool", "bean-other"]);
});

for (const bad of ["Bad Name", "../x", "", "a/b", "UP"]) {
  test(`createSkill: ${JSON.stringify(bad)} 거부, 디렉터리 변화 없음`, () => {
    const root = tmp();
    assert.throws(() => createSkill(root, bad));
    assert.deepEqual(readdirSync(root), []);
  });
}

test("parseFrontmatter: 따옴표 제거, 없으면 null", () => {
  assert.equal(parseFrontmatter("x"), null);
  assert.equal(parseFrontmatter('---\nname: "a"\n---\n').data.name, "a");
});

test("레포의 실제 skills/ 는 검증을 통과한다", () => {
  const root = resolve(dirname(fileURLToPath(import.meta.url)), "..", "skills");
  assert.deepEqual(checkSkills(root), { ok: true, errors: [] });
});
