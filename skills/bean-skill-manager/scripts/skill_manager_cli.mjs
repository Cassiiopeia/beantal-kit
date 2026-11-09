#!/usr/bin/env node
// bean-skill-manager CLI: 설정 상태, 캐시 반영, 배포 판정, 대기열, 잠금, 민감 정보 검사
// 출력: JSON {ok, code, summary, next}
import { execFileSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { parseArgs } from "node:util";
import { isAutomationEnabled, readSkillManagerConfig, resolveBeantalKitHome, resolveSkillManagerDirectory } from "./lib/config_store.mjs";
import { applySkillFilesToCache, findPluginInstallPath, resolveClaudeConfigDirectory } from "./lib/plugin_cache.mjs";
import { decideReleaseAction } from "./lib/release_gate.mjs";
import { collectSensitiveTerms, findSensitiveTerms } from "./lib/sensitive_scan.mjs";
import { acquireRepairLock, completeRepair, countDeploysOn, enqueueRepair, listPendingRepairs, recordDeploy, releaseRepairLock } from "./lib/work_queue.mjs";

const beantalKitHome = resolveBeantalKitHome();
const managerDirectory = resolveSkillManagerDirectory(beantalKitHome);
const config = readSkillManagerConfig(beantalKitHome);

const createResult = (ok, code, summary, next = null, extra = {}) => ({ ok, code, summary, next, ...extra });

function readStatus() {
  if (!isAutomationEnabled(config)) {
    return createResult(true, "not_configured", "automation is off", "run the setup conversation in SKILL.md");
  }
  const installPath = findPluginInstallPath(resolveClaudeConfigDirectory());
  const hasRepository = existsSync(join(config.repo_path, ".git"));
  const hasProjectops = existsSync(join(homedir(), ".projectops", "config", "config.json"));
  const details = { hasRepository, hasProjectops, installPath };
  if (!installPath) return createResult(true, "not_installed", "beantal-kit plugin is not installed", "npx beantal-kit", details);
  return createResult(true, "ready", "automation is ready", null, details);
}

function applyCache(options) {
  const installPath = findPluginInstallPath(resolveClaudeConfigDirectory());
  if (!installPath) return createResult(false, "not_installed", "beantal-kit plugin is not installed", "npx beantal-kit");
  // 백업: {설정 폴더}/backups/{skill}/{yyyyMMddHHmmss}
  const stamp = new Date().toISOString().replace(/\D/g, "").slice(0, 14);
  const outcome = applySkillFilesToCache({
    sourceSkillDirectory: options.source,
    installPath,
    skillName: options.skill,
    relativeFiles: options.files ? options.files.split(",") : null,
    backupDirectory: join(managerDirectory, "backups", options.skill, stamp),
  });
  return createResult(true, "applied", `${outcome.copiedFiles.length} file(s) applied`, null, outcome);
}

function readGitOutput(repositoryPath, args) {
  return execFileSync("git", ["-C", repositoryPath, ...args], { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });
}

// origin/develop 의 차단 스위치 조회 (못 읽으면 차단으로 처리)
function isRemoteDeployEnabled(repositoryPath) {
  try {
    return JSON.parse(readGitOutput(repositoryPath, ["show", "origin/develop:skills/bean-skill-manager/auto-deploy.json"])).enabled === true;
  } catch {
    return false;
  }
}

function readUnreleasedCommitHashes(repositoryPath) {
  try {
    return readGitOutput(repositoryPath, ["rev-list", "origin/main..origin/develop"]).split("\n").filter(Boolean);
  } catch {
    return ["unreadable"];
  }
}

function decideRelease(options) {
  const repositoryPath = options.repo || config.repo_path;
  const decision = decideReleaseAction({
    isRepositoryCheckPassed: options["checks-passed"] === "true",
    isVerificationPassed: options.verified === "true",
    unreleasedCommitHashes: readUnreleasedCommitHashes(repositoryPath),
    ownCommitHashes: (options["own-commits"] || "").split(",").filter(Boolean),
    isRemoteDeployEnabled: isRemoteDeployEnabled(repositoryPath),
    deployCountToday: countDeploysOn(managerDirectory, new Date()),
    dailyDeployLimit: config.daily_deploy_limit,
  });
  return createResult(true, decision.action, `release decision: ${decision.action} (${decision.reason})`, null, decision);
}

// 용어 원문은 출력에 넣지 않음 (대화 기록·이슈 유입 방지)
function scanText(options) {
  const count = findSensitiveTerms(readFileSync(options.file, "utf8"), collectSensitiveTerms(beantalKitHome)).length;
  return count > 0
    ? createResult(false, "sensitive_found", `${count} sensitive term(s) found`, "generalize the text and scan again", { count })
    : createResult(true, "clean", "no sensitive term found", null, { count });
}

const COMMANDS = {
  status: readStatus,
  "apply-cache": applyCache,
  "release-decision": decideRelease,
  scan: scanText,
  "queue-add": (options) => {
    const id = enqueueRepair(managerDirectory, JSON.parse(readFileSync(options["request-file"], "utf8")));
    return createResult(true, "queued", `queued ${id}`, null, { id });
  },
  "queue-list": () => {
    const pending = listPendingRepairs(managerDirectory);
    return createResult(true, "ok", `${pending.length} pending`, null, { pending });
  },
  "queue-done": (options) => {
    completeRepair(managerDirectory, options.id);
    return createResult(true, "done", `completed ${options.id}`);
  },
  lock: () => (acquireRepairLock(managerDirectory, Date.now())
    ? createResult(true, "locked", "lock acquired")
    : createResult(false, "busy", "another repair is running", "queue this request with queue-add")),
  unlock: () => {
    releaseRepairLock(managerDirectory);
    return createResult(true, "unlocked", "lock released");
  },
  "record-deploy": () => {
    recordDeploy(managerDirectory, new Date());
    return createResult(true, "recorded", "deploy recorded");
  },
};

const OPTION_NAMES = ["skill", "source", "files", "repo", "own-commits", "checks-passed", "verified", "file", "request-file", "id"];

function runCommand(args) {
  const { values, positionals } = parseArgs({
    args,
    allowPositionals: true,
    options: Object.fromEntries(OPTION_NAMES.map((name) => [name, { type: "string" }])),
  });
  const handler = COMMANDS[positionals[0]];
  if (!handler) return createResult(false, "bad_args", `unknown command: ${positionals[0]}`, `one of: ${Object.keys(COMMANDS).join(", ")}`);
  return handler(values);
}

let commandResult;
try {
  commandResult = runCommand(process.argv.slice(2));
} catch (error) {
  commandResult = createResult(false, "failed", error.message);
}
process.stdout.write(`${JSON.stringify(commandResult)}\n`);
process.exitCode = commandResult.ok ? 0 : 1;
