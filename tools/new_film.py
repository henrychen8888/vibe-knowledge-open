#!/usr/bin/env python3
"""新建一期知识短片。

与上游 new_film.py 的差别：引擎是**现成的一份**（本 skill 自带，已经带好全部钩子），
所以这里不再往第三方 skill 里拷文件、也不再靠字符串替换打补丁 —— 拷贝即用，不会因为
上游引擎改了一行就静默失效。

用法
  python3 new_film.py <期号> --template A --title "本福特定律"
  python3 new_film.py 01 --template F --title "为什么1最多" --ws ~/videos --series vk

建的目录
  <工作区>/examples/<系列>/
    cine/                引擎（index.html、engine/*.js、vendor/、fonts/、tools/）
    cine/audio/          bgm-source.wav 合成曲（首次混音时自动生成）
    lessons/<期号>/      narration.json · film.js · facts.md · assets.json · assets/{img,clips,audio} · build/ · stills/
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
ENGINE = SKILL / "engine"
TPL = SKILL / "templates"


def build_series(sd: Path, title: str) -> None:
    """建系列骨架：把自带引擎整份拷过去。已有引擎就跳过拷贝，但依赖工具每次同步。"""
    if (sd / "cine/engine/core.js").exists():
        print(f"✓ 引擎已就位：{sd/'cine'}")
    else:
        shutil.copytree(ENGINE, sd / "cine", dirs_exist_ok=True)
        (sd / "cine/audio").mkdir(parents=True, exist_ok=True)
        (sd / "tools").mkdir(parents=True, exist_ok=True)
        (sd / "cine/deliver.env").write_text(
            '# deliver.sh 的去向（zsh 语法）\n'
            f'D="$HOME/Desktop/{title}_视频"\n'
            "WEB=publish/course\n"
            'STRIP=""\n', encoding="utf-8")
        print(f"✓ 引擎就位：{sd/'cine'}（字体、vendor、tools 齐全）")
    # bgm.py 混音时按需调用同目录的 make_bgm.py 合成配乐；引擎整份拷贝时已经带上，这里兜一次底
    if not (sd / "cine/tools/make_bgm.py").exists():
        shutil.copy(ENGINE / "tools/make_bgm.py", sd / "cine/tools/make_bgm.py")


def main() -> None:
    ap = argparse.ArgumentParser(description="新建一期知识短片")
    ap.add_argument("id", help="期号，如 01")
    ap.add_argument("--template", default="A", choices=list("ABCDEF"),
                    help="脚本母版：A 猜谜 / B 两难 / C 痛点 / D 主线 / E 闯关 / F 六面轮转")
    ap.add_argument("--title", required=True)
    ap.add_argument("--ws", default="./vibe-workspace", help="工作区目录（默认当前目录下）")
    ap.add_argument("--series", default="vk", help="系列名（同一系列共用一份引擎）")
    a = ap.parse_args()

    ws = Path(a.ws).expanduser().resolve()
    sd = ws / "examples" / a.series
    build_series(sd, "Vibe知识大赏")

    L = sd / "lessons" / a.id
    if L.exists():
        sys.exit(f"这一期已存在：{L}\n换个期号，或先删掉它。")
    for d in ("assets/img", "assets/clips", "assets/audio", "build", "stills"):
        (L / d).mkdir(parents=True)

    narr_p = TPL / f"narration/{a.template}.json"
    narr = json.loads(narr_p.read_text(encoding="utf-8"))
    narr["_how"] = (f"母版 {a.template} · {a.title}。旁白由 tts_local.py 合成（本地 TTS，"
                    "不是云端克隆音色）；想换音色见 SKILL.md「配音」一节。")
    narr.setdefault("voice", {})["engine"] = "tts_local"
    (L / "narration.json").write_text(json.dumps(narr, ensure_ascii=False, indent=1), encoding="utf-8")

    film = (TPL / "film.skeleton.js").read_text(encoding="utf-8")
    for k, v in (("__TITLE__", a.title), ("__ID__", a.id), ("__TPL__", a.template)):
        film = film.replace(k, v)
    (L / "film.js").write_text(film, encoding="utf-8")
    shutil.copy(TPL / "facts.md", L / "facts.md")
    shutil.copy(TPL / "assets.json", L / "assets.json")

    print(f"✓ 新一期：{L}")
    print(f"  母版 {a.template} · {a.title} · {len(narr['beats'])} 拍骨架")
    print("\n下一步：")
    print(f"  1. 写 {L/'facts.md'}（每条事实带出处，后面 OCR 回读要对）")
    print(f"  2. 写 {L/'narration.json'}（逐拍旁白，[[cue]] 标记物体出现时刻）")
    print(f"  3. python3 {SKILL/'tools/tts_local.py'} {L} --probe   # 先试听音色")
    print(f"  4. python3 {SKILL/'tools/tts_local.py'} {L}           # 正式配音 + 时间轴")
    print(f"  5. 写 {L/'film.js'}（镜头表，全用 engine/engine/know.js 的组件）")
    print(f"  6. python3 {SKILL/'tools/render.py'} {L.parent.parent} {a.id}")


if __name__ == "__main__":
    main()
