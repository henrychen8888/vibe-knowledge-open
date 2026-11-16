#!/usr/bin/env python3
"""零 API 配音 + 逐字时间轴。

替代上游的 tts_mimo.py（小米 MiMo，需密钥）。三种后端任选，默认自动探测：

  say       macOS 系统语音。零安装、零密钥、断网可用，音质一般但清楚，适合先跑通链路。
  piper     Piper TTS，本地 ONNX 推理，开源（MIT）。跨平台，音色比系统语音自然。
            装法：pip install piper-tts，再下中文模型 zh_CN-huayan-medium。
  edge-tts  Edge 在线语音，免费、音色最好，但要联网且是微软未公开接口，稳定性不保证。
  cmd       自带命令模板（{text} {out} 占位），接任何你自己的 TTS。

逐字对齐也一样分两级：
  有 faster-whisper 或 whisper-cli  → 词级真实对齐，字幕跟着实际发音走
  都没有                            → 按字数比例分配，够用但节奏略钝

用法
  python3 tts_local.py <期目录>                      # 自动选后端 + 自动对齐
  python3 tts_local.py <期目录> --backend piper --voice zh_CN-huayan-medium
  python3 tts_local.py <期目录> --probe              # 只合第一拍，先听音色
  python3 tts_local.py <期目录> --list-backends      # 看本机能用哪个
  python3 tts_local.py <期目录> --rate 190 --gap 0.2 --lead 0.12

输出（与上游 voice_post.py 同构，引擎直接吃）
  build/narration.wav   全片旁白，48 kHz 立体声
  build/timings.json    {total, beats:{id:{text,start,end,chars[],cues{}}}}
"""
from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

SR = 48000
CUE_RE = re.compile(r"\[\[(\w+)\]\]")


# ────────────────────────── 通用工具 ──────────────────────────
def opt(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def have(cmd) -> bool:
    return shutil.which(cmd) is not None


def strip_cues(s: str) -> str:
    return CUE_RE.sub("", s)


def to_mono48(src: Path) -> np.ndarray:
    """任何音频 → 48 kHz 单声道 float32。统一用 ffmpeg，省得各后端格式不一致。"""
    b = subprocess.run(["ffmpeg", "-v", "error", "-i", str(src), "-ac", "1", "-ar", str(SR),
                        "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(b, np.float32).copy()


def trim(x: np.ndarray, thresh=0.006, keep_head=0.02, keep_tail=0.06) -> np.ndarray:
    """切掉首尾静音，只留一点点余量，拍间停顿统一由 gap 控制。"""
    idx = np.nonzero(np.abs(x) > thresh)[0]
    if len(idx) == 0:
        return x
    a = max(0, idx[0] - int(keep_head * SR))
    b = min(len(x), idx[-1] + int(keep_tail * SR))
    return x[a:b]


def write_wav(path: Path, x: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    st = np.repeat((np.clip(x, -1, 1) * 32767).astype(np.int16)[:, None], 2, axis=1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(st.tobytes())


def apply_lexicon(text: str, lexicon: dict) -> str:
    """按 lexicon 改写送进 TTS 的文本（如 AI → A I，避免念成「埃」）。"""
    if not lexicon:
        return text
    for k in sorted(lexicon, key=len, reverse=True):
        text = re.sub(rf"(?<![A-Za-z0-9]){re.escape(k)}(?![A-Za-z0-9])", str(lexicon[k]), text)
    return text


# ────────────────────────── 后端 ──────────────────────────
def say_voices() -> list[str]:
    """可用中文音色。Tingting 排第一：系统自带、名字唯一，最稳。

    坑：Eddy / Flo / Grandma 这些在 say -v ? 里标着 zh_CN，但同名英文音色也在，
    `say -v Eddy 中文` 会解析到英文音色，安静地合成一段 0.02 秒的空音频。所以默认不选它们。
    """
    if not have("say"):
        return []
    out = subprocess.run(["say", "-v", "?"], capture_output=True, text=True).stdout
    names, seen = [], set()
    for ln in out.splitlines():
        if "zh_CN" in ln or "zh_TW" in ln:
            n = ln.split()[0]
            if n not in seen:
                seen.add(n)
                names.append(n)
    names.sort(key=lambda n: (n != "Tingting", n))
    return names


def synth_say(text: str, out: Path, voice: str, rate: int) -> None:
    subprocess.run(["say", "-v", voice or "Tingting", "-r", str(rate),
                    "--data-format=LEI16@48000", "-o", str(out), text], check=True)


def piper_model_path(voice: str) -> Path | None:
    cands = [Path(voice).expanduser()]
    for base in (Path.home() / ".local/share/piper", Path.home() / ".cache/piper",
                 Path(__file__).resolve().parent.parent / "assets/voices"):
        cands.append(base / f"{voice}.onnx")
        cands.append(base / voice)
    for c in cands:
        if c.suffix == ".onnx" and c.exists():
            return c
    return None


def synth_piper(text: str, out: Path, voice: str, rate: int) -> None:
    model = piper_model_path(voice or "zh_CN-huayan-medium")
    if not model:
        raise FileNotFoundError(
            f"找不到 Piper 模型「{voice or 'zh_CN-huayan-medium'}」。下载 zh_CN-huayan-medium 的 "
            f".onnx 与 .onnx.json，放到 ~/.local/share/piper/ 下，再用 --voice 指定名字。")
    exe = shutil.which("piper") or sys.executable.replace("python", "piper")
    tmp = out.with_suffix(".piper.wav")
    subprocess.run([exe, "-m", str(model), "-f", str(tmp)], input=text.encode(), check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    x = to_mono48(tmp)
    tmp.unlink(missing_ok=True)
    # Piper 语速靠 length_scale 调，没有 --rate；用 ffmpeg atempo 近似
    speed = rate / 180.0
    if abs(speed - 1.0) > 0.02:
        w = out.with_suffix(".spd.wav")
        write_wav(w, x)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(w), "-filter:a", f"atempo={speed:.3f}",
                        "-ar", str(SR), str(out)], check=True)
        w.unlink(missing_ok=True)
    else:
        write_wav(out, x)


def synth_edge(text: str, out: Path, voice: str, rate: int) -> None:
    mp3 = out.with_suffix(".mp3")
    speed = int(round((rate / 180.0 - 1) * 100))
    cmd = ["edge-tts", "--voice", voice or "zh-CN-XiaoxiaoNeural", "--text", text, "--write-media", str(mp3)]
    if speed:
        cmd += ["--rate", f"{speed:+d}%"]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    write_wav(out, to_mono48(mp3))
    mp3.unlink(missing_ok=True)


def synth_cmd(text: str, out: Path, voice: str, rate: int) -> None:
    tpl = opt("--cmd")
    if not tpl:
        raise SystemExit("--backend cmd 需要配合 --cmd '你的命令 {text} {out}'")
    tmp = out.with_suffix(".raw")
    cmd = tpl.replace("{text}", text.replace("'", "'\\''")).replace("{out}", str(tmp))
    subprocess.run(cmd, shell=True, check=True)
    write_wav(out, to_mono48(tmp if tmp.exists() else out))
    tmp.unlink(missing_ok=True)


SYNTH = {"say": synth_say, "piper": synth_piper, "edge": synth_edge, "edge-tts": synth_edge, "cmd": synth_cmd}


def pick_backend(explicit: str | None) -> tuple[str, str]:
    """返回 (后端, 默认音色)。显式指定就校验，否则按可用性从好到差挑。"""
    if explicit:
        b = "edge" if explicit == "edge-tts" else explicit
        if b not in SYNTH:
            raise SystemExit(f"未知后端 {explicit}，可选：{', '.join(SYNTH)}")
        if b == "say" and not have("say"):
            raise SystemExit("--backend say 只在 macOS 可用")
        if b == "piper" and not piper_model_path(opt("--voice", "")):
            print("⚠ Piper 已选但模型没找到，装好模型后重试；本次改用比例对齐、仍会尝试合成")
        return b, opt("--voice", "")
    # 默认优先本地（断网也能跑），联网后端要用户显式选或环境变量放行
    if have("piper") and piper_model_path(opt("--voice", "zh_CN-huayan-medium")):
        return "piper", opt("--voice", "zh_CN-huayan-medium")
    if have("say") and platform.system() == "Darwin":
        vs = say_voices()
        return "say", opt("--voice", vs[0] if vs else "Tingting")
    if have("edge-tts") and os.environ.get("VK_ALLOW_NETWORK_TTS", "1") != "0":
        return "edge", opt("--voice", "zh-CN-XiaoxiaoNeural")
    raise SystemExit("没有可用的 TTS 后端。macOS 自带 say；其他平台装 piper-tts 或 edge-tts。")


# ────────────────────────── 对齐 ──────────────────────────
class Aligner:
    """词级对齐器。装得上 faster-whisper / whisper-cli 就用真的，装不上返回 None 走比例。"""

    def __init__(self, mode: str = "auto", model_size: str = "small"):
        self.kind = None
        self.model = None
        self.err = None
        if mode == "off" or os.environ.get("VK_ALIGN", "auto") == "off":
            return
        try:
            from faster_whisper import WhisperModel
        except Exception:
            if have("whisper-cli") or have("whisper"):
                self.kind = "whisper-cli"
            else:
                self.err = "未安装 faster-whisper（pip install faster-whisper）"
            return
        if mode == "probe":                       # 只探测可用性，不加载模型（模型可能几百 MB）
            self.kind = "faster-whisper"
            return
        try:
            self.model = WhisperModel(model_size, device="auto", compute_type="int8")
            self.kind = "faster-whisper"
        except Exception as e:
            # 首次使用要下模型，网络不通就会走到这里 —— 别静默降级，说清楚
            self.err = (f"模型 {model_size} 加载失败（首次需下载，约 150MB–1.5GB）："
                        f"{type(e).__name__}: {str(e)[:110]}")
            if have("whisper-cli") or have("whisper"):
                self.kind = "whisper-cli"

    def words(self, x: np.ndarray, tmpdir: Path) -> list[tuple[str, float, float]]:
        if self.kind == "faster-whisper":
            # 关键：faster-whisper 拿到 ndarray 时**假定采样率是 16 kHz**，不重采样。
            # 直接喂 48 kHz 的波形，时间戳会整体缩成 1/3，逐字对齐就全乱了。
            y = x[:: SR // 16000] if SR != 16000 else x
            segs, _ = self.model.transcribe(y.astype(np.float32), language="zh",
                                            word_timestamps=True, vad_filter=False, beam_size=1)
            return [(w.word.strip(), float(w.start), float(w.end))
                    for s in segs for w in (s.words or []) if w.word.strip()]
        if self.kind == "whisper-cli":
            wav = tmpdir / "_align.wav"
            write_wav(wav, x)
            exe = shutil.which("whisper-cli") or shutil.which("whisper")
            r = subprocess.run([exe, "-m", os.environ.get("WHISPER_MODEL", ""), "-l", "zh",
                                "-oj", "-of", str(wav.with_suffix("")), str(wav)],
                               capture_output=True, text=True)
            js = json.loads(Path(str(wav.with_suffix("")) + ".json").read_text(encoding="utf-8"))
            out = []
            for seg in js.get("transcription", []):
                off = float(seg.get("offsets", {}).get("from", 0)) / 1000
                to = float(seg.get("offsets", {}).get("to", 0)) / 1000
                t = seg.get("text", "").strip()
                if t:
                    out.append((t, off, to))
            return out
        return []


def char_times_from_words(text: str, words: list[tuple[str, float, float]]) -> list[float] | None:
    """把词级时间戳摊到每个字符上：词内线性插值，词间空隙按相邻词端点补。"""
    if not words:
        return None
    key_re = re.compile(r"[^\w\u4e00-\u9fff]+")
    spans, cur = [], 0
    for w, t0, t1 in words:
        k = key_re.sub("", w)
        if not k:
            continue
        p = text.find(k, cur)
        if p < 0:
            p = text.find(k[0], cur)
            if p < 0:
                continue
            k = k[0]
        spans.append((p, p + len(k), t0, t1))
        cur = p + len(k)
    if not spans:
        return None
    t = [float("nan")] * len(text)
    for p, q, t0, t1 in spans:
        n = q - p
        for i in range(n):
            t[p + i] = t0 + (t1 - t0) * (i / (n - 1) if n > 1 else 0.5)
    # 没被覆盖的字符（标点、数字）用左右邻居线性插值
    known = [i for i, v in enumerate(t) if v == v]
    if not known:
        return None
    for i in range(len(t)):
        if t[i] != t[i]:
            lo = max([j for j in known if j < i], default=None)
            hi = min([j for j in known if j > i], default=None)
            if lo is not None and hi is not None:
                t[i] = t[lo] + (t[hi] - t[lo]) * (i - lo) / (hi - lo)
            elif lo is not None:
                t[i] = t[lo]
            else:
                t[i] = t[hi]
    return t


def normalize_times(t: list[float], dur: float, min_gap: float = 0.012) -> list[float]:
    """把字符时间修成「严格递增且落在 [0, dur] 内」。

    whisper 少数情况下会把几个字压到同一时间戳（漏字、快读），表现为字幕一次跳好几个字。
    这里强制最小间隔；超出音频长度就整体线性压缩，不影响节奏形状。
    """
    n = len(t)
    if n < 2:
        return t
    out = [max(0.0, min(v, dur)) for v in t]
    for i in range(1, n):
        if out[i] < out[i - 1] + min_gap:
            out[i] = out[i - 1] + min_gap
    if out[-1] > dur > out[0]:
        k = (dur - out[0]) / (out[-1] - out[0])
        out = [out[0] + (v - out[0]) * k for v in out]
    return out


def looks_broken(ct: list[float], dur: float) -> bool:
    """对齐结果看着不对就认栽，回退比例。宁可字幕节奏钝一点，也不要卡在某一帧不动。

    典型故障：模型（尤其 tiny）把某个词的时间戳甩到很后面，字幕突然 6 秒不跳。
    """
    diffs = [ct[i + 1] - ct[i] for i in range(len(ct) - 1)]
    if not diffs:
        return False
    med = sorted(diffs)[len(diffs) // 2]
    return any(d > max(1.5, med * 6) for d in diffs)


# ────────────────────────── 主流程 ──────────────────────────
def main() -> None:
    if "--list-backends" in sys.argv:
        print(f"say      {'✓ 可用' if have('say') and platform.system() == 'Darwin' else '✗ 不可用'}"
              f"{'（中文音色：' + ', '.join(say_voices()[:6]) + '）' if say_voices() else ''}")
        print(f"piper    {'✓ ' + str(piper_model_path(opt('--voice', 'zh_CN-huayan-medium'))) if piper_model_path(opt('--voice', 'zh_CN-huayan-medium')) else '✗ 未装模型'}")
        print(f"edge-tts {'✓ 可用（需联网）' if have('edge-tts') else '✗ 未安装：pip install edge-tts'}")
        a = Aligner(mode="probe")
        if a.kind:
            print(f"对齐     ✓ {a.kind}（首次跑会下模型；用 --align-model 选大小）")
        else:
            print(f"对齐     ✗ {a.err or '无 whisper'} —— 退回字数比例分配")
        return

    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    L = Path(sys.argv[1]).resolve()
    narr_p = L / "narration.json"
    if not narr_p.exists():
        raise SystemExit(f"没找到 {narr_p}")
    narr = json.loads(narr_p.read_text(encoding="utf-8"))
    beats = narr.get("beats", [])
    if not beats:
        raise SystemExit("narration.json 里没有 beats")

    rate = int(opt("--rate", "180"))
    gap = float(opt("--gap", "0.18"))
    lead = float(opt("--lead", "0.12"))
    backend, voice = pick_backend(opt("--backend"))
    lexicon = narr.get("lexicon") or {}
    B = L / "build"
    B.mkdir(parents=True, exist_ok=True)

    print(f"后端 {backend}" + (f" · 音色 {voice}" if voice else "") + f" · 语速 {rate} · 拍间隙 {gap}s")
    aligner = Aligner(opt("--align", "auto"), opt("--align-model", "small"))
    if aligner.kind:
        print(f"对齐 词级 · {aligner.kind}")
    else:
        print(f"对齐 按字数比例 —— {aligner.err or '无 whisper'}")
        print("     装 faster-whisper 可升级为词级对齐，字幕会更跟得上发音")

    if "--probe" in sys.argv:
        b = beats[0]
        txt = strip_cues(b["narration"])
        with tempfile.TemporaryDirectory() as td:
            raw = Path(td) / "probe.wav"
            SYNTH[backend](apply_lexicon(txt, lexicon), raw, voice, rate)
            x = trim(to_mono48(raw))
        out = B / "probe.wav"
        write_wav(out, x)
        print(f"→ {out}  {len(x)/SR:.2f}s / {len(txt)} 字  （听一下，满意就正式跑）")
        return

    cursor, out_beats, pieces, tmpdir = lead, {}, [], Path(tempfile.mkdtemp(prefix="vktts_"))
    try:
        for i, b in enumerate(beats, 1):
            raw = b["narration"]
            txt = strip_cues(raw).strip()
            speak = apply_lexicon(txt, lexicon)
            wav = tmpdir / f"{b['id']}.wav"
            SYNTH[backend](speak, wav, voice, rate)
            x = trim(to_mono48(wav))
            dur = len(x) / SR
            if dur < 0.15:
                raise SystemExit(
                    f"{b['id']} 只合成出 {dur:.2f}s 音频 —— 后端 {backend} 多半没念出来。\n"
                    f"  文本：{txt[:40]}…\n"
                    f"  若在 macOS：换 --voice Tingting（其他音色可能解析到英文同名音色，合成空音频）")

            ct = None
            if aligner.kind:
                try:
                    ct = char_times_from_words(txt, aligner.words(x, tmpdir))
                except Exception as e:
                    print(f"  {b['id']} 对齐失败（{type(e).__name__}），本拍退回比例")
                if ct and looks_broken(ct, dur):
                    print(f"  {b['id']} 对齐结果异常（有超长停顿），本拍退回比例。"
                          f"想更准就换大模型：--align-model small")
                    ct = None
            if not ct or len(ct) != len(txt):
                n = max(len(txt), 1)
                ct = [i / n * dur for i in range(n)]
            else:
                ct = normalize_times(ct, dur)

            cues = {}
            for m in CUE_RE.finditer(raw):
                pos = len(strip_cues(raw[: m.start()]))
                cues[m.group(1)] = round(cursor + (ct[min(pos, len(ct) - 1)] if ct else 0), 3)

            out_beats[b["id"]] = {
                "text": txt,
                "start": round(cursor, 3),
                "end": round(cursor + dur, 3),
                "chars": [round(cursor + c, 3) for c in ct],
                "cues": cues,
            }
            pieces.append(x)
            pieces.append(np.zeros(int(gap * SR), np.float32))
            print(f"  {b['id']:5s} {dur:6.2f}s  {len(txt):3d} 字  cues={list(cues)}")
            cursor += dur + gap
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    total = round(cursor - gap, 3)
    y = np.concatenate(pieces[:-1]) if pieces else np.zeros(1, np.float32)
    y = np.pad(y, (0, max(0, int(round(total * SR)) - len(y))))
    write_wav(B / "narration.wav", y)
    (B / "timings.json").write_text(
        json.dumps({"total": total, "beats": out_beats}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"→ {B/'narration.wav'}  {total:.2f}s / {len(out_beats)} 拍")
    print(f"→ {B/'timings.json'}")


if __name__ == "__main__":
    main()
