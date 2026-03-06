# Local Handler Development & Testing Guide (zsh)

This guide explains how to run the ACE-Step RunPod handler **locally** from a `zsh` shell using
`local_run.py`. It is intended for macOS development and debugging, mirroring the environment that
`runpod_handler.generate_music_job` will see in production.

---

## 1. Prerequisites (zsh, macOS)

Make sure you have:

1. **macOS** with `zsh` as your login shell (default on modern macOS)
2. **Python & uv**:
   - Python 3.11–3.12 installed (e.g. via `pyenv` or system Python)
   - `uv` installed (see the ACE-Step README if needed)
3. **Project checkout**:

   ```bash
   # In zsh
   git clone <your-ace-step-repo-url>
   cd ACE-Step-1.5
   ```

4. (Optional but recommended) **Git LFS** for large model files.

---

## 2. Environment configuration (`.env`)

For local runs we use a `.env` file in the project root. This mirrors the variables you would
configure in RunPod:

1. **Create `.env` from the example**:

   ```bash
   cp runpod.env.example .env
   ```

2. **Edit `.env` in your editor and fill in values**, especially if you want Cloudflare R2 uploads:

   ```bash
   # Required R2 configuration (to enable uploads)
   R2_ENDPOINT=https://your-account-id.r2.cloudflarestorage.com
   R2_ACCESS_KEY=your-r2-access-key-id
   R2_SECRET_KEY=your-r2-secret-access-key
   R2_BUCKET_NAME=your-bucket-name
   R2_PUBLIC_URL=https://your-public-domain.com

   # Optional ACE-Step configuration
   ACESTEP_CONFIG_PATH=acestep-v15-turbo
   ACESTEP_DEVICE=auto
   ```

3. **R2 uploads vs local-only output**:

   - If **all** of `R2_ENDPOINT`, `R2_ACCESS_KEY`, `R2_SECRET_KEY`, `R2_BUCKET_NAME`,
     `R2_PUBLIC_URL` are set in `.env`, then:
     - `local_run.py` will **enable R2 uploads by default** (no `DISABLE_R2_UPLOAD` override)
   - If one or more of these are missing, then:
     - `local_run.py` will set `DISABLE_R2_UPLOAD=1` automatically
     - Outputs will be stored on the local filesystem (e.g. `/tmp/acestep_output/...`)
   - You can always **force-disable uploads** for safety by adding to `.env`:

     ```bash
     DISABLE_R2_UPLOAD=1
     ```

   - 此外，无论 R2 环境变量是否已经配置完整，你都可以通过在 `.env` 或 `zsh` 中把
     `DISABLE_R2_UPLOAD` 设为“真值”来**强制不上传**，例如：

     ```bash
     # 在 .env 中
     DISABLE_R2_UPLOAD=1
     DISABLE_R2_UPLOAD=true
     DISABLE_R2_UPLOAD=yes

     # 或在 zsh 里先导出再运行
     export DISABLE_R2_UPLOAD=1
     ```

---

## 3. Quick start (zsh, macOS)

From a `zsh` shell:

1. **Change into the project directory**:

   ```bash
   cd /Users/<your-username>/Documents/LLMApp/ACE-Step-1.5
   ```

2. **Install dependencies with uv**:

   ```bash
   uv sync
   ```

3. **Run the local handler with a prompt**:

   ```bash
   uv run python local_run.py --prompt "a beautiful melody" --duration 10
   ```

   - `local_run.py` will:
     - Relax the macOS MPS high-watermark (if using MPS) to reduce OOMs
     - Load `.env` from the project root
     - Build a fake RunPod job object
     - Call `runpod_handler.generate_music_job(job)`
     - Print the JSON result to stdout

   - If R2 uploads are enabled, the JSON will include a public URL pointing to your R2 bucket.
   - If R2 uploads are disabled, the JSON will reference local file paths (e.g. `/tmp/...`).

---

## 4. Advanced usage

### 4.1 Run with a saved RunPod job JSON

You can replay an actual RunPod job locally by saving the job JSON and passing `--input-json`:

```bash
uv run python local_run.py --input-json ./examples/sample_runpod_job.json
```

### 4.2 Custom lyrics and parameters

`local_run.py` exposes several arguments that map directly into the job `input`:

```bash
uv run python local_run.py \
  --prompt "upbeat pop track" \
  --duration 30 \
  --mode custom \
  --lyrics "These are my custom lyrics" \
  --bpm 120 \
  --key "C# minor" \
  --inference-steps 12 \
  --guidance-scale 8.0 \
  --seed 42 \
  --thinking
```

Arguments:

- `--prompt`: Text description of the desired music
- `--duration`: Duration in seconds
- `--mode`: `simple` or `custom` (lyrics required for `custom`)
- `--lyrics`: Optional lyrics for `custom` mode
- `--bpm`: Target beats per minute
- `--key`: Musical key (e.g. `C major`, `A minor`)
- `--inference-steps`: Number of diffusion steps
- `--guidance-scale`: Classifier-free guidance scale
- `--seed`: Random seed (`-1` for random)
- `--thinking` / `--no-thinking`: Enable/disable "thinking" output

---

## 5. Troubleshooting (zsh)

- **Command not found: uv**
  - Install `uv` following the project’s README, then restart your `zsh` session.

- **R2 uploads not happening**
  - In `zsh`, check:

    ```bash
    echo $R2_ENDPOINT
    echo $R2_BUCKET_NAME
    echo $DISABLE_R2_UPLOAD
    ```

  - Ensure all five R2 variables are set in `.env` and **do not** set `DISABLE_R2_UPLOAD=1`
    unless you explicitly want local-only output.

- **MPS / GPU issues on macOS**
  - Try running with CPU only by adding to `.env`:

    ```bash
    ACESTEP_DEVICE=cpu
    ```

