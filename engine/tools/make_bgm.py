#!/usr/bin/env python3
"""代码合成 BGM —— 取代上游随仓库分发的授权曲库（vibe-bgm.m4a 不可再分发）。

全部用 numpy 加法合成，不含任何采样素材，因此产物可随你的成片自由使用、也可再次分发。
音色取向：温和的 ambient pad + 低音铺底 + 稀疏高频点缀，专为「说话为主」的知识短片设计——
中频留空给人声，不抢注意力 3–4 kHz 的存在感。

用法
  python3 make_bgm.py --out bgm.wav --seconds 90
  python3 make_bgm.py --out bgm.wav --seconds 90 --key Dm --bpm 68 --seed 7
  python3 make_bgm.py --presets            # 列出内置调式与情绪

参数
  --seconds  时长（默认 90，够 5 分钟片靠循环裁切）
  --key      调式：Am / Dm / Em / Cmaj / Fmaj（默认 Am）
  --bpm      速度（默认 72；60–80 偏沉思，80–100 偏轻快）
  --mood     calm / warm / tense / bright（默认 calm）
  --seed     随机种子，换一个就是另一条曲子
"""
from __future__ import annotations

import argparse
import wave
from pathlib import Path

import numpy as np

SR = 48000
NOTE = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5,
        "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}

# 每种调式给两套进行，情绪由音程与音区控制
PROG = {
    "calm":  [("i", "VI", "III", "VII"), ("i", "iv", "VI", "v")],
    "warm":  [("I", "V", "vi", "IV"), ("I", "iii", "IV", "V")],
    "tense": [("i", "bII", "i", "V"), ("i", "VI", "bVII", "V")],
    "bright": [("I", "vi", "IV", "V"), ("I", "IV", "vi", "V")],
}
DEGREE = {"I": 0, "bII": 1, "ii": 2, "bIII": 3, "III": 4, "iv": 5, "IV": 5,
          "v": 7, "V": 7, "bVI": 8, "VI": 9, "bVII": 10, "VII": 11, "vi": 9, "iii": 4}


def hz(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def tone(f: float, dur: int, amp: float, bright: float = 0.35) -> np.ndarray:
    """一个柔和的长音：基波 + 两三个衰减谐波，头尾用正弦包络，避免爆音。"""
    t = np.arange(dur) / SR
    w = (np.sin(2 * np.pi * f * t)
         + bright * 0.5 * np.sin(2 * np.pi * 2 * f * t + 0.6)
         + bright * 0.22 * np.sin(2 * np.pi * 3 * f * t + 1.2)
         + bright * 0.09 * np.sin(2 * np.pi * 4 * f * t + 2.0))
    # 轻微颤音让长音不呆板
    w *= 1 + 0.0016 * np.sin(2 * np.pi * 4.6 * t)
    atk = min(dur // 3, int(1.1 * SR))
    rel = min(dur // 3, int(1.4 * SR))
    env = np.ones(dur)
    env[:atk] = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, atk))
    env[-rel:] = 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, rel))
    return (w * env * amp).astype(np.float32)


def place(buf: np.ndarray, seg: np.ndarray, at: int) -> None:
    n = min(len(seg), len(buf) - at)
    if n > 0:
        buf[at:at + n] += seg[:n]


def comb(x: np.ndarray, delays: list[tuple[float, float]]) -> np.ndarray:
    """极简延时混响：几个不同延迟的衰减副本，左右错开做宽度。"""
    y = x.copy()
    for sec, g in delays:
        d = int(sec * SR)
        if d < len(x):
            y[d:] += x[:-d] * g
    return y


def build(seconds: float, key: str, bpm: float, mood: str, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    bar = 60.0 / bpm * 4                     # 四拍一小节

    root_pc = NOTE[key[:-1] if key.endswith("m") and len(key) > 2 else key[0]]
    minor = key.endswith("m")
    base = 48 + root_pc                      # 低一个八度铺底（C3 附近）
    if base < 40:
        base += 12

    pads = np.zeros(n, np.float32)
    bass = np.zeros(n, np.float32)
    spark = np.zeros(n, np.float32)

    prog = PROG[mood][seed % len(PROG[mood])]
    nb = int(np.ceil(seconds / bar)) + 1
    for i in range(nb):
        deg = prog[i % len(prog)]
        r = base + DEGREE.get(deg, 0)
        third = 3 if minor or deg.islower() else 4
        chord = [r, r + third, r + 7, r + 12]
        at = int(i * bar * SR)
        seglen = int(bar * SR * 1.06)        # 略微交叠，和声连接更滑
        for j, m in enumerate(chord):
            a = 0.115 if j == 0 else (0.082 if j < 3 else 0.05)
            place(pads, tone(hz(m), seglen, a), at)
        place(bass, tone(hz(chord[0] - 12), seglen, 0.15, 0.18), at)
        # 每小节一次低频脉冲，给节奏骨架但不喧宾
        if mood in ("warm", "bright"):
            plen = int(0.5 * SR)
            t = np.arange(plen) / SR
            pulse = np.sin(2 * np.pi * hz(chord[0] - 24) * t) * np.exp(-t * 7) * 0.11
            place(bass, pulse.astype(np.float32), at)
        # 稀疏高音点缀（五声音阶，避开半音）
        for _ in range(2):
            if rng.random() < 0.55:
                m = r + 24 + int(rng.choice([0, 2, 3, 5, 7, 9, 12]))
                at2 = at + int(rng.integers(0, int(bar * 0.8) + 1) * SR / 4)
                place(spark, tone(hz(m), int(1.6 * SR), 0.030 + 0.02 * rng.random(), 0.7), at2)

    # 简易低通（7 点滑动平均，截止约 6.8 kHz），把谐波毛刺磨掉；向量化实现，90 秒只要几十毫秒
    k = np.ones(7, np.float32) / 7
    for ch in (pads, spark):
        ch[:] = np.convolve(ch, k, mode="same")

    mixL = pads + bass * 0.95 + spark
    mixR = pads * 0.985 + bass * 0.95 + spark * 1.0
    # 立体声宽度：左右各加一组错开的延时
    L = comb(mixL, [(0.091, 0.20), (0.173, 0.12), (0.283, 0.07)])
    R = comb(mixR, [(0.097, 0.20), (0.181, 0.12), (0.297, 0.07)])

    # 慢速呼吸（0.055 Hz），整条曲子的动态起伏
    t = np.arange(n) / SR
    breathe = 1 + 0.10 * np.sin(2 * np.pi * 0.055 * t)
    st = np.stack([L * breathe, R * breathe], axis=1)

    # 首尾淡入淡出，循环裁切时不会鼓包
    fi, fo = int(1.2 * SR), int(3.0 * SR)
    st[:fi] *= np.linspace(0, 1, fi)[:, None]
    st[-fo:] *= np.linspace(1, 0, fo)[:, None]

    peak = float(np.max(np.abs(st))) or 1.0
    return (st / peak * 0.62).astype(np.float32)


def write_wav(path: Path, st: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    x = np.clip(st, -1, 1)
    pcm = (x * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(st.shape[1])
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def main() -> None:
    ap = argparse.ArgumentParser(description="代码合成 BGM（无采样、可自由分发）")
    ap.add_argument("--out", help="输出 wav 路径")
    ap.add_argument("--seconds", type=float, default=90.0)
    ap.add_argument("--key", default="Am")
    ap.add_argument("--bpm", type=float, default=72.0)
    ap.add_argument("--mood", default="calm", choices=list(PROG))
    ap.add_argument("--seed", type=int, default=3)
    ap.add_argument("--presets", action="store_true", help="列出可用调式与情绪后退出")
    a = ap.parse_args()

    if a.presets:
        print("调式：Am  Dm  Em  Cmaj  Fmaj（也可写 Gm / Bbm 等，解析首字母 + 可选 m）")
        print("情绪：")
        for k, v in PROG.items():
            print(f"  {k:7s} 进行 {v[0]}")
        return
    if not a.out:
        ap.error("缺 --out")

    st = build(a.seconds, a.key, a.bpm, a.mood, a.seed)
    out = Path(a.out).expanduser()
    write_wav(out, st)
    rms = 20 * np.log10(float(np.sqrt(np.mean(st ** 2))) + 1e-9)
    print(f"→ {out}  {a.seconds:.0f}s  {a.key}  {a.bpm:.0f}bpm  {a.mood}  RMS {rms:.1f} dBFS")


if __name__ == "__main__":
    main()
