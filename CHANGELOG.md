# Changelog

本项目的所有显著变更都记录在本文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/cn/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

（暂无）

## [1.0.0] - 2026-11-16

### 首发

- **Vibe 知识大赏 · 开源版**：一个知识点 → 一条 45 秒～5 分钟、有旁白、句句有出处的知识短片。
- **画面**：不生成、而是计算画面——模型写 `film.js` 镜头表，浏览器按 `seek(t)` 逐帧渲染（1080p60），同一秒两次渲染像素级一致，风格 100% 可复现。
- **配音**：本地 TTS（系统 `say` / Piper / edge-tts），可自带命令；逐字对齐走 faster-whisper，缺失时按字数比例兜底。
- **配乐**：`make_bgm.py` 代码合成，可自由分发（无版权曲库依赖）。
- **6 种脚本母版**：猜谜概念片、两难选择片、痛点原理片、一条主线片、闯关片、六面轮转片（自 15 条爆款反推）。
- **43 种视觉风格**（`styles/`），每种含 `STYLE.md` 风格规范；引擎随包自带，固化全部钩子。
- **成片流程**：带出处的事实清单 → 旁白稿 → 三维确认 → 代码成片 → OCR 回读质检 → 发布包（标题、话题、封面、简介）。
- **全链路零 API 密钥、零积分**。

### 与原版（andyhuo520/vibe-knowledge）的差异

| 环节 | 原版 | 本版 |
|---|---|---|
| 配音 | 小米 MiMo（需 `MIMO_API_KEY`） | 本地 TTS：系统 `say` / Piper / edge-tts |
| 逐字对齐 | MiMo + whisper | faster-whisper 词级 |
| 配乐 | 作者授权曲库 `vibe-bgm.m4a` | `make_bgm.py` 代码合成 |
| 增强镜头 | Renoise MCP（按积分计费） | 默认不做；素材放 `assets/` |
| 引擎接入 | 往 ai-teardown 里字符串打补丁 | 引擎随包自带，已固化钩子 |
| 风格预览图 | 作者渲染的 44 张 still.jpg | 不含；风格规范在 `styles/*/STYLE.md` |

[Unreleased]: https://github.com/henrychen8888/vibe-knowledge-open/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/henrychen8888/vibe-knowledge-open/releases/tag/v1.0.0
