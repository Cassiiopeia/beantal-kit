// 실패한 명령의 원인 한 줄(stderr 우선, 없으면 stdout)을 뽑아 로그용 문자열로 만든다.
export function failNote(result) {
  const text = String(result?.stderr || result?.stdout || "").split(/\r?\n/).map((s) => s.trim()).find(Boolean);
  return text ? ` (${text})` : "";
}
