// 외부 CLI 실행·감지 래퍼. 전부 io 로 주입 가능해 테스트는 stub 을 쓴다.
import { spawnSync } from "node:child_process";
import { delimiter, join } from "node:path";
import { existsSync } from "node:fs";
import { homedir } from "node:os";

// which(cmd) → 실행 파일 경로 or null. PATH 직접 스캔, Windows 는 PATHEXT 까지 시도.
export function which(cmd) {
  const dirs = (process.env.PATH || "").split(delimiter).filter(Boolean);
  const exts = process.platform === "win32"
    ? (process.env.PATHEXT || ".COM;.EXE;.BAT;.CMD").split(";").filter(Boolean)
    : [""];
  for (const dir of dirs) {
    for (const ext of exts) {
      const full = join(dir, cmd + ext);
      if (existsSync(full)) return full;
    }
  }
  return null;
}

// Windows 용 인자 인용: 공백·특수문자를 방어한다. (인자 내부의 큰따옴표는 cmd 경유 시 소실되므로 미지원 — 호출 인자는 고정값뿐)
function winQuote(arg) {
  const s = String(arg);
  if (s !== "" && !/[\s"&|<>^%()]/.test(s)) return s;
  return `"${s.replace(/(\\*)"/g, '$1$1\\"').replace(/(\\+)$/, "$1$1")}"`;
}

// run(cmd, args, opts) → {code, stdout, stderr}. 실행 자체 실패면 code=127.
export function run(cmd, args = [], opts = {}) {
  const common = { cwd: opts.cwd, env: opts.env || process.env, encoding: "utf8", windowsHide: true };
  if (!which(cmd)) return { code: 127, stdout: "", stderr: `command not found: ${cmd}` };
  let r;
  if (process.platform === "win32") {
    r = spawnSync([cmd, ...args].map(winQuote).join(" "), { ...common, shell: true });
  } else {
    r = spawnSync(cmd, args, common);
  }
  if (r.error || r.status == null) {
    return { code: 127, stdout: r.stdout || "", stderr: r.stderr || String(r.error?.message || "") };
  }
  return { code: r.status, stdout: r.stdout || "", stderr: r.stderr || "" };
}

export function defaultIo() {
  return { which, run, home: () => homedir(), log: (msg) => console.log(msg) };
}
