import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { isAutomationEnabled, readSkillManagerConfig, resolveBeantalKitHome } from "../skills/bean-skill-manager/scripts/lib/config_store.mjs";

const createHome = () => mkdtempSync(join(tmpdir(), "manager-config-"));
function writeConfig(home, body) {
  const directory = join(home, "configs", "bean-skill-manager");
  mkdirSync(directory, { recursive: true });
  writeFileSync(join(directory, "config.json"), typeof body === "string" ? body : JSON.stringify(body));
}

test("resolveBeantalKitHome: 홈 폴더 아래 .beantal-kit", () => {
  assert.equal(resolveBeantalKitHome("/base"), join("/base", ".beantal-kit"));
});

test("readSkillManagerConfig: 파일 없음 > 기본값, 자동화 꺼짐", () => {
  const config = readSkillManagerConfig(createHome());
  assert.equal(config.enabled, false);
  assert.equal(config.daily_deploy_limit, 3);
  assert.equal(isAutomationEnabled(config), false);
});

test("readSkillManagerConfig: 깨진 JSON > 자동화 꺼짐", () => {
  const home = createHome();
  writeConfig(home, "{ not json");
  assert.equal(isAutomationEnabled(readSkillManagerConfig(home)), false);
});

for (const [label, values, expected] of [
  ["repo_path + enabled", { repo_path: "~/beantal-kit", enabled: true }, true],
  ["repo_path 없음", { repo_path: "", enabled: true }, false],
  ["enabled false", { repo_path: "~/beantal-kit", enabled: false }, false],
  ["enabled 문자열", { repo_path: "~/beantal-kit", enabled: "true" }, false],
]) {
  test(`isAutomationEnabled: ${label}`, () => {
    const home = createHome();
    writeConfig(home, { "skill-manager": values });
    assert.equal(isAutomationEnabled(readSkillManagerConfig(home)), expected);
  });
}

test("readSkillManagerConfig: 지정 값이 기본값보다 우선", () => {
  const home = createHome();
  writeConfig(home, { "skill-manager": { daily_deploy_limit: 1, maintainer_github: "owner" } });
  const config = readSkillManagerConfig(home);
  assert.equal(config.daily_deploy_limit, 1);
  assert.equal(config.maintainer_github, "owner");
});
