// Claude Code 플러그인 캐시 반영: 설치 경로 조회, 백업 후 덮어쓰기 (파일 삭제 없음)
import { copyFileSync, existsSync, mkdirSync, readFileSync, readdirSync, statSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, isAbsolute, join, normalize, relative, sep } from "node:path";

const DEFAULT_PLUGIN_ID = "beantal-kit@beantal-kit-marketplace";
const REPAIRABLE_SKILL_NAME = /^bean-[a-z0-9]+(-[a-z0-9]+)*$/;
// 자동 수리가 자기 자신을 고치지 못하게 제외
const SELF_SKILL_NAME = "bean-skill-manager";

export function resolveClaudeConfigDirectory(environment = process.env, homeDirectory = homedir()) {
  return environment.CLAUDE_CONFIG_DIR || join(homeDirectory, ".claude");
}

/** installed_plugins.json > 빈털킷 installPath (없거나 깨진 기록은 null) */
export function findPluginInstallPath(claudeConfigDirectory, pluginId = DEFAULT_PLUGIN_ID) {
  try {
    const installed = JSON.parse(readFileSync(join(claudeConfigDirectory, "plugins", "installed_plugins.json"), "utf8"));
    return installed.plugins?.[pluginId]?.[0]?.installPath || null;
  } catch {
    return null;
  }
}

function isSafeRelativePath(relativePath) {
  if (!relativePath || isAbsolute(relativePath)) return false;
  return !normalize(relativePath).split(sep).includes("..");
}

function listFilesRelativeTo(baseDirectory, currentDirectory = baseDirectory) {
  return readdirSync(currentDirectory).flatMap((name) => {
    const path = join(currentDirectory, name);
    return statSync(path).isDirectory() ? listFilesRelativeTo(baseDirectory, path) : [relative(baseDirectory, path)];
  });
}

function copyWithParents(sourcePath, targetPath) {
  mkdirSync(dirname(targetPath), { recursive: true });
  copyFileSync(sourcePath, targetPath);
}

/**
 * skill 파일 캐시 반영: 대상 검증 > 파일 검증 > 백업 > 덮어쓰기
 * relativeFiles null: 폴더 전체 (새 skill)
 */
export function applySkillFilesToCache({ sourceSkillDirectory, installPath, skillName, relativeFiles, backupDirectory }) {
  if (!REPAIRABLE_SKILL_NAME.test(skillName) || skillName === SELF_SKILL_NAME) {
    throw new Error(`반영할 수 없는 대상입니다: ${skillName}`);
  }
  const filesToCopy = relativeFiles ?? listFilesRelativeTo(sourceSkillDirectory);

  // 검증 먼저 (일부만 바뀐 상태 방지)
  for (const relativePath of filesToCopy) {
    if (!isSafeRelativePath(relativePath)) throw new Error(`허용되지 않는 경로입니다: ${relativePath}`);
    if (!existsSync(join(sourceSkillDirectory, relativePath))) throw new Error(`원본에 파일이 없습니다: ${relativePath}`);
  }

  const cacheSkillDirectory = join(installPath, "skills", skillName);
  const backedUpFiles = [];
  for (const relativePath of filesToCopy) {
    const cachePath = join(cacheSkillDirectory, relativePath);
    if (existsSync(cachePath)) {
      copyWithParents(cachePath, join(backupDirectory, relativePath));
      backedUpFiles.push(relativePath);
    }
    copyWithParents(join(sourceSkillDirectory, relativePath), cachePath);
  }
  return { copiedFiles: filesToCopy, backedUpFiles };
}
