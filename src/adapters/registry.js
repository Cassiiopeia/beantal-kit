// 어댑터 레지스트리: 유일한 확장 지점. 새 에이전트는 import + 배열에 1줄.
import { assertAdapter } from "./adapter.js";
import { claudeAdapter } from "./claude.js";
import { codexAdapter } from "./codex.js";

export const ADAPTERS = [claudeAdapter, codexAdapter]
  .map(assertAdapter)
  .sort((a, b) => (a.order ?? 100) - (b.order ?? 100));

export function adapterById(id) {
  return ADAPTERS.find((a) => a.id === id) || null;
}
