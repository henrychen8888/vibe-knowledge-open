#!/usr/bin/env bash
# 一次性安装：建虚拟环境、装 Python 依赖、检查外部工具、自检渲染链路。
set -euo pipefail
cd "$(dirname "$0")"

say() { printf '\033[1m%s\033[0m\n' "$*"; }
ok()  { printf '  \033[32m✓\033[0m %s\n' "$*"; }
bad() { printf '  \033[31m✗\033[0m %s\n' "$*"; }

say "1/4 Python 环境"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  ok "已建 .venv"
else
  ok ".venv 已存在"
fi
PY="$PWD/.venv/bin/python"
[ -x "$PY" ] || PY="$PWD/.venv/bin/python3"
"$PY" -m pip install --quiet --upgrade pip
"$PY" -m pip install --quiet -r requirements.txt
ok "已安装 numpy scipy pillow playwright"

say "2/4 外部工具"
for c in ffmpeg ffprobe; do
  if command -v $c >/dev/null 2>&1; then
    v=$("$c" -version 2>/dev/null | head -1 | awk '{print $NF}' || true)
    ok "$c ${v}"
  else
    bad "$c 未安装 —— 编解码、抽帧、响度都要它，请先装"
  fi
done

CHROME=""
for p in "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
         "/Applications/Chromium.app/Contents/MacOS/Chromium" \
         "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge" \
         "/usr/bin/google-chrome" "/usr/bin/chromium" "/usr/bin/chromium-browser"; do
  [ -x "$p" ] && CHROME="$p" && break
done
if [ -n "$CHROME" ]; then ok "浏览器：$CHROME"; else bad "没找到 Chrome/Chromium/Edge —— 渲染需要它"; fi

if command -v swiftc >/dev/null 2>&1; then ok "swiftc（OCR 回读可用）"; else bad "swiftc 缺失 —— 质检会跳过 OCR 回读，其余照常"; fi

say "3/4 可选增强"
"$PY" - <<'PY'
import importlib.util as u, shutil
def chk(mod, hint):
    print(("  \033[32m✓\033[0m " if u.find_spec(mod) else "  \033[33m·\033[0m ") + f"{mod}" + ("" if u.find_spec(mod) else f" 未装（{hint}）"))
chk("faster_whisper", "词级对齐，pip install faster-whisper")
chk("edge_tts", "在线配音，pip install edge-tts")
chk("piper", "本地配音，pip install piper-tts + 中文模型")
PY

say "4/4 渲染链路自检"
"$PY" - <<'PY'
import sys, os
from pathlib import Path
try:
    from playwright.sync_api import sync_playwright
except Exception as e:
    sys.exit(f"  ✗ playwright 导入失败：{e}")
cands = [os.environ.get("CINE_CHROME",""),
         "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
         "/usr/bin/google-chrome", "/usr/bin/chromium"]
chrome = next((c for c in cands if c and Path(c).exists()), None)
for kw in ({"channel":"chrome"}, {"executable_path": chrome} if chrome else {}):
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True, args=["--no-sandbox"], **kw)
            pg = b.new_page(viewport={"width":1280,"height":720})
            pg.set_content('<h1 id="t" style="font-family:sans-serif">CINE OK</h1>')
            assert pg.inner_text("#t") == "CINE OK"
            b.close()
        print("  \033[32m✓\033[0m 浏览器无头渲染正常")
        break
    except Exception as e:
        last = e
else:
    sys.exit(f"  ✗ 无法启动浏览器：{last}")
PY

echo
say "装好了。下一步："
cat <<'EOF'
  source .venv/bin/activate
  python3 tools/new_film.py 01 --template F --title "你的选题"
  然后照 SKILL.md 的六道工序走。
EOF
