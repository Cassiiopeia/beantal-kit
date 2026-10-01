import { test } from "node:test";
import assert from "node:assert/strict";
import { assertAdapter } from "../src/adapters/adapter.js";
import { ADAPTERS, adapterById } from "../src/adapters/registry.js";
import { parseMarketplace } from "../src/adapters/marketplaces.js";

test("assertAdapter: 필수 필드 누락 시 throw", () => {
  assert.throws(() => assertAdapter({ id: "x" }), /필수 필드/);
});

test("ADAPTERS: id 순서 claude, codex / adapterById", () => {
  assert.deepEqual(ADAPTERS.map((a) => a.id), ["claude", "codex"]);
  assert.equal(adapterById("nope"), null);
  assert.equal(adapterById("codex").id, "codex");
});

test("parseMarketplace: owner/repo[:name]", () => {
  assert.deepEqual(parseMarketplace("me/priv"), { source: "me/priv", name: "priv-marketplace", codexName: "priv" });
  assert.deepEqual(parseMarketplace("me/priv:custom"), { source: "me/priv", name: "custom", codexName: "custom" });
  assert.throws(() => parseMarketplace("bad"), /잘못된/);
});
