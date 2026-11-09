// bean-skill-manager 설정 조회: 위치 계산, 기본값 병합, 활성화 판정
import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

// config.json 최상위 키 (skill 이름에서 bean- 제외)
const CONFIG_NAMESPACE = "skill-manager";
const SKILL_FOLDER_NAME = "bean-skill-manager";

const DEFAULT_CONFIG = {
  repo_path: "",
  enabled: false,
  maintainer_github: "",
  // PC당 하루 자동 배포 상한 (회)
  daily_deploy_limit: 3,
};

export function resolveBeantalKitHome(homeDirectory = homedir()) {
  return join(homeDirectory, ".beantal-kit");
}

export function resolveSkillManagerDirectory(beantalKitHome) {
  return join(beantalKitHome, "configs", SKILL_FOLDER_NAME);
}

// ~/폴더 > 홈 기준 실제 경로 (config 예시 표기와 일치)
function expandHomePrefix(path) {
  return /^~[\\/]/.test(path) ? join(homedir(), path.slice(2)) : path;
}

/** 설정 파일 > 기본값 병합 (없거나 깨진 파일은 기본값, 자동화 꺼짐) */
export function readSkillManagerConfig(beantalKitHome) {
  try {
    const parsed = JSON.parse(readFileSync(join(resolveSkillManagerDirectory(beantalKitHome), "config.json"), "utf8"));
    const config = { ...DEFAULT_CONFIG, ...(parsed[CONFIG_NAMESPACE] || {}) };
    return { ...config, repo_path: expandHomePrefix(config.repo_path) };
  } catch {
    return { ...DEFAULT_CONFIG };
  }
}

/** 자동 수리 작동 조건 2개: repo_path 있음, enabled 가 정확히 true */
export function isAutomationEnabled(config) {
  return Boolean(config.repo_path) && config.enabled === true;
}
