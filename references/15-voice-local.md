# 15 · 本地配音完全指南

没有云端 TTS 密钥，配音这一环靠本机。`tools/tts_local.py` 一个脚本把「合成 → 对齐 → 拼接 → 出时间轴」全干了。

## 后端怎么选

| 后端 | 音质 | 联网 | 跨平台 | 适用 |
|---|---|---|---|---|
| `say` | 一般，清楚 | 否 | 仅 macOS | 先跑通链路、内部审片 |
| `piper` | 较好，略机械 | 否 | 是 | 要发布但不想依赖网络 |
| `edge-tts` | 最好，接近真人 | 是 | 是 | 正式发布，接受联网 |
| `cmd` | 看你接什么 | — | — | 已有一套自己的 TTS |

自动选择顺序是 **piper → say → edge-tts**（本地优先）。想指定就显式传：

```bash
python3 tools/tts_local.py <期目录> --backend edge --voice zh-CN-XiaoxiaoNeural
python3 tools/tts_local.py <期目录> --backend say  --voice Tingting --rate 190
python3 tools/tts_local.py <期目录> --list-backends        # 看本机有什么
```

`edge-tts` 常用中文音色：`zh-CN-XiaoxiaoNeural`（女，默认）、`zh-CN-YunxiNeural`（男，年轻）、
`zh-CN-YunjianNeural`（男，浑厚）、`zh-CN-XiaoyiNeural`（女，活泼）。

### 接自己的 TTS

```bash
python3 tools/tts_local.py <期目录> --backend cmd \
  --cmd 'my-tts --text {text} --out {out} --speaker 3'
```

`{text}` 会被替换成该拍文本（单引号已转义），`{out}` 是临时文件路径。命令只要产出一个音频文件
（wav/mp3/m4a 都行，脚本会用 ffmpeg 统一转成 48 kHz 单声道）。

## 语速与停顿

- `--rate 180`：每分钟 180 字左右。知识片一般 175–200；讲复杂概念降到 160。
- `--gap 0.18`：拍与拍之间的停顿。0.15 偏紧，0.25 偏舒展。**别用 0.8**，会让整片拖沓。
- `--lead 0.12`：首拍前的静音，给冷开场留气口。

前 5 秒决定留人率，所以第一拍宁可慢一点、把钩子说清楚。

## 逐字对齐怎么工作的

配音完要出 `build/timings.json`，里面每个字符一个绝对时间。字幕高亮、`[[cue]]` 触发的画面动作，
全靠这张表。

**词级对齐**（装了 faster-whisper）：逐拍把合成音频丢给 whisper，拿到词级时间戳，再把每个词的
时长摊到它的字符上，词间空隙线性插值。这样字幕跟着实际发音走——说到「一」的时候，画面上的
「一」正好亮起来。

**比例对齐**（没装 whisper）：按字数均分。50 字的拍就切成 50 段。能用，但遇到数字、英文、
标点处会明显不准。

三种情况会自动退回比例，并在日志里说明：

1. 没有 whisper
2. 转写结果和原文对不上（字幕文字与旁白文本匹配不上）
3. 对齐结果有异常长的停顿（单字间隔 > 1.5 秒且远超中位数）—— 这通常是模型漏字，
   让字幕卡在某一帧不动比节奏钝一点更糟

想更准：`--align-model small`（默认）或 `medium`。tiny 只建议试跑，中文漏字多。

> 有个坑已经踩过并修好：faster-whisper 收到 ndarray 时**假定采样率是 16 kHz**，不重采样。
> 直接喂 48 kHz 波形，时间戳会整体缩成 1/3，逐字全乱但不会报错。`tts_local.py` 里做了整数抽取。

## 发音纠正

`narration.json` 的 `lexicon` 字段在送进 TTS 前替换文本，只影响发音，不影响字幕：

```json
"lexicon": { "AI": "A I", "GPU": "G P U", "1.5": "一点五" }
```

必须处理的几类：

- 全大写英文缩写：`AI` / `GPU` / `API` 常被整体念成一个怪音，拆成单个字母。
- 版本号：`3.0` 会被念成「三点零」还是「三」看引擎，写成「三点零」最稳。
- 中英混排：`iPhone` 这种词用中文音色常念错，写「爱疯」或直接用英文音色。
- 罗马数字型缩写：`CLI`、`MD`、`CC` 全部由 I/V/X/L/C/D/M 组成，会被念成数字。

## 试听

```bash
python3 tools/tts_local.py <期目录> --probe
```

只合第一拍，输出 `build/probe.wav`。**每次换音色或语速都先听这一条**——
等 20 拍全合完再发现音色不对，白等十分钟。

## 常见故障

| 现象 | 原因 | 处理 |
|---|---|---|
| 某拍只有 0.02 秒 | `say -v Eddy` 这类同名音色被解析到英文发音，中文文本被丢弃 | 用 `Tingting`；脚本已把 Tingting 排第一，且对 <0.15s 的音频直接报错 |
| Piper 报找不到模型 | 模型没放到 `~/.local/share/piper/` | 下 `zh_CN-huayan-medium.onnx` 和 `.onnx.json` 放进去 |
| edge-tts 超时 | 网络不通或被限流 | 改 `--backend say` 或 piper；脚本有重试但不是万能的 |
| 字幕整体慢半拍 | 对齐用了比例，而旁白里有大段数字/英文 | 装 faster-whisper，补 lexicon |
| 时间轴里某拍 chars 长度对不上 | 转写把 `[[cue]]` 之后的内容也算了 | 检查 `narration.json` 里 cue 标记是否写成了全角括号或中文 |
