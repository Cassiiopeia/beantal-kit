// status: detect 결과만 출력.
export function formatStatusTable(io, adapters) {
  return adapters.map((a) => {
    const st = a.detect(io);
    const label = a.label.padEnd(12);
    if (st.cliMissing) return `${label}: ${st.note || "CLI 없음"}`;
    if (st.installed) return `${label}: 설치됨${st.scope ? ` (scope: ${st.scope})` : ""}`;
    return `${label}: ${st.note || "미설치"}`;
  });
}

export function runStatus({ io, adapters }) {
  for (const line of formatStatusTable(io, adapters)) io.log(line);
  return 0;
}
