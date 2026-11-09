// Claude Code 플러그인 캐시 반영: 설치 경로 조회, 대화 중 저장, 새 대화 시작 시 백업 후 덮어쓰기
import { copyFileSync, existsSync, mkdirSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from "node:fs";
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

// 복사 전 전체 검증 (일부만 바뀐 상태 방지) > 복사할 파일 목록
function resolveValidatedFiles({ sourceSkillDirectory, skillName, relativeFiles }) {
  if (!REPAIRABLE_SKILL_NAME.test(skillName) || skillName === SELF_SKILL_NAME) {
    throw new Error(`반영할 수 없는 대상입니다: ${skillName}`);
  }
  const filesToCopy = relativeFiles ?? listFilesRelativeTo(sourceSkillDirectory);
  for (const relativePath of filesToCopy) {
    if (!isSafeRelativePath(relativePath)) throw new Error(`허용되지 않는 경로입니다: ${relativePath}`);
    if (!existsSync(join(sourceSkillDirectory, relativePath))) throw new Error(`원본에 파일이 없습니다: ${relativePath}`);
  }
  return filesToCopy;
}

/**
 * 대화 중 저장만 수행 (scripts/ 는 실행마다 캐시에서 읽히므로 작업 중 교체 금지)
 * 구조: {stagingDirectory}/{skill}/files/..., {skill}/target.json
 */
export function stageSkillFilesForNextConversation({ sourceSkillDirectory, stagingDirectory, installPath, skillName, relativeFiles }) {
  const filesToStage = resolveValidatedFiles({ sourceSkillDirectory, skillName, relativeFiles });
  for (const relativePath of filesToStage) {
    copyWithParents(join(sourceSkillDirectory, relativePath), join(stagingDirectory, skillName, "files", relativePath));
  }
  writeFileSync(join(stagingDirectory, skillName, "target.json"), JSON.stringify({ installPath }));
  return { stagedFiles: filesToStage };
}

/** 새 대화 시작 시 대기본 반영 (플러그인이 업데이트돼 경로가 다르면 최신본 보호를 위해 폐기) */
export function applyStagedSkillFiles({ stagingDirectory, installPath, backupRootDirectory }) {
  const outcome = { appliedSkills: [], discardedSkills: [] };
  if (!existsSync(stagingDirectory)) return outcome;
  // 백업: {backupRootDirectory}/{skill}/{yyyyMMddHHmmss}
  const stamp = new Date().toISOString().replace(/\D/g, "").slice(0, 14);
  for (const skillName of readdirSync(stagingDirectory)) {
    const stagedSkillDirectory = join(stagingDirectory, skillName);
    const { installPath: stagedInstallPath } = JSON.parse(readFileSync(join(stagedSkillDirectory, "target.json"), "utf8"));
    if (stagedInstallPath === installPath) {
      applySkillFilesToCache({
        sourceSkillDirectory: join(stagedSkillDirectory, "files"),
        installPath,
        skillName,
        relativeFiles: null,
        backupDirectory: join(backupRootDirectory, skillName, stamp),
      });
      outcome.appliedSkills.push(skillName);
    } else {
      outcome.discardedSkills.push(skillName);
    }
    rmSync(stagedSkillDirectory, { recursive: true, force: true });
  }
  return outcome;
}

/**
 * skill 파일 캐시 반영: 대상·파일 검증 > 백업 > 덮어쓰기
 * relativeFiles null: 폴더 전체 (새 skill)
 */
export function applySkillFilesToCache({ sourceSkillDirectory, installPath, skillName, relativeFiles, backupDirectory }) {
  const filesToCopy = resolveValidatedFiles({ sourceSkillDirectory, skillName, relativeFiles });

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
