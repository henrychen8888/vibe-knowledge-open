# Notice · 衍生关系与资产说明

## 衍生自哪里

本项目的流程、脚本骨架、渲染引擎契约与内容方法论衍生自：

- **vibe-knowledge** — https://github.com/andyhuo520/vibe-knowledge（MIT）
- 其渲染引擎 **cine** 来自同作者的 **ai-teardown**

原项目的 LICENSE 是 MIT，覆盖代码与文档。本版在此基础上做了「去外部依赖」改造（见下），
改造部分同样以 MIT 发布。

## 本版改了什么

原版有几处依赖外部服务或不可再分发的资产，本版逐一替换：

| 原版 | 问题 | 本版处理 |
|---|---|---|
| 小米 MiMo TTS（`tts_mimo.py`） | 需要 `MIMO_API_KEY`，接口限免但不对公众开放 | 换成 `tools/tts_local.py`：系统语音 / Piper / edge-tts / 自带命令四后端 |
| MiMo ASR 回读打分 | 同上 | 换成 faster-whisper 转写 + 字符相似度；没有 whisper 就跳过并标注 |
| 默认 BGM `assets/music/vibe-bgm.m4a` | 作者取得授权随仓库提供，**NOTICE 明确不可单独分发或出售** | 移除；换成 `engine/tools/make_bgm.py` 代码合成（无采样，产物可自由使用与再分发） |
| 默认音色 `assets/voice/default-voice-ref.wav` | MiMo 音色设计的 AI 声音，作者资产 | 移除；音色由本机 TTS 决定 |
| 44 张 `styles/*/still.jpg` | 作者的作品，NOTICE 说明「仅作演示，不要当成自己的作品重新上传」 | 移除；保留 `STYLE.md` 文字规范，风格照样可用，只是没有预览图 |
| `docs/` 的样片、海报、动图 | 同上 | 不含 |
| Renoise MCP 增强层 | 按积分计费、需接入私有 MCP | 不做内置；需要写实镜头就自己生成后放进 `assets/img`、`assets/clips` |
| 往 ai-teardown 目录打字符串补丁 | 换宿主就断、上游改一行就静默失效 | 引擎随包自带，钩子已固化，`new_film.py` 只拷贝不修改 |

## 你需要知道的

- **做出来的片子是你自己的**，包括用内置合成 BGM 的版本，随便发、随便商用。
- 本仓库**不含**原作者的任何视频、图片、音频素材。如果你另外拿到原仓库的 `still.jpg` 或
  `vibe-bgm.m4a`，那些仍然受原 NOTICE 约束：不要当自己的作品重新上传，不要单独分发或出售。
- 用 `edge-tts` 后端时，音频由微软服务生成，遵守对方条款；介意就用本地 Piper 或系统语音。
- 克隆真人音色只能用于你本人或已获明确授权的声音。
- 事实与出处要自己核。片子里的每个数字都应能在 `facts.md` 里查到来源，`qa.py` 的 OCR
  回读只负责「屏幕上的字和台账一致」，不负责「这个事实本身对不对」。

---

# English

Derived from [andyhuo520/vibe-knowledge](https://github.com/andyhuo520/vibe-knowledge) (MIT) and its
`cine` engine from the same author's `ai-teardown`.

The upstream NOTICE restricts redistribution of the author's sample videos, posters, style previews
(`still.jpg`), the default BGM, and the default narrator voice. **None of those assets are included
here.** This version replaces them with code-generated equivalents: BGM is synthesized by
`engine/tools/make_bgm.py`, styles ship as written specs, and narration uses your local TTS.

Videos you produce are yours, including the synthesized soundtrack. Code and docs are MIT.
