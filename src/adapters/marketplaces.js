// 등록할 마켓플레이스 목록. private 마켓플레이스를 쓰려면 원소를 추가한다(또는 --marketplace).
//   source:    owner/repo (GitHub)
//   name:      Claude Code 마켓플레이스 이름 (.claude-plugin/marketplace.json 의 name)
//   codexName: Codex 마켓플레이스 이름 (.agents/plugins/marketplace.json 의 name)
// Claude Code 는 git 인증, 자동 업데이트에는 GITHUB_TOKEN 필요.
export const MARKETPLACES = [
  { source: "Cassiiopeia/beantal-kit", name: "beantal-kit-marketplace", codexName: "beantal-kit" },
];

export const PLUGIN_NAME = "beantal-kit";

export function pluginId(marketplace) {
  return `${PLUGIN_NAME}@${marketplace.name}`;
}

export function codexPluginId(marketplace) {
  return `${PLUGIN_NAME}@${marketplace.codexName}`;
}

// `--marketplace owner/repo[:name]` 로 받은 추가 마켓플레이스 파싱.
// 이름을 생략하면 Claude 는 <repo>-marketplace, Codex 는 <repo> 로 가정한다.
export function parseMarketplace(spec) {
  const [source, name] = String(spec).split(":");
  if (!/^[\w.-]+\/[\w.-]+$/.test(source || "")) throw new Error(`잘못된 마켓플레이스: ${spec} (owner/repo[:name] 형식)`);
  const repo = source.split("/")[1];
  return { source, name: name || `${repo}-marketplace`, codexName: name || repo };
}
