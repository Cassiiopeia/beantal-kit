import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { readVersionYml, syncVersion } from "../scripts/sync-version.js";

const write = (root, rel, obj) => {
  mkdirSync(dirname(join(root, rel)), { recursive: true });
  writeFileSync(join(root, rel), typeof obj === "string" ? obj : JSON.stringify(obj, null, 2) + "\n");
};
const read = (root, rel) => JSON.parse(readFileSync(join(root, rel), "utf8"));

function fixture(version = "0.2.0") {
  const root = mkdtempSync(join(tmpdir(), "sync-"));
  write(root, "version.yml", `# 주석 version: "9.9.9"\nversion: "${version}"\nversion_code: 1\n`);
  write(root, "package.json", { name: "x", version: "0.1.0" });
  write(root, ".claude-plugin/plugin.json", { name: "x", version: "0.1.0" });
  write(root, ".claude-plugin/marketplace.json", { name: "m", metadata: { version: "0.1.0" }, plugins: [{ name: "x", version: "0.1.0" }] });
  write(root, ".codex-plugin/plugin.json", { name: "x", version: "0.1.0" });
  return root;
}

test("readVersionYml: 주석은 무시하고 version 키만 읽는다 (따옴표 유무, CRLF 허용)", () => {
  assert.equal(readVersionYml('# version: "9"\r\nversion: "1.2.3"\r\n'), "1.2.3");
  assert.equal(readVersionYml("version: 1.2.3\n"), "1.2.3");
  assert.throws(() => readVersionYml("name: x\n"), /version/);
  assert.throws(() => readVersionYml('version: "abc"\n'), /semver|형식/);
});

test("syncVersion: version.yml 값으로 4개 파일 5곳을 맞추고 변경 파일을 돌려준다", () => {
  const root = fixture("0.2.0");
  const changed = syncVersion(root);
  assert.deepEqual(changed.sort(), [".claude-plugin/marketplace.json", ".claude-plugin/plugin.json", ".codex-plugin/plugin.json", "package.json"]);
  assert.equal(read(root, "package.json").version, "0.2.0");
  assert.equal(read(root, ".claude-plugin/plugin.json").version, "0.2.0");
  const mp = read(root, ".claude-plugin/marketplace.json");
  assert.equal(mp.plugins[0].version, "0.2.0");
  assert.equal(mp.metadata.version, "0.2.0");
  assert.equal(read(root, ".codex-plugin/plugin.json").version, "0.2.0");
});

test("syncVersion: 이미 맞으면 변경 없음(멱등), 없는 파일은 건너뜀", () => {
  const root = fixture("0.1.0");
  assert.deepEqual(syncVersion(root), []);
  const only = mkdtempSync(join(tmpdir(), "sync-"));
  write(only, "version.yml", 'version: "1.0.0"\n');
  write(only, "package.json", { name: "x", version: "0.0.1" });
  assert.deepEqual(syncVersion(only), ["package.json"]);
});

test("레포의 실제 매니페스트는 version.yml 과 일치한다", () => {
  const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
  const v = readVersionYml(readFileSync(join(root, "version.yml"), "utf8"));
  assert.equal(read(root, "package.json").version, v);
  assert.equal(read(root, ".claude-plugin/plugin.json").version, v);
  assert.equal(read(root, ".claude-plugin/marketplace.json").plugins[0].version, v);
  assert.equal(read(root, ".codex-plugin/plugin.json").version, v);
});
