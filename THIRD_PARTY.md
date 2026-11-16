# 第三方组件

本仓库自带或建议安装的组件，各自的授权如下。代码部分是 MIT，字体不是——字体按 SIL OFL 分发。

## 随仓库自带

| 组件 | 位置 | 许可证 | 说明 |
|---|---|---|---|
| Noto Sans SC | `engine/fonts/NotoSansSC-VF.ttf` | SIL OFL 1.1 | Google / Adobe。可变字重，正文与标题共用 |
| Geist | `engine/fonts/Geist-VF.ttf` | SIL OFL 1.1 | Vercel。西文与数字 |
| Geist Mono | `engine/fonts/GeistMono-VF.ttf` | SIL OFL 1.1 | Vercel。等宽，用来排数据与代码 |
| three.js | `engine/vendor/three.*.min.js` | MIT | WebGL 场景（粒子、光轨、三维） |
| cine 渲染引擎 | `engine/engine/*.js`、`engine/tools/*.py` | MIT | 作者 Berryxia（andyhuo520），来自 ai-teardown |
| know.js 知识片组件 | `engine/engine/know.js` | MIT | 同上，为知识短片新写的 25 个组件 |

OFL 的要求是：字体文件可以随软件分发、可以嵌入产物，但**不能单独售卖字体**，
修改字体文件后不能用原名称。本仓库未修改字体，只是随附。

## 建议安装（不随仓库分发）

| 组件 | 许可证 | 用途 | 备注 |
|---|---|---|---|
| numpy / scipy | BSD-3 | 音频合成、混音、滤波 | 必需 |
| pillow | MIT-CMU | 接触表拼图 | 必需 |
| playwright | Apache-2.0 | 驱动浏览器逐帧截图 | 必需（浏览器用你系统里的 Chrome，不下载 Playwright 的 chromium） |
| ffmpeg | LGPL / GPL（取决于编译选项） | 编解码、抽帧、响度 | 必装，自行安装 |
| faster-whisper | MIT | 词级逐字对齐、回读 | 可选 |
| CTranslate2 | MIT | faster-whisper 的推理后端 | 随 faster-whisper 装 |
| Whisper 模型 | MIT | 语音识别权重 | 首次运行自动下载 |
| Piper | MIT | 本地中文 TTS | 可选 |
| edge-tts | GPL-3.0 | 在线 TTS 后端 | 可选；**只在你自己装的时候**才引入，不随本仓库分发 |
| earshot | MIT | 代码合成音效 | 可选，作者 Leonxlnx |

## 关于 ocr.swift

`tools/ocr.swift` 用 macOS Vision 框架做屏幕文字识别，编译产物不随仓库分发（`qa.py` 首次运行会
用 `swiftc` 现场编译）。只在 macOS 可用；其他平台的质检会跳过 OCR 回读这一步，其余检查照常。
