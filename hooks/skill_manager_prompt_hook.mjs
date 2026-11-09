// UserPromptSubmit hook: 활성화한 PC에서만 수정 요구 분류 안내 주입 (판단은 Claude)
// 어떤 실패에도 사용자 대화를 막지 않음 (항상 exit 0)
import { isAutomationEnabled, readSkillManagerConfig, resolveBeantalKitHome } from "../skills/bean-skill-manager/scripts/lib/config_store.mjs";

const REPAIR_GUIDANCE = "bean-skill-manager 활성: 사용자가 bean-* skill 결과의 수정을 요구하거나 '앞으로', '매번', '자주'처럼 지속 적용을 말하면 현재 작업을 먼저 처리하고 bean-skill-manager skill의 4단계 분류를 따른다. 해당 없으면 이 안내를 무시한다.";

try {
  if (isAutomationEnabled(readSkillManagerConfig(resolveBeantalKitHome()))) {
    process.stdout.write(JSON.stringify({
      hookSpecificOutput: { hookEventName: "UserPromptSubmit", additionalContext: REPAIR_GUIDANCE },
    }));
  }
} catch {
  // 안내는 보조 기능이므로 실패를 무시
}
