#!/usr/bin/env python3
"""强制 BGM + 按人声校准音量（引擎侧钩子，由 finish.py 混音时调用）。

与原版 bgm_force.py 的区别：曲源不再是一份随仓库分发的授权音频，而是 **代码现场合成**
（同目录 make_bgm.py）。所以这份 skill 可以整包公开分发，你的成片也能自由使用这条 BGM。

规则
  0. 唯一例外：用户明确要求换曲 → film.js 的 music 条目写 bgm: true + user_request: "用户原话"，
     这条当 BGM，内置曲让位（音量照样校准）。
  1. prepare()：片子里没放 BGM → 按片长从合成源裁一份 build/bgm_auto.wav 补上；
     其他 ≥20 秒的整段配乐一律停用，短音效、镜头原声保留。
  2. calibrate()：不管 film.js 写了多大 gain，BGM 整体音量按人声重新校准——
     说话时 BGM 比人声低 VOICE_GAP dB；没说话处照引擎原本的压低逻辑抬起（约 +7 dB）。
  3. 写 build/bgm.json（有没有 BGM、校准前后的人声比），qa.py 读它，缺了就报警。
"""
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

CINE = Path(__file__).resolve().parent.parent          # <系列>/cine/
BGM_SRC = CINE / "audio/bgm-source.wav"
MAKE = Path(__file__).resolve().parent / "make_bgm.py"
SR = 48000
VOICE_GAP = 10.0        # 说话时 BGM 比人声低多少 dB。8 以下开始抢人声，12 以上偏轻
LONG = 20.0             # 超过这个时长的非 BGM 音乐条目视为整段配乐，停用


def is_bgm(m):
    return Path(str(m.get("src", ""))).name in ("bgm.wav", "bgm_auto.wav")


def is_user_bgm(m):
    # 唯一的更换口子：film.js 里这样写——
    # music.push({ src: P("audio/xxx.wav"), …, bgm: true, user_request: "用户原话" })
    return bool(m.get("bgm")) and bool(str(m.get("user_request", "")).strip())


def _read(p):
    with wave.open(str(p), "rb") as w:
        ch, n = w.getnchannels(), w.getnframes()
        x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32).reshape(-1, ch) / 32768.0
    return x if ch == 2 else np.repeat(x, 2, axis=1)


def _write(p, x):
    with wave.open(str(p), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def ensure_source(py=sys.executable):
    """合成源不存在就现场生成一条 150 秒的（够 2.5 分钟片，更长的片子自动循环拼接）。"""
    if not BGM_SRC.exists():
        BGM_SRC.parent.mkdir(parents=True, exist_ok=True)
        print("  BGM：合成源不存在，现场生成 150 秒（无采样、可自由分发）")
        subprocess.run([py, str(MAKE), "--out", str(BGM_SRC), "--seconds", "150"],
                       check=True, stdout=subprocess.DEVNULL)
    return BGM_SRC


def fit(total, out, py=sys.executable):
    """按片长裁 BGM：裁剪或循环拼接，首尾做淡入淡出。"""
    src = _read(ensure_source(py))
    need = int(round(total * SR))
    have = len(src)
    if have >= need:
        y = src[:need].copy()            # 从曲子开头取：qa.py 要拿成片开头和源开头做相关校验
    else:
        reps = int(np.ceil(need / have))
        y = np.tile(src, (reps, 1))[:need]
    fi, fo = min(int(0.3 * SR), need // 8), min(int(1.8 * SR), need // 4)
    if fi > 0:
        y[:fi] *= np.linspace(0, 1, fi)[:, None]
    if fo > 0:
        y[-fo:] *= np.linspace(1, 0, fo)[:, None]
    _write(Path(out), y)
    return Path(out)


def _exists(src, root) -> bool:
    """音乐条目的 src 支持绝对路径和「相对系列目录」两种写法。"""
    p = Path(str(src))
    if p.is_absolute():
        return p.exists()
    return (Path(root) / p).exists() if root else p.exists()


def prepare(info, total, B, root=None, py=sys.executable):
    music = info.get("music", [])
    keep, dropped, missing = [], [], []
    user = [m for m in music if is_user_bgm(m)]
    for m in music:
        if user and is_bgm(m):            # 用户要求换曲：内置曲让位
            dropped.append(Path(str(m.get("src"))).name)
            continue
        if is_user_bgm(m):
            if not _exists(m.get("src"), root):
                missing.append(Path(str(m.get("src"))).name)
                continue
            m["_bgm"] = True
            keep.append(m)
        elif m.get("bgm") and not is_user_bgm(m):
            print("  BGM 强制：有条目标了 bgm: true 但没写 user_request（用户原话），不认，改用内置曲")
            dropped.append(Path(str(m.get("src"))).name)
        elif is_bgm(m):
            # film.js 里常留着一条「bgm.wav」占位，但文件可能从来没生成过 —— 不校验就会让 ffmpeg 报错
            if not _exists(m.get("src"), root):
                missing.append(Path(str(m.get("src"))).name)
                continue
            m["_bgm"] = True
            keep.append(m)
        elif float(m.get("dur", 0)) >= LONG and not str(m.get("src", "")).startswith("earshot:"):
            dropped.append(Path(str(m.get("src"))).name)
        else:
            keep.append(m)
    auto = False
    if not any(m.get("_bgm") for m in keep):
        out = Path(B) / "bgm_auto.wav"
        fit(total, out, py)
        keep.insert(0, {"src": str(out), "from": 0, "at": 0, "dur": total,
                        "gain": 0, "fade_in": 0.3, "fade_out": 1.8, "_bgm": True})
        auto = True
    if user:
        print(f"  BGM：用户要求更换 → {Path(str(user[0].get('src'))).name}（{user[0].get('user_request')}）")
    if dropped:
        print(f"  BGM 强制：停用整段配乐 {', '.join(dropped)}（" + ("用户要求换曲" if user else "本 skill 统一用内置合成曲") + "）")
    if auto:
        print(f"  BGM 强制：片子里没放 BGM，已按片长 {total:.1f}s 自动补上")
    if missing:
        print(f"  BGM：{', '.join(missing)} 文件不存在，已忽略并改用内置合成曲")
    info["music"] = keep
    return {"auto": auto, "dropped": dropped, "missing": missing,
            "user_bgm": (Path(str(user[0]["src"])).name, user[0]["user_request"]) if user else None}


def calibrate(bgmt, narr, speech, B, state):
    """bgmt：已乘过 gain_curve 形状与压低包络的 BGM 轨（n×2）；narr：人声轨；speech：说话采样掩码。"""
    rep = {"has_bgm": bool(np.any(bgmt)), "voice_gap_target_db": VOICE_GAP, **state}
    if rep["has_bgm"] and speech.any():
        rv = np.sqrt(np.mean(narr[speech] ** 2))
        rb = np.sqrt(np.mean(bgmt[speech] ** 2))
        before = 20 * np.log10(rv / max(rb, 1e-9))
        g = 10 ** ((before - VOICE_GAP) / 20)
        bgmt = bgmt * g
        quiet = ~speech
        rq = np.sqrt(np.mean(bgmt[quiet] ** 2)) if quiet.any() else 0
        rep.update(voice_gap_before_db=round(float(before), 1),
                   gain_applied_db=round(float(20 * np.log10(g)), 1),
                   voice_gap_db=VOICE_GAP,
                   gap_in_pauses_db=round(float(20 * np.log10(rv / max(rq, 1e-9))), 1) if quiet.any() else None)
        print(f"  BGM 校准：说话时人声比 BGM 高 {before:.1f} → {VOICE_GAP:.1f} dB"
              f"（BGM {20 * np.log10(g):+.1f} dB）；没说话处人声比 BGM 高 {rep['gap_in_pauses_db']} dB")
    Path(B, "bgm.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    return bgmt
