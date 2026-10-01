// 테스트용 stub io. responder(cmd,args) 가 {code,stdout,stderr} 일부를 돌려주면 덮어쓴다.
export function makeStubIo({ missing = [], responder = () => ({}) } = {}) {
  const calls = [];
  const logs = [];
  return {
    calls, logs,
    which: (cmd) => (missing.includes(cmd) ? null : `/bin/${cmd}`),
    run: (cmd, args = []) => {
      calls.push([cmd, ...args]);
      return { code: 0, stdout: "", stderr: "", ...responder(cmd, args) };
    },
    home: () => "/home/x",
    log: (msg) => logs.push(String(msg)),
  };
}
