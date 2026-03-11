## RunPod JSON 输入格式速查（ACE-Step-1.5）

本文档用于**记录 RunPod Serverless 调用**时 Job 请求体的 JSON `input` 字段格式，按三种常用模式给出可直接复制的示例：

- `mode: "simple"`：纯伴奏（服务端会强制 `lyrics="[Instrumental]"`）
- `mode: "custom"`：你提供完整歌词（`lyrics` 必填）
- `sample_query`：给自然语言描述，由内置 LLM 自动推理 `caption/lyrics/metas`

> RunPod 标准请求外层结构为 `{ "input": { ... } }`，真正关注的是 `input` 内字段。

---

## 一、simple mode（`mode: "simple"`）

```json
{
  "input": {
    "mode": "simple",
    "prompt": "dark cinematic trap instrumental, mythic monkey king energy, heavy 808s, sparse bells, industrial textures, haunting atmosphere, dramatic rise, aggressive low end",
    "lyrics": "[Instrumental]",
    "duration": 60,
    "bpm": 140,
    "keyscale": "A minor",
    "timesignature": "4/4",
    "vocal_language": "en",
    "thinking": false,
    "lm_temperature": 0.85,
    "lm_top_p": 0.9,
    "lm_top_k": 50,
    "lm_cfg_scale": 2.5,
    "inference_steps": 8,
    "guidance_scale": 7.0,
    "seed": 12345,
    "batch_size": 1,
    "audio_format": "mp3"
  }
}
```

---

## 二、custom mode（`mode: "custom"`）

```json
{
  "input": {
    "mode": "custom",
    "caption": "dark cinematic trap with neo-soul undertones, emotional male vocal, melodic rap-singing, haunting ad-libs, heavy 808s, sparse bells, industrial textures, hypnotic hook, mythic monkey king energy, wounded but arrogant mood",
    "lyrics": "[Intro]\nStone in my chest, gold in my stare\nSky used to know me, now nobody there\n\n[Verse 1]\nBuried alive but I still talk fly\nFive peaks on my back, still I won’t die\nDust in my teeth, thunder in my veins\nHeaven threw chains, I turned them to names\n\n[Hook]\nI’m still him, even under stone\nStill got fire in my broken bones\nFive hundred winters, I slept alone\nNow the whole sky gon’ feel this tone",
    "duration": 75,
    "bpm": 140,
    "keyscale": "A minor",
    "timesignature": "4/4",
    "vocal_language": "en",
    "thinking": false,
    "lm_temperature": 0.85,
    "lm_top_p": 0.9,
    "lm_top_k": 50,
    "lm_cfg_scale": 2.5,
    "inference_steps": 8,
    "guidance_scale": 7.0,
    "seed": 8888,
    "batch_size": 1,
    "audio_format": "mp3"
  }
}
```

---

## 三、sample_query mode（`sample_query`）

> 只要 `input` 中存在非空 `sample_query`（或 `sampleQuery`），就会进入该模式（与 `mode` 字段无关）。

```json
{
  "input": {
    "sample_query": "Write and generate a full English song with sung lyrics about the Monkey King after centuries of imprisonment. Use a dark cinematic trap style with emotional male vocals, heavy 808s, sparse bells, haunting ad-libs, a clear verse-chorus structure, and a catchy hook.",
    "duration": 60,
    "vocal_language": "en",
    "thinking": false,
    "lm_temperature": 0.85,
    "lm_top_p": 0.9,
    "lm_top_k": 50,
    "lm_cfg_scale": 2.5,
    "inference_steps": 8,
    "guidance_scale": 7.0,
    "seed": 42,
    "batch_size": 1,
    "audio_format": "mp3"
  }
}
```

