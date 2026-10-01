// Codex CLI 어댑터: codex plugin marketplace add/upgrade/remove + plugin add/remove/list.
import { MARKETPLACES, PLUGIN_NAME, codexPluginId } from "./marketplaces.js";
import { failNote } from "./util.js";

// `codex plugin list --json` → { installed: [...], available: [...] }. 항목 형태가 확정되지 않아
// 항목을 문자열화해 "<plugin>@<marketplace>" 또는 (name, marketplace) 조합으로 느슨하게 판정한다.
function isInstalled(io, mp) {
  const r = io.run("codex", ["plugin", "list", "--json"]);
  let installed;
  try { installed = JSON.parse(r.stdout || "{}")?.installed; } catch { return false; }
  if (!Array.isArray(installed)) return false;
  const id = codexPluginId(mp);
  return installed.some((p) => JSON.stringify(p).includes(id) || (p?.name === PLUGIN_NAME && p?.marketplace === mp.codexName));
}

function detect(io, marketplaces = MARKETPLACES) {
  if (!io.which("codex")) return { installed: false, cliMissing: true, note: "CLI 없음" };
  const installed = marketplaces.some((mp) => isInstalled(io, mp));
  return { installed, cliMissing: false };
}

function apply(io, marketplaces = MARKETPLACES) {
  try {
    if (!io.which("codex")) { io.log(manualHint(marketplaces)); return false; }
    let ok = true;
    for (const mp of marketplaces) {
      const add = io.run("codex", ["plugin", "marketplace", "add", mp.source]);
      io.log(add.code === 0 ? `  Codex 마켓플레이스 등록: ${mp.source}` : `  Codex 마켓플레이스 이미 등록되어 있거나 등록 생략: ${mp.source}`);
      const up = io.run("codex", ["plugin", "marketplace", "upgrade", mp.codexName]);
      if (up.code !== 0) io.log(`  마켓플레이스 갱신 실패${failNote(up)}. 수동: codex plugin marketplace upgrade ${mp.codexName}`);
      if (isInstalled(io, mp)) { io.log(`  이미 설치됨: ${codexPluginId(mp)}`); continue; }
      const ins = io.run("codex", ["plugin", "add", codexPluginId(mp)]);
      if (ins.code === 0) io.log(`  설치 완료: ${codexPluginId(mp)}`);
      else { io.log(`  설치 실패${failNote(ins)}. 수동: codex plugin add ${codexPluginId(mp)}`); ok = false; }
    }
    return ok;
  } catch (e) { io.log(`  Codex 처리 중 오류: ${e.message}`); return false; }
}

function remove(io, marketplaces = MARKETPLACES) {
  try {
    if (!io.which("codex")) { io.log("  Codex CLI가 없어 건너뜁니다"); return true; }
    for (const mp of marketplaces) {
      if (isInstalled(io, mp)) {
        const un = io.run("codex", ["plugin", "remove", codexPluginId(mp)]);
        if (un.code !== 0) io.log(`  플러그인 제거 실패${failNote(un)}. 수동: codex plugin remove ${codexPluginId(mp)}`);
      }
      const r = io.run("codex", ["plugin", "marketplace", "remove", mp.codexName]);
      if (r.code !== 0) io.log(`  마켓플레이스 해제 실패${failNote(r)}. 수동: codex plugin marketplace remove ${mp.codexName}`);
    }
    return true;
  } catch (e) { io.log(`  Codex 제거 중 오류: ${e.message}`); return true; }
}

function manualHint(marketplaces = MARKETPLACES) {
  const mp = marketplaces[0];
  return `  💡 Codex CLI: codex plugin marketplace add ${mp.source}\n     codex plugin add ${codexPluginId(mp)}`;
}

export const codexAdapter = {
  id: "codex", label: "Codex CLI", order: 40, strategy: "marketplace",
  detect, apply, remove, manualHint,
};
