#!/usr/bin/env python3
"""渲染驱动：起静态服务 → 跑引擎 → 收工。一条命令走完录制、混音、质检。

引擎的 ES module 必须走 http 协议，所以每次都要有个本地静态服务；这个脚本把服务、
浏览器路径、环境变量全包了，不用自己拼命令。

用法
  python3 render.py <系列目录> <期号>                  # 录制 + 混音 + 质检，出完整 mp4
  python3 render.py <系列目录> <期号> --still 2,10,30   # 只出样帧接触表（改完版式先看这个）
  python3 render.py <系列目录> <期号> --record-only     # 只录制，不混音
  python3 render.py <系列目录> <期号> --finish-only     # 只混音（改了 BGM／音量／时间轴就不必重录）
  python3 render.py <系列目录> <期号> --from 20 --to 34 # 只重录这一段（改了几秒的镜头，不用整片重跑）
  python3 render.py <系列目录> <期号> --qa-only         # 只对已有成片跑质检

浏览器：默认复用它系统里已装的 Chrome / Chromium / Edge，不下载 Playwright 的 chromium。
  想指定就设 CINE_CHROME=/path/to/chrome
端口：默认 8964，被占就设 CINE_PORT
"""
from __future__ import annotations

import functools
import http.server
import os
import shutil
import socketserver
import subprocess
import sys
import threading
from pathlib import Path

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/snap/bin/chromium",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def find_chrome() -> str | None:
    env = os.environ.get("CINE_CHROME")
    if env and Path(env).exists():
        return env
    for p in CHROME_CANDIDATES:
        if Path(p).exists():
            return p
    for name in ("google-chrome", "chromium", "chrome", "msedge"):
        got = shutil.which(name)
        if got:
            return got
    return None


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    series = Path(sys.argv[1]).expanduser().resolve()
    if not (series / "cine/engine/core.js").exists():
        raise SystemExit(f"{series} 不像系列目录（缺 cine/engine/core.js）。先跑 new_film.py。")

    args = sys.argv[2:]
    lid = args[0]
    flags = [a for a in args[1:] if a.startswith("--")]
    only_still = "--still" in flags
    record_only = "--record-only" in flags
    finish_only = "--finish-only" in flags
    qa_only = "--qa-only" in flags
    skip_qa = "--skip-qa" in flags

    chrome = find_chrome()
    if not chrome:
        raise SystemExit("没找到 Chrome/Chromium/Edge。装一个，或设 CINE_CHROME=/path/to/chrome")
    port = int(os.environ.get("CINE_PORT", "8964"))
    env = {**os.environ, "CINE_PY": sys.executable, "CINE_CHROME": chrome}

    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", port),
                                   functools.partial(Quiet, directory=str(series)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    print(f"服务 127.0.0.1:{port} → {series}\n浏览器 {chrome}", flush=True)

    def run(cmd: list[str], optional: bool = False) -> int:
        print(f"\n▸ {' '.join(Path(c).name if i == 0 else c for i, c in enumerate(cmd))}", flush=True)
        r = subprocess.run([sys.executable, *cmd], cwd=series, env=env)
        if r.returncode != 0 and not optional:
            httpd.shutdown()
            sys.exit(r.returncode)
        return r.returncode

    try:
        if only_still:
            i = sys.argv.index("--still")
            times = sys.argv[i + 1] if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith("--") else "2,10,30"
            out = f"lessons/{lid}/stills/sheet.png"
            run(["cine/tools/stills.py", lid, out, *times.split(","), "--cols", "3", "--w", "560"])
            print(f"\n→ {series/out}")
        elif qa_only:
            mp4 = series / f"lessons/{lid}/build/lesson{lid}.mp4"
            run([str(Path(__file__).resolve().parent / "qa.py"), str(mp4), "--every", "4"])
        else:
            if not finish_only:                      # 只改了 BGM / 音量 / 字幕时间轴就不必重录
                cmd = ["cine/tools/record.py", lid]
                for f in ("--from", "--to", "--out"):
                    if f in sys.argv:
                        cmd += [f, sys.argv[sys.argv.index(f) + 1]]
                run(cmd)
            if not record_only:
                run(["cine/tools/finish.py", lid])
                if not skip_qa:
                    mp4 = series / f"lessons/{lid}/build/lesson{lid}.mp4"
                    print()
                    run([str(Path(__file__).resolve().parent / "qa.py"), str(mp4), "--every", "4"],
                        optional=True)          # 质检失败不拦交付，只是报警
    finally:
        httpd.shutdown()

    print(f"\n产物：{series/f'lessons/{lid}/build/lesson{lid}.mp4'}")


if __name__ == "__main__":
    main()
