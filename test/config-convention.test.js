import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { checkSkills } from "../scripts/check-skills.js";
import { createSkill } from "../scripts/new-skill.js";
import { main } from "../src/cli.js";
import { makeStubIo } from "./helpers.js";

const tmp = () => mkdtempSync(join(tmpdir(), "cfg-"));
const good = (name) => `---\nname: ${name}\ndescription: "desc"\n---\n본문\n`;
function skill(root, folder, extra = {}) {
  mkdirSync(join(root, folder), { recursive: true });
  writeFileSync(join(root, folder, "SKILL.md"), good(folder));
  for (const [rel, body] of Object.entries(extra)) writeFileSync(join(root, folder, rel), typeof body === "string" ? body : JSON.stringify(body, null, 2));
}
const example = (key, extra = {}) => ({ [key]: { name: "", _comment_name: "회사명" }, language: "ko", ...extra });

test("skills 안의 config.json 은 실패 (설정은 플러그인 밖 ~/.beantal-kit 에만)", () => {
  const root = tmp();
  skill(root, "bean-proposal", { "config.json": { proposal: {} } });
  const r = checkSkills(root);
  assert.equal(r.ok, false);
  assert.match(r.errors.join("\n"), /config\.json.*~\/\.beantal-kit/);
});

test("config.json.example: 정상(네임스페이스 키 = skill 짧은 이름)은 통과", () => {
  const root = tmp();
  skill(root, "bean-proposal", { "config.json.example": example("proposal") });
  assert.deepEqual(checkSkills(root), { ok: true, errors: [] });
});

for (const [label, body, re] of [
  ["유효하지 않은 JSON", "{ not json", /JSON/],
  ["네임스페이스 키 누락", JSON.stringify({ other: {} }), /최상위 키 'proposal'/],
  ["허용되지 않은 최상위 키", JSON.stringify({ proposal: {}, extra: 1 }), /허용되지 않은 최상위 키/],
  ["실제 토큰처럼 보이는 값", JSON.stringify({ proposal: { token: "npm_ABCDEFGHIJKLMNOPQRSTUV123456" } }), /토큰/],
  ["GitHub 토큰", JSON.stringify({ proposal: { token: "ghp_ABCDEFGHIJKLMNOPQRSTUV1234567890" } }), /토큰/],
]) {
  test(`config.json.example: ${label} → 실패`, () => {
    const root = tmp();
    skill(root, "bean-proposal", { "config.json.example": body });
    const r = checkSkills(root);
    assert.equal(r.ok, false);
    assert.match(r.errors.join("\n"), re);
  });
}

test("config.json.example 에 _comment_*, _required, language, output 은 허용", () => {
  const root = tmp();
  skill(root, "bean-proposal", { "config.json.example": example("proposal", { _required: ["proposal.name"], output: { dir: "" }, _comment_top: "x" }) });
  assert.equal(checkSkills(root).ok, true);
});

test("new-skill --config: example 과 설정 섹션이 있는 뼈대를 만들고 check 를 통과한다", () => {
  const root = tmp();
  const { path } = createSkill(root, "my-tool", { config: true });
  assert.ok(existsSync(join(dirname(path), "config.json.example")));
  const md = readFileSync(path, "utf8");
  assert.match(md, /~\/\.beantal-kit\/configs\/bean-my-tool\/config\.json/);
  assert.match(md, /플러그인 폴더/);
  const ex = JSON.parse(readFileSync(join(dirname(path), "config.json.example"), "utf8"));
  assert.ok("my-tool" in ex);
  assert.deepEqual(checkSkills(root), { ok: true, errors: [] });
});

test("new-skill (옵션 없음): config 뼈대를 만들지 않는다", () => {
  const root = tmp();
  const { path } = createSkill(root, "plain");
  assert.ok(!existsSync(join(dirname(path), "config.json.example")));
});

function srcFiles(dir) {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n);
    return statSync(p).isDirectory() ? srcFiles(p) : p.endsWith(".js") ? [p] : [];
  });
}

test("불변 조건: 설치기 코드는 파일을 삭제하지 않는다 (uninstall 이 ~/.beantal-kit 를 지울 수 없다)", () => {
  const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
  for (const f of [...srcFiles(join(root, "src")), join(root, "bin", "beantal-kit.js")]) {
    const text = readFileSync(f, "utf8");
    assert.doesNotMatch(text, /\b(rmSync|rmdirSync|unlinkSync|rm|rmdir|unlink)\s*\(|fs\.promises\.rm|"rm"|'rm'/, f);
  }
});

test("uninstall 은 .beantal-kit 경로를 건드리는 명령을 실행하지 않는다", () => {
  const io = makeStubIo({ responder: (c, args) => (args.includes("list") ? { stdout: JSON.stringify([{ name: "beantal-kit@beantal-kit-marketplace", scope: "user" }]) } : {}) });
  assert.equal(main(["uninstall"], io), 0);
  assert.ok(io.calls.length > 0);
  for (const c of io.calls) assert.ok(!c.join(" ").includes(".beantal-kit"), c.join(" "));
});

test(".gitignore 가 skills 아래 config.json 을 막는다", () => {
  const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
  const gi = readFileSync(join(root, ".gitignore"), "utf8");
  assert.match(gi, /skills\/\*\*\/config\.json/);
});

test("CLAUDE.md 가 외부 설정 폴더 규약을 명시한다", () => {
  const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
  const md = readFileSync(join(root, "CLAUDE.md"), "utf8");
  for (const s of ["~/.beantal-kit/", "config.json.example", "플러그인 폴더", "업데이트"]) assert.ok(md.includes(s), s);
});
