// 공개 레포 유입 차단용 민감 용어 수집·검사 (회사 프로필, 등록된 고객사)
import { readFileSync } from "node:fs";
import { join } from "node:path";

// 값 상태·출처 표기 칸은 회사 정보가 아님
const IGNORED_KEYS = new Set(["status", "source"]);
const HANGUL = /\p{Script=Hangul}/u;
const LETTER = /\p{L}/u;
const MINIMUM_HANGUL_TERM_LENGTH = 2;
const MINIMUM_LATIN_TERM_LENGTH = 3;

function readJsonOrNull(path) {
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch {
    return null;
  }
}

function isTermCandidate(text) {
  const term = text.trim();
  if (!LETTER.test(term)) return false;
  return term.length >= (HANGUL.test(term) ? MINIMUM_HANGUL_TERM_LENGTH : MINIMUM_LATIN_TERM_LENGTH);
}

function collectStringValues(node) {
  if (typeof node === "string") return isTermCandidate(node) ? [node.trim()] : [];
  if (Array.isArray(node)) return node.flatMap(collectStringValues);
  if (node && typeof node === "object") {
    return Object.entries(node)
      .filter(([key]) => !IGNORED_KEYS.has(key) && !key.startsWith("_"))
      .flatMap(([, value]) => collectStringValues(value));
  }
  return [];
}

export function collectSensitiveTerms(beantalKitHome) {
  const companyProfile = readJsonOrNull(join(beantalKitHome, "shared", "company", "company.json"));
  const references = readJsonOrNull(join(beantalKitHome, "configs", "bean-proposal", "references.json"));
  const projectTerms = (references?.projects || []).flatMap((project) => collectStringValues([project.client, project.title]));
  return [...new Set([...collectStringValues(companyProfile), ...projectTerms])];
}

export function findSensitiveTerms(text, terms) {
  const lowerText = text.toLowerCase();
  return terms.filter((term) => lowerText.includes(term.toLowerCase()));
}
