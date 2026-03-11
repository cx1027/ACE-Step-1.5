## RunPod Serverless 调用说明（ACE-Step-1.5）

本文档说明 `runpod_handler.py` 在 **Simple Mode**、**Custom Mode**、**sample_query 模式** 下的请求 JSON 格式（RunPod Job 的 `input` 字段）。

如果你只想快速复制粘贴示例，请看：[`RunPod_JSON_Inputs.md`](RunPod_JSON_Inputs.md)。

所有示例均假设 RunPod 标准请求外层结构如下：

```json
{
  "input": {
    "...": "见下文"
  }
}
```

即：**真正需要关注的是 `input` 里的字段**。

---

## 一、Simple Mode（`mode = "simple"`）

**用途**：强制纯伴奏 / 器乐曲，忽略用户提供的歌词。

### 1. 必填字段

- **`mode`**：`"simple"`
- **`prompt` / `caption`**：描述音乐风格/内容的文本（二选一；`caption` 优先）
- **`duration` / `audio_duration` / `audioDuration`**：目标时长（秒）

### 2. 可选字段（常用）

- **`bpm`**：节奏（拍速），整数或浮点数
- **`key` / `key_scale` / `keyscale`**：调式，如 `"C major"`、`"A minor"`
- **`time_signature` / `timesignature`**：拍号，如 `"4/4"`、`"3/4"`
- **`vocal_language` / `vocalLanguage`**：人声语言代码（即便是 simple 模式也可设置，默认 `"en"`）
- **`audio_format` / `audioFormat`**：输出音频格式，默认 `"mp3"`
- **`seed`**：随机种子，`< 0` 表示使用随机种子（默认 `-1`）
- **`thinking`**：是否启用 CoT + LM 辅助（默认 `true`）
- **`use_cot_metas` / `use_cot_caption` / `use_cot_language`**：是否使用 CoT 生成的元数据/标题/语言（默认 `true`）
- **`lm_temperature` / `lmTemperature`**、`lm_top_k` / `lmTopK`、`lm_top_p` / `lmTopP`：LM 采样参数
- **`batch_size` / `batchSize`**：一次生成的样本数量（默认 `1`）
- **`callback_url`**：可选，用于接收进度回调

### 3. Simple Mode 示例

```json
{
  "input": {
    "mode": "simple",
    "prompt": "An uplifting orchestral track with epic drums",
    "duration": 30,
    "bpm": 120,
    "key": "C major",
    "time_signature": "4/4",
    "vocal_language": "en",
    "audio_format": "mp3",
    "seed": -1,
    "thinking": true,
    "use_cot_metas": true,
    "use_cot_caption": true,
    "use_cot_language": true,
    "lm_temperature": 0.85,
    "batch_size": 1,
    "callback_url": "https://your.server.com/runpod/callback"
  }
}
```

> 注意：在 `mode = "simple"` 下，服务端会强制 `lyrics = "[Instrumental]"`，即无论你是否传 `lyrics` 字段，都会按纯伴奏处理。

---

## 二、Custom Mode（`mode = "custom"`）

**用途**：需要你**显式提供完整歌词**，模型按照你给定的歌词生成带人声的音乐。

### 1. 必填字段

- **`mode`**：`"custom"`
- **`prompt` / `caption`**：描述音乐整体风格/氛围的文本（不一定是歌词）
- **`duration` / `audio_duration` / `audioDuration`**：目标时长（秒）
- **`lyrics`**：**必填**，完整的歌词文本；如果缺失则会报错：
  - `"Custom mode requires 'lyrics' in job input."`

### 2. 可选字段（同 Simple Mode）

- `bpm`
- `key` / `key_scale` / `keyscale`
- `time_signature` / `timesignature`
- `vocal_language` / `vocalLanguage`
- `audio_format` / `audioFormat`
- `seed`
- `thinking`
- `use_cot_metas` / `use_cot_caption` / `use_cot_language`
- `lm_temperature` / `lmTemperature`、`lm_top_k` / `lmTopK`、`lm_top_p` / `lmTopP`
- `batch_size` / `batchSize`
- `callback_url`

### 3. Custom Mode 示例

```json
{
  "input": {
    "mode": "custom",
    "caption": "Emotional pop ballad with piano and strings",
    "duration": 45,
    "lyrics": "Verse 1...\nChorus...\nVerse 2...",
    "bpm": 90,
    "keyscale": "A minor",
    "time_signature": "4/4",
    "vocal_language": "en",
    "audio_format": "mp3",
    "seed": 12345,
    "thinking": true,
    "use_cot_metas": true,
    "use_cot_caption": true,
    "use_cot_language": true,
    "lm_temperature": 0.8,
    "batch_size": 1,
    "callback_url": "https://your.server.com/runpod/callback"
  }
}
```

---

## 三、sample_query 模式（`sample_query` / `sampleQuery`）

**用途**：只给一段**自然语言描述**（query），由内置 LLM 自动推理并生成：

- 标题 / caption  
- 歌词（或器乐标记）  
- BPM / key / 拍号 / 时长 等元信息  

然后再调用 DiT 生成音乐。

### 1. 触发方式

- 在 `input` 中传入任意非空的：
  - **`sample_query`** 或
  - **`sampleQuery`**

当存在 `sample_query` / `sampleQuery` 且内容非空时：

- 会进入 sample_query 模式（与 `mode` 值无关）
- 内部会调用 `LLMHandler` 的 `create_sample` 推理元信息

> 注意：**sample_query 模式需要 LLM 已成功初始化**，否则会返回错误：
> `"sample_query mode requires LLM handler, but it's not initialized."`

### 2. 字段说明

#### 必填字段

- **`sample_query` / `sampleQuery`**：自然语言描述（例如“来一首 120BPM 的电子舞曲，有女声英文主歌和中文说唱”）

#### 可选字段（对 LLM / DiT 的影响）

- **`vocal_language` / `vocalLanguage`**：
  - 如果提供且不在 `("en", "unknown", "")`，则强制使用该语言作为样本语言
  - 否则使用从 `sample_query` 自动解析出的语言
- **`duration` / `audio_duration` / `audioDuration`**：
  - 显式指定时长会覆盖 LLM 推理出的 duration
  - 如果不提供，则使用 LLM 结果中的 `duration`，再不行就默认 `30` 秒
- **LM 采样参数**：
  - `lm_temperature` / `lmTemperature`（默认 `0.85`）
  - `lm_top_p` / `lmTopP`（如果 `< 1.0` 才会生效）
  - `lm_top_k` / `lmTopK`（如果 `> 0` 才会生效）
- **生成控制参数**（传入 DiT）：
  - `thinking`：是否启用 CoT + LM（在 sample_query 模式下，`use_cot_*` 会强制设为 `False`，因为元数据已经由 LLM 生成）
  - `seed`
  - `audio_format` / `audioFormat`
  - `batch_size` / `batchSize`
  - `callback_url`

### 3. sample_query 模式示例

```json
{
  "input": {
    "sample_query": "A high-energy EDM track with female English vocals and a Chinese rap verse, around 32 seconds, 128 BPM, suitable for a game trailer.",
    "duration": 32,
    "vocal_language": "en",
    "lm_temperature": 0.9,
    "lm_top_p": 0.95,
    "audio_format": "mp3",
    "seed": -1,
    "thinking": true,
    "batch_size": 1,
    "callback_url": "https://your.server.com/runpod/callback"
  }
}
```

在上述示例中：

- LLM 会根据 `sample_query` 自动生成：
  - `caption`（描述文本）
  - `lyrics`（包括英文女声主歌 + 中文 rap）
  - `bpm`、`keyscale`、`timesignature`、`duration` 等
- 你显式提供的 `duration` 会覆盖 LLM 推理的时长
- DiT 最终在 **sample_query 模式** 下生成音乐，返回结果结构与其他模式相同：

```json
{
  "status": "success",
  "output_url": "https://.../your_generated_song.mp3",
  "mode": "sample_query"
}
```

---

## 四、模式选择行为总结

- **Simple Mode**：`mode = "simple"`，忽略 `lyrics`，始终视为纯伴奏。
- **Custom Mode**：`mode = "custom"`，必须提供 `lyrics`，否则报错。
- **sample_query 模式**：只要 `sample_query` / `sampleQuery` 非空即启用，`mode` 字段会被忽略，元数据完全由 LLM 生成。

