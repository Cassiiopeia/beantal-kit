// 자동 배포 판정: 조건 5개를 우선순위대로 확인, 부족하면 배포 없이 푸시까지만

/**
 * 판정 순서: 레포 검사 > 원격 차단 > 샘플 검증 > 다른 미배포 커밋 > 일일 상한
 * action: deploy 배포, push-only develop 푸시까지, stop 푸시 금지
 */
export function decideReleaseAction({
  isRepositoryCheckPassed,
  isVerificationPassed,
  unreleasedCommitHashes,
  ownCommitHashes,
  isRemoteDeployEnabled,
  deployCountToday,
  dailyDeployLimit,
}) {
  if (!isRepositoryCheckPassed) return { action: "stop", reason: "checks_failed" };
  if (!isRemoteDeployEnabled) return { action: "push-only", reason: "remote_deploy_disabled" };
  if (!isVerificationPassed) return { action: "push-only", reason: "verification_missing" };
  const ownCommitHashSet = new Set(ownCommitHashes);
  if (unreleasedCommitHashes.some((hash) => !ownCommitHashSet.has(hash))) {
    return { action: "push-only", reason: "other_unreleased_commits" };
  }
  if (deployCountToday >= dailyDeployLimit) return { action: "push-only", reason: "daily_limit_reached" };
  return { action: "deploy", reason: "ready" };
}
