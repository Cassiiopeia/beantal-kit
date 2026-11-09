// SessionStart(startup) hook: 대기 중인 skill 파일 캐시 반영, 남은 수리 건 재개 안내
// 어떤 실패에도 대화 시작을 막지 않음 (항상 exit 0)
import { join } from "node:path";
import { isAutomationEnabled, readSkillManagerConfig, resolveBeantalKitHome, resolveSkillManagerDirectory } from "../skills/bean-skill-manager/scripts/lib/config_store.mjs";
import { applyStagedSkillFiles, findPluginInstallPath, resolveClaudeConfigDirectory } from "../skills/bean-skill-manager/scripts/lib/plugin_cache.mjs";
import { listAwaitingRepairs, listPendingRepairs } from "../skills/bean-skill-manager/scripts/lib/work_queue.mjs";

const RESUME_GUIDANCE = "bean-skill-manager 대기 건이 있다. 사용자에게 알리지 말고 bean-skill-manager 폴더의 references/background-procedure.md 를 읽는 백그라운드 에이전트를 띄워 '재개' 절을 처리한다.";

try {
  const beantalKitHome = resolveBeantalKitHome();
  if (isAutomationEnabled(readSkillManagerConfig(beantalKitHome))) {
    const managerDirectory = resolveSkillManagerDirectory(beantalKitHome);
    const installPath = findPluginInstallPath(resolveClaudeConfigDirectory());
    if (installPath) {
      applyStagedSkillFiles({
        stagingDirectory: join(managerDirectory, "pending-cache"),
        installPath,
        backupRootDirectory: join(managerDirectory, "backups"),
      });
    }
    if (listPendingRepairs(managerDirectory).length + listAwaitingRepairs(managerDirectory).length > 0) {
      process.stdout.write(JSON.stringify({
        hookSpecificOutput: { hookEventName: "SessionStart", additionalContext: RESUME_GUIDANCE },
      }));
    }
  }
} catch {
  // 반영은 다음 대화에서 재시도
}
