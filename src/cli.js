// CLI 진입 로직: 인자 파싱 → 어댑터 선택 → 명령 실행. 종료 코드를 반환한다.
import { ADAPTERS, adapterById } from "./adapters/registry.js";
import { parseMarketplace, MARKETPLACES } from "./adapters/marketplaces.js";
import { defaultIo } from "./runner.js";
import { runInstall } from "./commands/install.js";
import { runStatus } from "./commands/status.js";
import { runUninstall } from "./commands/uninstall.js";

const COMMANDS = ["install", "status", "uninstall"];

export const USAGE = `beantal-kit — 빈털 skill 키트 설치기

사용법: npx beantal-kit [install|status|uninstall] [옵션]

옵션:
  --only <id,id>          지정한 에이전트만 (예: claude,codex)
  --marketplace <o/r[:n]> 추가 마켓플레이스 등록 (private 레포 등, 반복 가능)
  --dry-run               실행할 명령만 출력 (조회는 실제 실행)
  -h, --help              도움말
`;

export function parseArgs(argv) {
  const out = { command: "install", only: null, dryRun: false, marketplaces: [] };
  const args = [...argv];
  if (args[0] && !args[0].startsWith("-")) {
    const c = args.shift();
    if (!COMMANDS.includes(c)) { out.command = "unknown"; out.unknown = c; return out; }
    out.command = c;
  }
  while (args.length) {
    const a = args.shift();
    if (a === "--help" || a === "-h") out.command = "help";
    else if (a === "--dry-run") out.dryRun = true;
    else if (a === "--only") out.only = String(args.shift() || "").split(",").map((s) => s.trim()).filter(Boolean);
    else if (a === "--marketplace") out.marketplaces.push(args.shift() || "");
    else { out.command = "unknown"; out.unknown = a; return out; }
  }
  return out;
}

// dry-run: 조회성 호출("list")만 실제 실행하고 나머지는 출력만 한다.
function dryRunIo(io) {
  return {
    ...io,
    run: (cmd, args = [], opts) => {
      if (args.includes("list")) return io.run(cmd, args, opts);
      io.log(`[dry-run] ${cmd} ${args.join(" ")}`);
      return { code: 0, stdout: "", stderr: "" };
    },
  };
}

export function main(argv, baseIo = defaultIo()) {
  const opts = parseArgs(argv);
  if (opts.command === "help") { baseIo.log(USAGE); return 0; }
  if (opts.command === "unknown") { baseIo.log(`알 수 없는 명령/옵션: ${opts.unknown}\n\n${USAGE}`); return 2; }

  let adapters = ADAPTERS;
  if (opts.only) {
    opts.only = [...new Set(opts.only)];
    if (!opts.only.length) { baseIo.log("--only 에 에이전트 id 가 필요합니다 (예: --only claude,codex)"); return 2; }
    const bad = opts.only.filter((id) => !adapterById(id));
    if (bad.length) {
      baseIo.log(`알 수 없는 에이전트: ${bad.join(", ")} (사용 가능: ${ADAPTERS.map((a) => a.id).join(", ")})`);
      return 2;
    }
    adapters = opts.only.map(adapterById);
  }

  // 추가 마켓플레이스: 어댑터의 기본 MARKETPLACES 에 합쳐 전달한다.
  let marketplaces = MARKETPLACES;
  try {
    if (opts.marketplaces.length) marketplaces = [...MARKETPLACES, ...opts.marketplaces.map(parseMarketplace)];
  } catch (e) { baseIo.log(e.message); return 2; }
  if (marketplaces !== MARKETPLACES) {
    adapters = adapters.map((a) => ({
      ...a,
      apply: (io) => a.apply(io, marketplaces),
      remove: (io) => a.remove(io, marketplaces),
      detect: (io) => a.detect(io, marketplaces),
      manualHint: () => a.manualHint(marketplaces),
    }));
  }

  const io = opts.dryRun ? dryRunIo(baseIo) : baseIo;
  const ctx = { io, adapters };
  let code;
  if (opts.command === "status") code = runStatus(ctx);
  else if (opts.command === "uninstall") code = runUninstall(ctx);
  else code = runInstall(ctx);
  if (opts.dryRun) io.log("\n(dry-run: 위 [dry-run] 명령은 실제로 실행되지 않았습니다)");
  return code;
}
