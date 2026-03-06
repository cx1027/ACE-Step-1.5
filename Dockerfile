# =============================================================================
# ACE-Step 1.5 — RunPod Serverless Dockerfile
# =============================================================================
#
# Builds ACE-Step 1.5 for RunPod serverless deployment with .env file support.
#
# Build:
#   docker build -t acestep-runpod .
#
# Run locally (for testing):
#   docker run --gpus all -it --rm \
#     -v $(pwd)/checkpoints:/app/checkpoints \
#     -v $(pwd)/.env:/app/.env \
#     acestep-runpod
#
# For RunPod deployment:
#   1. Build and push to a container registry
#   2. Use the image in RunPod serverless endpoint
#   3. Set handler path: runpod_handler.py
#   4. Configure environment variables in RunPod console (recommended)
#      OR include .env file in the image (see below)
#
# =============================================================================

# ==================== Base image ====================
# Use Python 3.11 on Ubuntu 22.04 (compatible with RunPod)
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# ==================== System packages ====================
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        git \
        curl \
        wget \
        pkg-config \
        # Audio processing libraries
        libsndfile1 \
        libsndfile1-dev \
        ffmpeg \
        # BLAS / LAPACK for scipy & numpy
        libopenblas-dev \
        liblapack-dev \
        gfortran \
    && rm -rf /var/lib/apt/lists/*

# ==================== Python dependencies ====================
# Upgrade pip and install build tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install PyTorch with CUDA 12.8 (for Linux x86_64)
RUN pip install --no-cache-dir \
        torch==2.10.0+cu128 \
        torchvision==0.25.0+cu128 \
        torchaudio==2.10.0+cu128 \
        --extra-index-url https://download.pytorch.org/whl/cu128

# Install RunPod-specific dependencies
RUN pip install --no-cache-dir \
        runpod \
        boto3 \
        python-dotenv

# Install core ACE-Step dependencies
RUN pip install --no-cache-dir \
        "transformers>=4.51.0,<4.58.0" \
        "diffusers" \
        "gradio==6.2.0" \
        "matplotlib>=3.7.5" \
        "scipy>=1.10.1" \
        "soundfile>=0.13.1" \
        "loguru>=0.7.3" \
        "einops>=0.8.1" \
        "accelerate>=1.12.0" \
        "fastapi>=0.110.0" \
        "diskcache" \
        "uvicorn[standard]>=0.27.0" \
        "numba>=0.63.1" \
        "vector-quantize-pytorch>=1.27.15" \
        "torchcodec>=0.9.1; platform_machine != 'aarch64'" \
        "torchao>=0.14.1,<0.16.0" \
        "toml" \
        "safetensors==0.7.0" \
        "modelscope" \
        "peft>=0.18.0" \
        "lycoris-lora" \
        "lightning>=2.0.0" \
        "tensorboard>=2.20.0" \
        "typer-slim>=0.21.1" \
        "xxhash" \
        "pyyaml"

# Install nano-vllm dependencies (for LLM backend)
RUN pip install --no-cache-dir \
        "triton>=3.0.0" \
        "flash-attn" \
        || echo "WARNING: flash-attn install failed (non-fatal — will fall back to SDPA)"

# ==================== Project source ====================
WORKDIR /app

# Copy project files
COPY . /app/

# Install ACE-Step package in editable mode
# This ensures acestep module can be imported by runpod_handler.py
RUN pip install --no-cache-dir -e .

# Install nano-vllm from local source (if available)
RUN if [ -d "acestep/third_parts/nano-vllm" ]; then \
        pip install --no-cache-dir --no-deps acestep/third_parts/nano-vllm || \
        echo "WARNING: nano-vllm install failed (non-fatal)"; \
    fi

# ==================== .env file support ====================
# To include .env file in the image (for development/testing):
#   1. Copy runpod.env.example to .env and fill in your values
#   2. Uncomment the COPY line below:
#      COPY .env /app/.env
#
# WARNING: Including .env in the image will embed secrets. For production,
# use RunPod's environment variable settings instead (see RUNPOD_DEPLOYMENT.md).
#
# The handler will automatically load .env if it exists at runtime.
# If .env is not included, configure environment variables in RunPod console.
#
# Copy example file for reference
COPY runpod.env.example /app/runpod.env.example

# Uncomment the next line to include .env file in the image:
# COPY .env /app/.env

# ==================== Runtime directories ====================
RUN mkdir -p /app/checkpoints /tmp/acestep_output

# ==================== Environment defaults ====================
# These can be overridden by RunPod environment variables or .env file
ENV ACESTEP_PROJECT_ROOT=/app
ENV ACESTEP_CONFIG_PATH=acestep-v15-turbo
ENV ACESTEP_DEVICE=auto
ENV ACESTEP_USE_FLASH_ATTENTION=true
ENV ACESTEP_COMPILE_MODEL=false
ENV ACESTEP_OFFLOAD_TO_CPU=false
ENV ACESTEP_OFFLOAD_DIT_TO_CPU=false
ENV ACESTEP_LM_MODEL_PATH=acestep-5Hz-lm-0.6B
ENV ACESTEP_LM_BACKEND=vllm
ENV ACESTEP_LM_OFFLOAD_TO_CPU=false
ENV TOKENIZERS_PARALLELISM=false

# ==================== Health check ====================
# Lightweight probe: check if Python can import the handler
HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=3 \
    CMD python -c "import runpod_handler" || exit 1

# ==================== Entrypoint ====================
# RunPod serverless will call the handler directly
# The handler is configured in RunPod console: handler = runpod_handler.py
ENTRYPOINT ["python", "runpod_handler.py"]
