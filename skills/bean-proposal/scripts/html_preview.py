"""HTML 작업본 미리보기 서버. 이 PC(127.0.0.1)에서만 열린다. deck.html 이 바뀌면 브라우저가 자동으로 새로고침한다.

  python html_preview.py <작업 폴더> --port 8765
"""
import argparse
import functools
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RELOAD = b"""<script>(function(){var v=null;
try{var y=sessionStorage.getItem('deck-y');if(y)addEventListener('load',function(){scrollTo(0,+y)})}catch(e){}
setInterval(function(){fetch('/__version',{cache:'no-store'}).then(function(r){return r.text()}).then(function(t){
if(v===null){v=t;return}if(t!==v){try{sessionStorage.setItem('deck-y',scrollY)}catch(e){}location.reload()}}).catch(function(){})},1000)})();</script>
"""


def version(root):
    stamps = []
    for name in ("deck.html", "deck.css", "deck.js"):
        p = root / name
        if p.exists():
            stamps.append(p.stat().st_mtime_ns)
    assets = root / "assets"
    if assets.exists():
        stamps.append(assets.stat().st_mtime_ns)
    return str(stamps)


class Handler(SimpleHTTPRequestHandler):
    root = None

    def log_message(self, *a):
        pass

    def _send(self, body, ctype):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/__version":
            return self._send(version(self.root).encode(), "text/plain")
        if path in ("/", "/deck.html"):
            body = (self.root / "deck.html").read_bytes().replace(b"</body>", RELOAD + b"</body>", 1)
            return self._send(body, "text/html; charset=utf-8")
        if path.rsplit("/", 1)[-1].startswith("."):      # .baseline.html 등 내부 파일은 내보내지 않는다
            return self.send_error(404)
        return super().do_GET()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--port", type=int, required=True)
    a = ap.parse_args()
    root = Path(a.dir).resolve()
    Handler.root = root
    os.chdir(root)
    ThreadingHTTPServer(("127.0.0.1", a.port), functools.partial(Handler, directory=str(root))).serve_forever()


if __name__ == "__main__":
    main()
