// version.yml 의 version 을 단일 기준으로 매니페스트 버전을 동기화한다.
// 대상: package.json, .claude-plugin/plugin.json, .claude-plugin/marketplace.json(plugins[0], metadata), .codex-plugin/plugin.json
// 사용: node scripts/sync-version.js  (변경된 파일 목록을 출력, 이미 맞으면 아무것도 안 함)
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const SEMVER = /^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$/;

// 줄 시작의 `version:` 만 읽는다(주석·version_code 무시).
export function readVersionYml(text) {
  const m = String(text).match(/^version:\s*["']?([^"'\s#]+)["']?/m);
  if (!m) throw new Error("version.yml 에서 version 을 찾지 못했습니다");
  if (!SEMVER.test(m[1])) throw new Error(`version 형식이 semver 가 아닙니다: ${m[1]}`);
  return m[1];
}

// [파일, 버전을 쓰는 위치들]
const TARGETS = [
  ["package.json", (o, v) => [["version", o, v]]],
  [".claude-plugin/plugin.json", (o, v) => [["version", o, v]]],
  [".claude-plugin/marketplace.json", (o, v) => [
    ...(o.plugins?.[0] ? [["version", o.plugins[0], v]] : []),
    ...(o.metadata ? [["version", o.metadata, v]] : []),
  ]],
  [".codex-plugin/plugin.json", (o, v) => [["version", o, v]]],
];

export function syncVersion(root) {
  const version = readVersionYml(readFileSync(join(root, "version.yml"), "utf8"));
  const changed = [];
  for (const [rel, slots] of TARGETS) {
    const path = join(root, rel);
    if (!existsSync(path)) continue;
    const obj = JSON.parse(readFileSync(path, "utf8"));
    let dirty = false;
    for (const [key, target, v] of slots(obj, version)) {
      if (target[key] !== v) { target[key] = v; dirty = true; }
    }
    if (dirty) { writeFileSync(path, JSON.stringify(obj, null, 2) + "\n"); changed.push(rel); }
  }
  return changed;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
  try {
    const changed = syncVersion(root);
    console.log(changed.length ? `✔ 동기화: ${changed.join(", ")}` : "ℹ 이미 동기화되어 있습니다");
  } catch (e) { console.error(`✖ ${e.message}`); process.exit(1); }
}
