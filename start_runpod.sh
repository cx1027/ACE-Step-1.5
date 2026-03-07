#!/usr/bin/env bash
# ACE-Step RunPod Serverless Startup Script
# This script ensures models are downloaded before starting the handler

set -euo pipefail

# Get checkpoint directory from environment variable (default: /runpod-volume/checkpoints)
CHECKPOINT_DIR="${CHECKPOINT_DIR:-/runpod-volume/checkpoints}"

echo "========================================"
echo "ACE-Step RunPod Startup"
echo "========================================"
echo "Checkpoint directory: $CHECKPOINT_DIR"
echo

# Check if VAE model exists (indicator that main model is present)
VAE_MODEL_PATH="$CHECKPOINT_DIR/vae/diffusion_pytorch_model.safetensors"

if [ -f "$VAE_MODEL_PATH" ]; then
    echo "Models already cached, skipping download."
    echo
else
    echo "VAE model not found, starting download..."
    echo "This may take a while depending on your internet connection..."
    echo
    
    # Call Python to download models using ensure_main_model
    python -c "
import os
import sys
from pathlib import Path
from acestep.model_downloader import ensure_main_model
from loguru import logger

checkpoint_dir = os.environ.get('CHECKPOINT_DIR', '/runpod-volume/checkpoints')
checkpoint_path = Path(checkpoint_dir)

logger.info(f'Checking models in: {checkpoint_path}')
success, message = ensure_main_model(checkpoints_dir=checkpoint_path)

if success:
    logger.info(f'Model download completed: {message}')
    sys.exit(0)
else:
    logger.error(f'Model download failed: {message}')
    sys.exit(1)
" || {
        echo
        echo "========================================"
        echo "ERROR: Model download failed"
        echo "========================================"
        echo "Please check your network connection and try again."
        exit 1
    }
    
    echo
    echo "Model download completed successfully!"
    echo
fi

echo "Starting RunPod handler..."
echo

# Start the RunPod handler
exec python runpod_handler.py
