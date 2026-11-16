# 08 · 两档制作：全代码 / 自备素材

原则只有一条：**能用代码做的都用代码做**。代码画面零成本、可复现、改一个数字只重渲那几秒；
写实镜头才值得动用外部工具，而且用谁的工具由你决定，本 skill 不绑定任何服务。

## 代码档（默认，零成本零密钥）

| 层 | 用什么 |
|---|---|
| 旁白 | `tools/tts_local.py`：系统语音 / Piper / edge-tts / 自带命令；对齐用 faster-whisper |
| 画面主体 | **直接写 SVG 插画**（扁平矢量人物 / 建筑 / 器物 / 地图轮廓），`layers` 分远中近三层做视差推移；`Particles` / `Tunnel` / `Liquid` 等做抽象概念 |
| 数据与信息 | know.js：`counter`、`bars`、`spread`、`trail`、`vquote`、`keyword`、`chapter`、`foot` |
| 配乐 | `engine/tools/make_bgm.py` 合成（首次混音时 `bgm.py` 自动生成并裁到片长）；想换曲见下 |
| 音效 | cine 内置（slam whoosh riser impact chime tick shutter card…，写进 `sfx`）+ 可选 earshot 代码音效 |
| 素材 | 公有领域 / CC 素材可用（Wikimedia 古画、古籍书影、NASA 图），署名写进片尾与 `facts.md`；不用来路不明的图 |

**怎么做到精品**：

- 每个场景至少三层 SVG（远景剪影、中景主体、前景遮挡物），推移时有景深。
- 人物用「几何化无五官」造型，画得稳、整期统一，也没有肖像风险。
- 每章一个「代码王炸」镜头：粒子聚字、光点变形、地图扩散、3D 镜头穿梭。
- 色板严格按视觉系统（`03-visual-systems.md`），颗粒与暗角统一由 `bg()` 控制。
- **每个镜头都要有持续运动**（缓推 / 光扫 / 粒子）。静止超 3 秒 `qa.py` 直接告警。

## 自备素材档（可选，成本发生在你那边）

判断哪些镜头值得动用外部工具（满足任意一条）：

1. 写实场景代码画不出来：历史现场、自然现象（雷暴、洪水、星云）、真实材质（青铜、丝绸、古籍纸纹）。
2. 全片最需要被记住的 1–3 个时刻：冷开场、反转、高潮。
3. 需要真实运动：人群、水流、火、机械运转。

其余镜头（数据、地图、文字、图表、抽象概念、示意动画）**仍然用代码**。

用你惯的工具生成（任何生图 / 生视频服务、本地 SD、自己拍的照片都行），然后：

| 素材类型 | 放哪 | 在 film.js 里怎么用 |
|---|---|---|
| 静态配图 | `lessons/<期号>/assets/img/` | `plate(s, { src: A("img/a01.jpg") })` |
| 视频片段 | `lessons/<期号>/assets/clips/` | 先 `tools/clip2frames.py` 转帧序列，再 `vclip` |
| 音效 | `lessons/<期号>/assets/audio/` | `music.push({ src: P("audio/sfx.wav"), at: T("B04"), dur: 2, gain: -8 })` |
| 整段配乐 | `lessons/<期号>/assets/audio/` | `music.push({ src: P("audio/your.wav"), bgm: true, user_request: "用户原话" })` |

**换 BGM 的那个 `user_request` 是必须的**：`bgm.py` 只认「用户明确要求换曲」这一种情况，
随便标的 `bgm: true` 会被忽略并照常用合成曲。这是为了防止模型自作主张把统一音色换掉。

## 一份 film.js 两种档位通用

素材有没有都不改镜头结构，只切一个开关：

```js
const ENH = false;   // 有素材了改成 true
const scene01 = (s) => ENH
  ? plate(s, { src: A("img/a01.jpg") })
  : layers(s, [{ svg: SVG_SKY, depth: 0.15 }, { svg: SVG_PALACE, depth: 0.5 }, { svg: SVG_FG, depth: 1 }]);
// render 里两者签名一样：x.update(t, t0, t1, { … })
```

这样同一期可以在「先出个纯代码版本给人看」和「补几张写实图出正式版」之间来回切，
只重渲改动的那几个镜头（`render.py --from 20 --to 34`）。
