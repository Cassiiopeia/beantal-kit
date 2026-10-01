import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const json = (p) => JSON.parse(readFileSync(resolve(root, p), "utf8"));
const pkg = json("package.json");

test("매니페스트는 유효 JSON이고 이름이 일치한다", () => {
  assert.equal(json(".claude-plugin/plugin.json").name, "beantal-kit");
  const mp = json(".claude-plugin/marketplace.json");
  assert.equal(mp.name, "beantal-kit-marketplace");
  assert.equal(mp.plugins[0].name, "beantal-kit");
  assert.equal(mp.plugins[0].source, "./");
  assert.equal(json(".codex-plugin/plugin.json").skills, "./skills/");
  const ag = json(".agents/plugins/marketplace.json");
  assert.equal(ag.plugins[0].name, "beantal-kit");
  assert.equal(ag.plugins[0].source.path, ".");
});

test("모든 매니페스트의 version 은 package.json 과 같다", () => {
  assert.equal(json(".claude-plugin/plugin.json").version, pkg.version);
  assert.equal(json(".claude-plugin/marketplace.json").plugins[0].version, pkg.version);
  assert.equal(json(".codex-plugin/plugin.json").version, pkg.version);
});

test("마켓플레이스 상수가 매니페스트와 일치한다", async () => {
  const { MARKETPLACES, pluginId } = await import("../src/adapters/marketplaces.js");
  assert.equal(MARKETPLACES[0].name, json(".claude-plugin/marketplace.json").name);
  assert.equal(pluginId(MARKETPLACES[0]), "beantal-kit@beantal-kit-marketplace");
});

test("CLAUDE.md 와 publish 워크플로우가 존재하고 핵심 규칙을 담는다", () => {
  const md = readFileSync(resolve(root, "CLAUDE.md"), "utf8");
  for (const s of ["bean-", "npm run check", "projectops"]) assert.ok(md.includes(s), s);
  assert.ok(existsSync(resolve(root, ".github/workflows/PROJECT-NODE-NPM-PUBLISH.yaml")));
});

test("package.json 은 의존성 0, files 는 bin/src 만", () => {
  assert.deepEqual(pkg.dependencies, {});
  assert.deepEqual(pkg.files, ["bin/", "src/"]);
});
