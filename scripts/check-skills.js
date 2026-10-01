// skills/*/SKILL.md 검증: frontmatter, name==폴더명, bean- 접두사, description 필수.
import { readdirSync, readFileSync, existsSync, statSync } from "node:fs";
import { join, dirname, resolve, basename } from "node:path";
import { fileURLToPath } from "node:url";
import { parseFrontmatter } from "./lib/frontmatter.js";

export const PREFIX = "bean-";

// 공개 레포·npm 패키지에 실수로 들어가면 안 되는 문서 파일 (제안서, 보고서, 회사 자료 등).
const DOC_EXT = /\.(pptx?|pdf|zip|docx?|xlsx?|hwpx?)$/i;

// 실제 토큰처럼 보이는 값 (example 에는 값을 비워 두어야 한다).
const SECRET_LIKE = /(npm_|ghp_|gho_|ghs_|github_pat_|sk-ant-|sk-|AKIA)[A-Za-z0-9_-]{16,}/;
const ALLOWED_TOP = new Set(["language", "output"]);

function checkConfigExample(name, file, errors) {
  const text = readFileSync(file, "utf8");
  if (SECRET_LIKE.test(text)) errors.push(`${name}: config.json.example 에 실제 토큰처럼 보이는 값이 있습니다. 값은 비워 두세요`);
  let obj;
  try { obj = JSON.parse(text); } catch { errors.push(`${name}: config.json.example 이 유효한 JSON 이 아닙니다`); return; }
  const ns = name.startsWith(PREFIX) ? name.slice(PREFIX.length) : name;
  if (!obj || typeof obj !== "object" || !(ns in obj)) errors.push(`${name}: config.json.example 의 최상위 키 '${ns}' 가 필요합니다`);
  for (const k of Object.keys(obj || {})) {
    if (k === ns || k.startsWith("_") || ALLOWED_TOP.has(k)) continue;
    errors.push(`${name}: config.json.example 에 허용되지 않은 최상위 키가 있습니다: ${k}`);
  }
}

function listFiles(dir) {
  const out = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) out.push(...listFiles(p));
    else out.push(p);
  }
  return out;
}

export function checkSkills(skillsDir) {
  const errors = [];
  if (!existsSync(skillsDir)) return { ok: false, errors: [`${skillsDir}: skills 폴더가 없습니다`] };
  for (const name of readdirSync(skillsDir)) {
    const dir = join(skillsDir, name);
    if (!statSync(dir).isDirectory()) continue;
    if (!name.startsWith(PREFIX)) errors.push(`${name}: 폴더명은 '${PREFIX}'로 시작해야 합니다`);
    for (const f of listFiles(dir)) {
      if (DOC_EXT.test(f)) errors.push(`${name}: 문서 파일은 공개 레포에 넣을 수 없습니다 (민감 정보 가능성): ${f.slice(dir.length + 1)}`);
    }
    for (const f of listFiles(dir)) {
      if (basename(f) === "config.json") errors.push(`${name}: ${f.slice(dir.length + 1)} 는 둘 수 없습니다. 설정은 플러그인 밖 ~/.beantal-kit/configs/${name}/config.json 에만 둡니다`);
    }
    const example = join(dir, "config.json.example");
    if (existsSync(example)) checkConfigExample(name, example, errors);
    const file = join(dir, "SKILL.md");
    if (!existsSync(file)) { errors.push(`${name}: SKILL.md가 없습니다`); continue; }
    const fm = parseFrontmatter(readFileSync(file, "utf8"));
    if (!fm) { errors.push(`${name}: frontmatter가 없습니다`); continue; }
    if (!fm.data.name) errors.push(`${name}: name이 비어 있습니다`);
    else if (fm.data.name !== name) errors.push(`${name}: name('${fm.data.name}')이 폴더명과 다릅니다`);
    if (!fm.data.description) errors.push(`${name}: description이 비어 있습니다`);
  }
  return { ok: errors.length === 0, errors };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const root = resolve(dirname(fileURLToPath(import.meta.url)), "..", "skills");
  const { ok, errors } = checkSkills(root);
  if (!ok) { for (const e of errors) console.error(`✖ ${e}`); process.exit(1); }
  console.log("✔ 모든 skill 검증 통과");
}
