// Claude Code 어댑터: claude plugin marketplace/install/update/uninstall 호출.
import { MARKETPLACES, pluginId } from "./marketplaces.js";
import { failNote } from "./util.js";

function listPlugins(io) {
  const r = io.run("claude", ["plugin", "list", "--json"]);
  try {
    const parsed = JSON.parse(r.stdout || "[]");
    const list = Array.isArray(parsed) ? parsed : (parsed?.plugins || []);
    return Array.isArray(list) ? list : [];
  } catch { return []; }
}

function findPlugin(io, id) {
  return listPlugins(io).find((p) => String(p.name || p.id || "") === id) || null;
}

function detect(io, marketplaces = MARKETPLACES) {
  if (!io.which("claude")) return { installed: false, cliMissing: true, note: "CLI 없음" };
  const ids = marketplaces.map(pluginId);
  const hit = listPlugins(io).find((p) => ids.includes(String(p.name || p.id || "")));
  return { installed: !!hit, cliMissing: false, scope: hit?.scope || "user" };
}

function apply(io, marketplaces = MARKETPLACES) {
  try {
    if (!io.which("claude")) { io.log(manualHint(marketplaces)); return false; }
    let ok = true;
    for (const mp of marketplaces) {
      const id = pluginId(mp);
      const hit = findPlugin(io, id);
      if (hit) {
        const scope = hit.scope || "user";
        const up = io.run("claude", ["plugin", "update", id, "--scope", scope]);
        if (up.code === 0) io.log(`  업데이트 완료: ${id}`);
        else { io.log(`  업데이트 실패${failNote(up)}. 수동: claude plugin update ${id} --scope ${scope}`); ok = false; }
        continue;
      }
      const add = io.run("claude", ["plugin", "marketplace", "add", mp.source]);
      io.log(add.code === 0 ? `  마켓플레이스 등록: ${mp.source}` : `  마켓플레이스 이미 등록되어 있거나 등록 생략: ${mp.source}`);
      const ins = io.run("claude", ["plugin", "install", id, "--scope", "user"]);
      if (ins.code === 0) io.log(`  설치 완료: ${id}`);
      else { io.log(`  설치 실패${failNote(ins)}. 수동: claude plugin install ${id} --scope user`); ok = false; }
    }
    return ok;
  } catch (e) { io.log(`  Claude Code 처리 중 오류: ${e.message}`); return false; }
}

function remove(io, marketplaces = MARKETPLACES) {
  try {
    if (!io.which("claude")) { io.log("  Claude Code CLI가 없어 건너뜁니다"); return true; }
    let ok = true;
    for (const mp of marketplaces) {
      const id = pluginId(mp);
      const hit = findPlugin(io, id);
      if (!hit) continue;
      const scope = hit.scope || "user";
      const un = io.run("claude", ["plugin", "uninstall", id, "--scope", scope]);
      if (un.code === 0) io.log(`  제거 완료: ${id}`);
      else { io.log(`  제거 실패${failNote(un)}. 수동: claude plugin uninstall ${id} --scope ${scope}`); ok = false; }
    }
    return ok;
  } catch (e) { io.log(`  Claude Code 제거 중 오류: ${e.message}`); return false; }
}

function manualHint(marketplaces = MARKETPLACES) {
  const mp = marketplaces[0];
  return `  💡 Claude Code: claude plugin marketplace add ${mp.source}\n     claude plugin install ${pluginId(mp)} --scope user`;
}

export const claudeAdapter = {
  id: "claude", label: "Claude Code", order: 10, strategy: "marketplace",
  detect, apply, remove, manualHint,
};
