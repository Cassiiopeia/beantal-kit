import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { acquireRepairLock, completeRepair, countDeploysOn, enqueueRepair, listPendingRepairs, recordDeploy, releaseRepairLock } from "../skills/bean-skill-manager/scripts/lib/work_queue.mjs";
import { collectSensitiveTerms, findSensitiveTerms } from "../skills/bean-skill-manager/scripts/lib/sensitive_scan.mjs";

const createDirectory = () => mkdtempSync(join(tmpdir(), "manager-queue-"));
const HOUR_MILLISECONDS = 3600000;

test("대기열: 등록, 조회, 완료", () => {
  const directory = createDirectory();
  const firstId = enqueueRepair(directory, { summary: "첫 요구" });
  const secondId = enqueueRepair(directory, { summary: "둘째 요구" });
  assert.deepEqual(listPendingRepairs(directory).map((repair) => repair.summary).sort(), ["둘째 요구", "첫 요구"]);
  completeRepair(directory, firstId);
  assert.deepEqual(listPendingRepairs(directory).map((repair) => repair.id), [secondId]);
});

test("대기열: 폴더 없음이면 빈 목록", () => {
  assert.deepEqual(listPendingRepairs(join(createDirectory(), "missing")), []);
});

test("대기열: 경로를 벗어나는 id 거부", () => {
  assert.throws(() => completeRepair(createDirectory(), "../evil"), /id/);
});

test("잠금: 중복 획득 실패, 해제 후 재획득", () => {
  const directory = createDirectory();
  assert.equal(acquireRepairLock(directory, 1000), true);
  assert.equal(acquireRepairLock(directory, 2000), false);
  releaseRepairLock(directory);
  assert.equal(acquireRepairLock(directory, 3000), true);
});

test("잠금: 2시간 지난 잠금 회수, 이내면 유지", () => {
  const directory = createDirectory();
  assert.equal(acquireRepairLock(directory, 0), true);
  assert.equal(acquireRepairLock(directory, 2 * HOUR_MILLISECONDS), false);
  assert.equal(acquireRepairLock(directory, 2 * HOUR_MILLISECONDS + 1), true);
});

test("배포 기록: 날짜별 집계", () => {
  const directory = createDirectory();
  const today = new Date(2026, 10, 9, 10);
  recordDeploy(directory, today);
  recordDeploy(directory, new Date(2026, 10, 9, 23));
  recordDeploy(directory, new Date(2026, 10, 8, 23));
  assert.equal(countDeploysOn(directory, today), 2);
  assert.equal(countDeploysOn(directory, new Date(2026, 10, 7)), 0);
});

function createProfile() {
  const home = createDirectory();
  mkdirSync(join(home, "shared", "company"), { recursive: true });
  mkdirSync(join(home, "configs", "bean-proposal"), { recursive: true });
  writeFileSync(join(home, "shared", "company", "company.json"), JSON.stringify({ name: { value: "가상물류", status: "confirmed" }, employees: { value: "2026", status: "conflict" } }));
  writeFileSync(join(home, "configs", "bean-proposal", "references.json"), JSON.stringify({ projects: [{ client: "테스트고객", title: "운영 제안" }] }));
  return home;
}

test("collectSensitiveTerms: 회사 프로필, 고객사 수집, status·숫자 제외", () => {
  const terms = collectSensitiveTerms(createProfile());
  assert.ok(terms.includes("가상물류"));
  assert.ok(terms.includes("테스트고객"));
  assert.ok(!terms.includes("confirmed"));
  assert.ok(!terms.includes("2026"));
});

test("collectSensitiveTerms: 프로필 없음이면 빈 목록", () => {
  assert.deepEqual(collectSensitiveTerms(createDirectory()), []);
});

test("findSensitiveTerms: 포함된 용어만 반환, 대소문자 무시", () => {
  assert.deepEqual(findSensitiveTerms("ACME 제안서의 표가 넘친다", ["acme", "다른회사"]), ["acme"]);
  assert.deepEqual(findSensitiveTerms("표가 슬라이드를 넘친다", ["acme"]), []);
});
