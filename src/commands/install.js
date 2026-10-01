// install: 어댑터를 순회해 apply. 한 어댑터의 실패가 다음 실행을 막지 않는다.
import { formatStatusTable } from "./status.js";

export function runInstall({ io, adapters }) {
  io.log("── 현재 상태 ──");
  for (const line of formatStatusTable(io, adapters)) io.log(line);
  io.log("");

  const summary = { ok: [], skipped: [], failed: [] };
  for (const a of adapters) {
    io.log(`[ ${a.label} ]`);
    const st = a.detect(io);
    if (st.cliMissing) {
      io.log(a.manualHint());
      summary.skipped.push(a.label);
      continue;
    }
    (a.apply(io) ? summary.ok : summary.failed).push(a.label);
  }

  io.log("");
  io.log(`요약: 성공 ${summary.ok.length} / 건너뜀 ${summary.skipped.length} / 실패 ${summary.failed.length}`);
  if (summary.failed.length) io.log(`실패: ${summary.failed.join(", ")}`);
  return summary.failed.length ? 1 : 0;
}
