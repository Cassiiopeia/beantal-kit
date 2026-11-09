// 수리 대기열·잠금·배포 기록: 대화가 끊겨도 다음 대화에서 이어 가기 위한 파일 상태
import { randomBytes } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const QUEUE_FOLDER_NAME = "queue";
const LOCK_FILE_NAME = "repair.lock";
const DEPLOY_LOG_FILE_NAME = "deploys.json";
// 죽은 세션이 남긴 잠금 회수 기준 (2시간)
const DEFAULT_LOCK_STALE_MILLISECONDS = 2 * 60 * 60 * 1000;
const SAFE_REPAIR_ID = /^[0-9]+-[0-9a-f]+$/;

function resolveRepairPath(directory, id) {
  if (!SAFE_REPAIR_ID.test(id)) throw new Error(`잘못된 수리 id 입니다: ${id}`);
  return join(directory, QUEUE_FOLDER_NAME, `${id}.json`);
}

export function enqueueRepair(directory, repairRequest) {
  mkdirSync(join(directory, QUEUE_FOLDER_NAME), { recursive: true });
  const id = `${Date.now()}-${randomBytes(3).toString("hex")}`;
  writeFileSync(resolveRepairPath(directory, id), JSON.stringify({ ...repairRequest, id, status: "pending" }, null, 2));
  return id;
}

export function listPendingRepairs(directory) {
  const queueDirectory = join(directory, QUEUE_FOLDER_NAME);
  if (!existsSync(queueDirectory)) return [];
  return readdirSync(queueDirectory)
    .sort()
    .map((name) => JSON.parse(readFileSync(join(queueDirectory, name), "utf8")))
    .filter((repair) => repair.status === "pending");
}

export function completeRepair(directory, id) {
  const path = resolveRepairPath(directory, id);
  writeFileSync(path, JSON.stringify({ ...JSON.parse(readFileSync(path, "utf8")), status: "done" }, null, 2));
}

/** 잠금 획득 (wx 로 동시 생성 차단, 오래된 잠금은 회수) */
export function acquireRepairLock(directory, nowMilliseconds, staleMilliseconds = DEFAULT_LOCK_STALE_MILLISECONDS) {
  mkdirSync(directory, { recursive: true });
  const path = join(directory, LOCK_FILE_NAME);
  try {
    writeFileSync(path, String(nowMilliseconds), { flag: "wx" });
    return true;
  } catch (error) {
    if (error.code !== "EEXIST") throw error;
  }
  const lockedAtMilliseconds = Number(readFileSync(path, "utf8"));
  const isLockFresh = Number.isFinite(lockedAtMilliseconds) && nowMilliseconds - lockedAtMilliseconds <= staleMilliseconds;
  if (isLockFresh) return false;
  writeFileSync(path, String(nowMilliseconds));
  return true;
}

export function releaseRepairLock(directory) {
  rmSync(join(directory, LOCK_FILE_NAME), { force: true });
}

// 사용자 PC 기준 날짜 (YYYY-MM-DD)
const toLocalDateKey = (date) => date.toLocaleDateString("en-CA");

function readDeployDateKeys(directory) {
  try {
    return JSON.parse(readFileSync(join(directory, DEPLOY_LOG_FILE_NAME), "utf8"));
  } catch {
    return [];
  }
}

export function recordDeploy(directory, now) {
  mkdirSync(directory, { recursive: true });
  writeFileSync(join(directory, DEPLOY_LOG_FILE_NAME), JSON.stringify([...readDeployDateKeys(directory), toLocalDateKey(now)]));
}

export function countDeploysOn(directory, now) {
  const dateKey = toLocalDateKey(now);
  return readDeployDateKeys(directory).filter((deployDateKey) => deployDateKey === dateKey).length;
}
