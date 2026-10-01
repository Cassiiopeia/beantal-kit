// skills/*/SKILL.md 검증: frontmatter, name==폴더명, bean- 접두사, description 필수.
import { readdirSync, readFileSync, existsSync, statSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parseFrontmatter } from "./lib/frontmatter.js";

export const PREFIX = "bean-";

export function checkSkills(skillsDir) {
  const errors = [];
  if (!existsSync(skillsDir)) return { ok: false, errors: [`${skillsDir}: skills 폴더가 없습니다`] };
  for (const name of readdirSync(skillsDir)) {
    const dir = join(skillsDir, name);
    if (!statSync(dir).isDirectory()) continue;
    if (!name.startsWith(PREFIX)) errors.push(`${name}: 폴더명은 '${PREFIX}'로 시작해야 합니다`);
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
