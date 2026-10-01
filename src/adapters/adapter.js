// 에이전트 어댑터 공통 계약. 새 에이전트 = 이 shape 의 객체 1개 + registry.js 1줄.
//
// {
//   id, label, order,
//   strategy: "marketplace",            // 추후 "copy" (cursor 등 마켓플레이스 없는 에이전트)
//   detect(io, marketplaces?) -> { installed, cliMissing, scope?, note? },
//   apply(io, marketplaces?)  -> boolean,   // 멱등 설치/업데이트
//   remove(io, marketplaces?) -> boolean,
//   (marketplaces 생략 시 marketplaces.js 의 MARKETPLACES. --marketplace 로 추가분이 합쳐져 전달된다)
//   manualHint() -> string
// }
// 규칙: 예외를 던지지 않는다(로그 + false). 외부와는 io(which/run/home/log)로만 통신한다.

export function assertAdapter(a) {
  for (const k of ["id", "label", "detect", "apply", "remove", "manualHint"]) {
    if (a?.[k] == null) throw new Error(`어댑터 '${a?.id || "?"}'에 필수 필드 '${k}'가 없습니다`);
  }
  return a;
}
