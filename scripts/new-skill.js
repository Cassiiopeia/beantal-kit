// npm run new-skill <이름> : skills/bean-<이름>/SKILL.md 뼈대 생성.
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { PREFIX } from "./check-skills.js";

const NAME_RE = /^[a-z0-9]+(-[a-z0-9]+)*$/;

export function createSkill(skillsDir, rawName) {
  const raw = String(rawName || "").trim();
  if (!NAME_RE.test(raw)) throw new Error(`skill 이름은 소문자, 숫자, 하이픈만 쓸 수 있습니다: '${raw}'`);
  const name = raw.startsWith(PREFIX) ? raw : `${PREFIX}${raw}`;
  const dir = join(skillsDir, name);
  if (existsSync(dir)) throw new Error(`이미 존재하는 skill입니다: ${name}`);
  mkdirSync(dir, { recursive: true });
  const path = join(dir, "SKILL.md");
  writeFileSync(path, `---
name: ${name}
description: "이 skill이 언제 쓰이는지 트리거 문구와 함께 구체적으로 적는다. 예: '~해줘', '~확인' 이라고 말할 때 사용."
---

# ${name}

## 언제 쓰는가

-

## 절차

1.
`);
  return { path };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const root = resolve(dirname(fileURLToPath(import.meta.url)), "..", "skills");
  try {
    const { path } = createSkill(root, process.argv[2]);
    console.log(`✔ 생성: ${path}`);
  } catch (e) { console.error(`✖ ${e.message}`); process.exit(1); }
}
