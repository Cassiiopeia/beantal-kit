// npm run new-skill <이름> [-- --config] : skills/bean-<이름>/SKILL.md 뼈대 생성.
// --config: 설정이 필요한 skill. 규약(플러그인 밖 ~/.beantal-kit/ 에만 설정 저장)을 지키는 SKILL.md 설정 섹션과 config.json.example 을 함께 만든다.
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { PREFIX } from "./check-skills.js";

const NAME_RE = /^[a-z0-9]+(-[a-z0-9]+)*$/;

// SKILL.md 에 넣는 설정 규약. 사용자가 비개발자일 수 있으므로 Claude 가 대화로 관리한다.
// (마크다운의 백틱과 Windows 경로의 역슬래시를 템플릿 리터럴에서 안전하게 쓰기 위해 줄 배열로 만든다.)
function configSection(name) {
  return [
    "",
    "## 설정 (config)",
    "",
    `- 설정 파일 위치는 고정이다: \`~/.beantal-kit/configs/${name}/config.json\` (Windows: \`%USERPROFILE%\\.beantal-kit\\configs\\${name}\\config.json\`). 탐색하지 말고 이 경로를 바로 읽는다.`,
    "- 템플릿은 이 skill 폴더의 `config.json.example` 이다. 각 칸의 의미는 `_comment_*` 에 적혀 있다.",
    "- **플러그인 폴더(캐시) 안에는 설정을 절대 쓰지 않는다.** 플러그인을 업데이트하면 폴더가 바뀌어 설정이 사라진 것처럼 보인다. 업데이트 후 설정이 없어 보이면 삭제됐다고 단정하지 말고 위 경로를 먼저 확인한다.",
    "- 설정이 없으면 `config.json.example` 을 기준으로 **한 번에 한 질문**씩 물어 파일을 만든다. 사용자가 파일을 직접 편집하게 하지 않는다.",
    "- 기존 값은 덮어쓰지 않는다. 새 버전에서 키가 늘었으면 빠진 키만 보충한다.",
    "- 비밀번호, 토큰은 화면에 출력할 때 마스킹한다.",
    "",
  ].join("\n");
}

// 모든 skill 에 들어가는 OS 호환 규칙 (macOS, Windows 양쪽에서 동작해야 한다).
function osSection() {
  return [
    "",
    "## OS 호환 (macOS, Windows)",
    "",
    "- 홈 폴더는 `~`, `$HOME`, `%USERPROFILE%` 로만 표기한다. 드라이브 문자나 사용자 이름이 들어간 절대 경로는 쓰지 않는다 (`npm run check` 가 막는다).",
    "- 파일 읽기, 쓰기, 수정은 가능하면 agent 도구(Read, Write, Edit)로 한다. 셸 명령은 macOS 와 Windows 에서 똑같이 동작하는 것만 쓴다.",
    "- Python, Node 같은 실행 환경이 필요하면 이 문서에 필요 조건, 확인 명령, 없을 때의 안내를 적는다. 사용자는 개발자가 아닐 수 있다.",
    "- 파일은 UTF-8, 줄바꿈은 LF 로 저장한다. 한글 파일명이나 공백이 든 경로는 따옴표로 감싼다.",
    "- 경로 구분자를 직접 이어 붙이지 말고 도구나 path 함수를 쓴다.",
    "",
  ].join("\n");
}

function configExample(short) {
  return JSON.stringify({
    [short]: {
      _comment_example: "이 칸의 의미와 입력 예시를 적는다. 값은 비워 둔다. 토큰, 비밀번호 같은 실제 값은 절대 적지 않는다.",
      example: "",
    },
    _required: [],
    language: "ko",
  }, null, 2) + "\n";
}

export function createSkill(skillsDir, rawName, { config = false } = {}) {
  const raw = String(rawName || "").trim();
  if (!NAME_RE.test(raw)) throw new Error(`skill 이름은 소문자, 숫자, 하이픈만 쓸 수 있습니다: '${raw}'`);
  const name = raw.startsWith(PREFIX) ? raw : `${PREFIX}${raw}`;
  const dir = join(skillsDir, name);
  if (existsSync(dir)) throw new Error(`이미 존재하는 skill입니다: ${name}`);
  mkdirSync(dir, { recursive: true });
  const path = join(dir, "SKILL.md");
  const body = `---
name: ${name}
description: "이 skill이 언제 쓰이는지 트리거 문구와 함께 구체적으로 적는다. 예: '~해줘', '~확인' 이라고 말할 때 사용."
---

# ${name}

## 언제 쓰는가

-

## 절차

1.
`;
  writeFileSync(path, body + osSection() + (config ? configSection(name) : ""));
  if (config) writeFileSync(join(dir, "config.json.example"), configExample(name.slice(PREFIX.length)));
  return { path };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const root = resolve(dirname(fileURLToPath(import.meta.url)), "..", "skills");
  try {
    const args = process.argv.slice(2);
    const { path } = createSkill(root, args.find((a) => !a.startsWith("--")), { config: args.includes("--config") });
    console.log(`✔ 생성: ${path}`);
  } catch (e) { console.error(`✖ ${e.message}`); process.exit(1); }
}
