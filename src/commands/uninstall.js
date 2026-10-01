// uninstall: 어댑터를 순회해 remove.
export function runUninstall({ io, adapters }) {
  let failed = 0;
  for (const a of adapters) {
    io.log(`[ ${a.label} 제거 ]`);
    if (!a.remove(io)) failed++;
  }
  return failed ? 1 : 0;
}
