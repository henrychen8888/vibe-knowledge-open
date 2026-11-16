---
name: vibe-knowledge-open
description: 「Vibe 知识大赏 · 开源版」知识短片工作室：一个知识点 → 一条 45 秒～5 分钟、有旁白、每句有出处的知识短片。画面不用 AI 生图，由模型写 film.js、浏览器逐帧渲染（1080p60），风格 100% 可复现。配音走本地 TTS（系统语音 / Piper / edge-tts），对齐走 faster-whisper，BGM 由代码合成——**全链路零 API 密钥、零积分**。从 15 条爆款反推的 6 种脚本母版（猜谜概念片、两难选择片、痛点原理片、一条主线片、闯关片、六面轮转片）→ 带出处的事实清单 → 旁白稿 → 三维确认 → 代码成片 → OCR 回读质检 → 发布包（标题、话题、封面、简介）。触发：做一期知识大赏 / 知识科普短片 / 把这个概念做成知识视频 / 用代码做视频 / 不花钱做知识视频。不用于：系列课、财经口播、品牌宣传片、数字人出镜。
---

# Vibe 知识大赏 · 开源版

一个知识点，做成一条能发的知识短片。**不调任何付费 API**：配音、对齐、配乐、画面全部在本机完成。

核心思路是反过来的——**不生成画面，而是算画面**。模型写一份 `film.js` 镜头表，浏览器按时间 `seek(t)` 逐帧渲染。
同一秒渲两次像素级一致，所以能任意跳帧截图、只重渲改动的几秒、失败断点续渲。风格是代码，不是抽卡。

---

## 和原版的关系

本 skill 衍生自 [andyhuo520/vibe-knowledge](https://github.com/andyhuo520/vibe-knowledge)（MIT），
把其中所有需要外部服务或不可再分发的环节换成了开源实现：

| 环节 | 原版 | 本版 |
|---|---|---|
| 配音 | 小米 MiMo（需 `MIMO_API_KEY`） | 本地 TTS：系统 `say` / Piper / edge-tts，可自带命令 |
| 逐字对齐 | MiMo + whisper | faster-whisper 词级；没有就按字数比例 |
| 配乐 | 作者授权曲库 `vibe-bgm.m4a` | `make_bgm.py` 代码合成，可自由分发 |
| 增强镜头 | Renoise MCP（按积分计费） | 默认不做；自己放图/片段到 `assets/` 即可 |
| 引擎接入 | 往 ai-teardown 里字符串打补丁 | 引擎随包自带，已固化全部钩子 |
| 风格预览图 | 作者渲染的 44 张 still.jpg | 不含；风格规范在 `styles/*/STYLE.md` |

原版是精品工具链，值得一看；本版的目标是**任何人 clone 下来就能跑，不欠任何账号**。

---

## 环境

必需：

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt      # numpy scipy pillow playwright
```

外加 `ffmpeg`，以及一个 Chrome / Chromium / Edge（复用系统已装的，**不用**下 Playwright 的 chromium）。

可选（装了更好，不装也能出片）：

| 组件 | 作用 | 装法 |
|---|---|---|
| `faster-whisper` | 词级逐字对齐 + OCR 之外的回读质检 | `pip install faster-whisper`，首次跑会下模型 |
| Piper 模型 | 比系统语音自然的本地中文音色 | 下 `zh_CN-huayan-medium.onnx` 放到 `~/.local/share/piper/` |
| `edge-tts` | 音色最好（需联网，非官方接口） | `pip install edge-tts` |
| `earshot` | 代码合成音效（转场、点击、揭示） | 见 `references/10-earshot.md` |

macOS 自带 `swiftc`，`qa.py` 用它编译 Vision OCR 做屏幕文字回读；其他平台质检会跳过 OCR 那一步。

---

## 六道工序

每期都走这六步，**中间有三个人工确认点，不要跳**。

| # | 工序 | 产出 | 确认 |
|---|---|---|---|
| ① | 选题 · 母版 · 风格 · 时长 | 一页方案 | **第 1 次：方向对不对** |
| ② | 事实台账 | `facts.md`（每条带出处） | — |
| ③ | 旁白 + 对抗审查 | `narration.json`（逐拍 + `[[cue]]`） | **第 2 次：稿子听不听得下去** |
| ④ | 配音 + 时间轴 | `build/narration.wav`、`build/timings.json` | 试听 `probe.wav` |
| ⑤ | 镜头表 | `film.js` | — |
| ⑥ | 渲染 + 质检 + 发布包 | 成片 mp4、接触表、OCR 回读 | **第 3 次：看成片** |

### ① 建期

```bash
python3 tools/new_film.py 01 --template A --title "本福特定律"
```

`--template`：A 猜谜概念片（3:30–4:30）· B 两难选择片（2:55）· C 痛点原理片（2–2:30）
· D 一条主线片（3:00）· E 闯关片（4–6 min）· F 六面轮转片（45–60 秒）。

不确定选哪个就给选题，用 `tools/recommend.py "<选题>"` 拿风格推荐，`tools/duration.py` 估算时长档位。

### ② 事实台账

`facts.md` 每条一个「断言 → 出处」。**屏幕上的每个数字都必须在这里能查到**——
后面 `qa.py` 的 OCR 回读就是拿它逐条比对的。写不出出处的说法，删掉或改成「有争议，两说并列」。

### ③ 旁白

`narration.json` 逐拍写，`[[cue]]` 标记「这个词出现时画面该动」：

```json
{ "id": "B04", "narration": "九个数字里，一占了百分之三十。[[bars]] 本该各 11.1%。" }
```

写完全局过一遍：念出来拗口的地方改短句；`lexicon` 里处理会被念错的缩写（`{"AI": "A I"}`）。

### ④ 配音

```bash
python3 tools/tts_local.py <期目录> --probe     # 先听第一拍，定音色
python3 tools/tts_local.py <期目录>             # 正式：逐拍合成 + 对齐 + 拼接
```

自动选后端（本地优先）：Piper → 系统 `say` → edge-tts。指定音色：

```bash
python3 tools/tts_local.py <期目录> --backend edge --voice zh-CN-XiaoxiaoNeural
python3 tools/tts_local.py <期目录> --backend say  --voice Tingting --rate 190
python3 tools/tts_local.py <期目录> --backend cmd  --cmd "你的tts --text {text} --out {out}"
```

对齐有 `faster-whisper` 就是词级真对齐（字幕跟着实际发音走）；没有就按字数比例，
够用但节奏偏钝。对齐结果异常（超长停顿）时该拍自动退回比例，不会让字幕卡住。
换大模型更准：`--align-model small`。

### ⑤ 镜头表

`film.js` 是唯一的画面真相，契约极简：

```js
export async function build(ctx) {
  const add = (from, to, b, r) => shots.push({ from, to, build: b, render: r });
  add(0, T("B03"), (root) => ({ ... }), (t, u) => { bg(ctx, TM); u.q.update(t, ...); });
  return shots;
}
```

`render(t, u)` 是**纯函数**：只吃绝对时间，不依赖上一帧。组件都在 `engine/engine/know.js`
（25 个：`keyword` / `counter` / `bars` / `spread` / `chapter` / `ask` / `choice` / `plate` /
`vquote` / `trail` / `foot` / `foots` / `seriesCard` …），视觉主题 `TH` 有 5 套。

**必须给每个镜头加持续运动**（缓推 `drift`、光扫 `sweep`、粒子）。`qa.py` 对「静止超过 3 秒」是硬告警，
纯静态排版会被判不过。

### ⑥ 渲染

```bash
python3 tools/render.py <系列目录> <期号>              # 录制 + 混音 + 质检
python3 tools/render.py <系列目录> <期号> --still 2,10,30   # 先出样帧看版式
python3 tools/render.py <系列目录> <期号> --from 20 --to 34  # 只重录这一段
```

`render.py` 自己起静态服务、找浏览器、跑完收工。约 21 帧/秒，60 秒片子约 3 分钟。

---

## 精品标准（硬门槛，不是建议）

1. **三层构图**：背景 / 主体 / 信息层，任何一层都不是纯装饰。
2. **没有静止超 3 秒**的画面——这是 `qa.py` 会直接报的。
3. **每章一个「王炸」镜头**：粒子爆发、数据倾泻、光轨拖尾、视差推近。
4. **声音分层**：旁白 / BGM / 音效三层，BGM 说话时自动压到人声下 10 dB（`bgm.py` 会算）。
5. **整期一个视觉系统**：颜色、字体、动效曲线统一，不要这镜头古风下镜头赛博。
6. **每句有出处**：脚注跟画面同在，`facts.md` 是唯一真相源。

## 时长与配乐

`duration.py` 按字数估片长。BGM 默认由 `make_bgm.py` 合成：

```bash
python3 engine/tools/make_bgm.py --out bgm.wav --seconds 90 --mood calm --key Am --bpm 72
```

三种情绪 `calm / warm / tense / bright`，换 `--seed` 就是另一条曲子。第一次混音时
`engine/tools/bgm.py` 会自动生成 `cine/audio/bgm-source.wav` 并按片长裁。想换成自己的曲子：
在 `film.js` 的 music 条目写 `{ src: P("audio/你的.wav"), bgm: true, user_request: "用户原话" }`。

## 风格库

`styles/catalog.json` 是唯一真相源，44 套风格分 8 个家族（东方、暗场概念、游戏、剪辑纪实、
明亮流行、图解设计、印刷纸感、电影感），每条带 `fit`（适合什么题材）、`keywords`（选题打分用）、
`templates`（配哪几个母版）。每套风格另有 `styles/<key>/STYLE.md` 写清配色、字体、构图、动效。

**母版（怎么讲）× 风格（长什么样）是两个正交轴**，6 × 44 的组合空间。加风格只需加数据，
不用改代码。`styles/_samples/` 里有 10 份真实 `film.js`，是最快的写法参考。

## 目录

```
engine/           渲染引擎（已固化全部钩子，拷贝即用）
  engine/*.js     core / narr / ui / util / post / glsl / know
  tools/          record / stills / finish / bgm / browser / clips
  fonts/          Noto Sans SC、Geist、Geist Mono（OFL）
  vendor/         three.js
tools/            new_film / tts_local / make_bgm / render / qa / recommend / duration
styles/           catalog.json + 44 套 STYLE.md + 10 份 film.js 样例
templates/        6 个母版大纲、film 骨架、facts / assets 模板
references/       旁白写法、精品标准、视觉系统、时长、发布、踩坑
```

## 三条容易踩的坑

- **`say -v Eddy` 合成 0.02 秒空音频**：Eddy/Flo/Grandma 在中文音色表里，但同名英文音色优先匹配。
  用 `Tingting`，或让脚本自动选（它已把 Tingting 排在第一）。
- **faster-whisper 吃 ndarray 时假定 16 kHz**，喂 48 kHz 会让时间戳整体缩成 1/3、逐字全乱。
  `tts_local.py` 已做抽取。
- **`qa.py` 不能连跑第二次**：`build/qa/frames` 里有残留会干扰接触表。先 `rm -rf build/qa`。

## 授权

代码与文档 MIT。字体 OFL。**不含**原作者的样片、海报、风格预览图、默认 BGM 与默认音色——
那些资产按原仓库 NOTICE 不可二次分发，所以本版全部用代码重建。详见 `NOTICE.md` 与 `THIRD_PARTY.md`。
