import { test } from "node:test";
import assert from "node:assert/strict";
import { decideReleaseAction } from "../skills/bean-skill-manager/scripts/lib/release_gate.mjs";

const readyInput = {
  isRepositoryCheckPassed: true,
  isVerificationPassed: true,
  unreleasedCommitHashes: ["own1"],
  ownCommitHashes: ["own1"],
  isRemoteDeployEnabled: true,
  deployCountToday: 0,
  dailyDeployLimit: 3,
};

for (const [label, override, action, reason] of [
  ["모두 정상", {}, "deploy", "ready"],
  ["레포 검사 실패", { isRepositoryCheckPassed: false }, "stop", "checks_failed"],
  ["샘플 미통과", { isVerificationPassed: false }, "push-only", "verification_missing"],
  ["다른 미배포 커밋", { unreleasedCommitHashes: ["own1", "other"] }, "push-only", "other_unreleased_commits"],
  ["원격 차단", { isRemoteDeployEnabled: false }, "push-only", "remote_deploy_disabled"],
  ["일일 상한 도달", { deployCountToday: 3 }, "push-only", "daily_limit_reached"],
  ["레포 검사 실패가 최우선", { isRepositoryCheckPassed: false, isRemoteDeployEnabled: false }, "stop", "checks_failed"],
]) {
  test(`decideReleaseAction: ${label}`, () => {
    assert.deepEqual(decideReleaseAction({ ...readyInput, ...override }), { action, reason });
  });
}
