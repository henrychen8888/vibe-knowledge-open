# assets

放你自己的东西，仓库里默认是空的（合成曲和字体都不在这里）。

| 子目录 | 放什么 | 谁会用 |
|---|---|---|
| `voices/` | Piper 的 `.onnx` + `.onnx.json` 中文模型 | `tools/tts_local.py` 的 `--voice` 会先在这里找 |
| `music/` | 你想复用的 BGM 源（wav/mp4 都行） | `film.js` 里的 music 条目引用 |

Piper 模型也可以放在 `~/.local/share/piper/`，两边都会找。首个混音时
`engine/tools/bgm.py` 会在**系列目录**的 `cine/audio/` 下生成合成曲 `bgm-source.wav`，
那个不进仓库（见 `.gitignore`）。
