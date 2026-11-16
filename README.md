# Vibe 知识大赏 · 开源版

把**一个知识点**做成一条 45 秒～5 分钟的知识短片：有旁白、有字幕、每句有出处、1080p60。

**不需要任何 API 密钥，不花一分钱积分。** 配音、对齐、配乐、画面全部在你本机完成。

```
选题 → 事实台账 → 旁白 → 配音对齐 → 镜头表(film.js) → 逐帧渲染 → OCR 回读质检 → 发布包
```

## 它和一般「AI 视频工具」不一样的地方

大多数 AI 视频工具是**生成画面**：给提示词，模型吐像素，每次都不一样，风格不可控，按次计费。

这个是**算画面**：模型写一份 `film.js` 镜头表（就是代码），浏览器按时间 `seek(t)` 逐帧渲染。

| | 生成式 | 本项目 |
|---|---|---|
| 画面来源 | 扩散模型采样 | 代码绘制的 SVG / Canvas / WebGL |
| 可复现 | 同一提示词偏差很大 | 同一秒渲两次像素级一致 |
| 成本 | 按张/按秒计费 | 零 |
| 改一个数字 | 重刷整条 | 只重渲那 3 秒 |
| 适合 | 写实镜头、真实质感 | 数据图、概念图、文字动画、抽象视觉 |

结论：**能用代码表达的，就别花积分。** 真正需要写实质感的镜头，自己用惯的工具生成后丢进 `assets/` 即可，不绑定任何服务。

## 安装

```bash
git clone <this-repo> vibe-knowledge-open
cd vibe-knowledge-open
./install.sh            # 或手动：python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

前提：`ffmpeg` + 一个 Chrome / Chromium / Edge（复用系统已装的，不下载 Playwright 浏览器）。

可选，装了更好：

```bash
pip install faster-whisper      # 词级逐字对齐（不装则按字数比例，够用但节奏偏钝）
pip install edge-tts            # 音色最好的配音后端（需联网）
# Piper 中文模型 → ~/.local/share/piper/zh_CN-huayan-medium.onnx
```

## 五分钟跑一期

```bash
# 1. 建期（母版 F：六面轮转片，45–60 秒，适合先试水）
python3 tools/new_film.py 01 --template F --title "为什么 1 最多"

# 2. 写 facts.md（每条断言带出处）和 narration.json（逐拍旁白）

# 3. 配音 + 逐字时间轴
python3 tools/tts_local.py vibe-workspace/examples/vk/lessons/01 --probe   # 先听音色
python3 tools/tts_local.py vibe-workspace/examples/vk/lessons/01

# 4. 写 film.js 镜头表（参考 styles/_samples/ 里的 10 份真实例子）

# 5. 渲染（自己起服务、找浏览器、跑完收工）
python3 tools/render.py vibe-workspace/examples/vk 01
```

产物在 `vibe-workspace/examples/vk/lessons/01/build/lesson01.mp4`，
同目录 `qa/` 里有接触表和 OCR 回读结果。

## 命令一览

| 命令 | 作用 |
|---|---|
| `tools/new_film.py` | 建一期（引擎 + 母版骨架 + 模板） |
| `tools/tts_local.py` | 配音 + 逐字对齐（say / Piper / edge-tts / 自带命令） |
| `engine/tools/make_bgm.py` | 代码合成 BGM（4 种情绪、可换调式与种子） |
| `tools/render.py` | 录制 + 混音 + 质检一条龙 |
| `tools/qa.py` | 接触表、OCR 回读、响度、冻结帧、BGM 检测 |
| `tools/recommend.py` | 按选题推荐风格 |
| `tools/duration.py` | 按字数估片长档位 |
| `tools/cover_first.py` | 封面接成首帧 |

## 内置了什么

- **6 种脚本母版**：猜谜 / 两难 / 痛点原理 / 一条主线 / 闯关 / 六面轮转，从 15 条爆款反推
- **44 套视觉风格 / 8 个家族**：每套有 `STYLE.md` 写清配色、字体、构图、动效
- **10 份真实 `film.js` 样例**：`styles/_samples/`，最快的写法参考
- **25 个画面组件**：关键词、计数器、柱状图、地图扩散、光轨、竖排古文、出处脚注、两难按钮…
- **5 套视觉主题**：starfield / gufeng / darkgold / paper / pixel
- **质检闭环**：事实台账 → 屏幕 OCR 回读逐条比对 → 响度 / 峰值 / 冻结帧 / BGM 四道门禁

## 授权

代码与文档 MIT。字体 OFL。三方组件见 `THIRD_PARTY.md`。

本仓库**不含**原作者的样片、海报、风格预览图、默认 BGM 与默认音色——那些按上游 NOTICE 不可二次分发，
所以这里的配乐用代码合成、风格用文档描述。衍生关系说明见 `NOTICE.md`。

做出来的片子是你自己的，随便发。
