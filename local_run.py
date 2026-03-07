"""Run ACE-Step RunPod handler locally with .env configuration.

This script is intended for local development/testing of the RunPod serverless
job handler (`runpod_handler.generate_music_job`) with the same environment
variables you would use in RunPod (e.g. R2 credentials).

Usage:
  - Create `.env` in the project root (recommended: `cp runpod.env.example .env`)
  - `uv sync`
  - `uv run python local_run.py --prompt "a beautiful melody" --duration 30`
"""

from __future__ import annotations

import argparse
import json
import os
import uuid
from pathlib import Path
from typing import Any

from loguru import logger


def _has_r2_config() -> bool:
    """Return True if all required Cloudflare R2 env vars are present.

    Supports two authentication methods:
    1. REST API: CLOUDFLARE_ACCOUNT_ID + CLOUDFLARE_API_TOKEN
    2. S3-Compatible: R2_ENDPOINT + R2_ACCESS_KEY + R2_SECRET_KEY
    """
    # Method 1: REST API (Bearer Token)
    rest_api_keys = [
        "CLOUDFLARE_ACCOUNT_ID",
        "CLOUDFLARE_API_TOKEN",
        "R2_BUCKET_NAME",
        "R2_PUBLIC_URL",
    ]
    has_rest_api = all(os.environ.get(key) for key in rest_api_keys)

    # Method 2: S3-Compatible API
    s3_keys = [
        "R2_ENDPOINT",
        "R2_ACCESS_KEY",
        "R2_SECRET_KEY",
        "R2_BUCKET_NAME",
        "R2_PUBLIC_URL",
    ]
    has_s3_api = all(os.environ.get(key) for key in s3_keys)

    return has_rest_api or has_s3_api


def _configure_mps_high_watermark() -> None:
    """Relax MPS high-watermark limit for local macOS runs to reduce spurious OOM."""
    # This environment variable is only respected by the PyTorch MPS backend on macOS.
    # Setting it to 0.0 disables the high-watermark guard, allowing allocations even
    # when the previous peak usage was near the OS unified-memory limit. This is
    # safe for local development on machines with sufficient RAM, but should not be
    # relied on for shared production environments.
    if os.environ.get("PYTORCH_MPS_HIGH_WATERMARK_RATIO") is not None:
        return

    try:
        import torch

        if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
            os.environ["PYTORCH_MPS_HIGH_WATERMARK_RATIO"] = "0.0"
            logger.info(
                "Detected macOS MPS; setting PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0 "
                "for local_run.py to reduce MPS high-watermark OOMs."
            )
    except Exception:
        # If torch is not available or MPS is misconfigured, we silently skip
        # and let the default behavior apply.
        logger.debug("Skipping MPS high-watermark configuration (torch/MPS unavailable).")


def _load_project_env() -> None:
    """Load `.env` from the project root if python-dotenv is installed."""
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - optional dependency, but should be installed via uv
        logger.warning("python-dotenv is not installed; skipping .env loading")
        return

    project_root = Path(__file__).resolve().parent
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(str(env_path), override=False)
        logger.info(f"Loaded environment variables from {env_path}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run generate_music_job locally.")
    parser.add_argument("--input-json", type=str, default="", help="Path to a RunPod job JSON file.")
    parser.add_argument("--prompt", type=str, default="a beautiful melody")
    parser.add_argument("--duration", type=float, default=30.0)
    parser.add_argument("--mode", type=str, default="", help="Optional: simple/custom")
    parser.add_argument("--lyrics", type=str, default="", help="Optional: lyrics (required for mode=custom)")
    parser.add_argument("--bpm", type=int, default=0)
    parser.add_argument("--key", type=str, default="")
    parser.add_argument("--inference-steps", type=int, default=8)
    parser.add_argument("--guidance-scale", type=float, default=7.0)
    parser.add_argument("--seed", type=int, default=-1)
    parser.add_argument("--thinking", action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args()


def _load_job_from_file(path: str) -> dict[str, Any]:
    job_path = Path(path).expanduser().resolve()
    with job_path.open("r", encoding="utf-8") as f:
        job = json.load(f)
    if not isinstance(job, dict):
        raise ValueError(f"Job JSON must be an object, got: {type(job)}")
    return job  # type: ignore[return-value]


def _build_job_from_args(args: argparse.Namespace) -> dict[str, Any]:
    job_input: dict[str, Any] = {
        "prompt": args.prompt,
        "duration": args.duration,
        "inference_steps": args.inference_steps,
        "guidance_scale": args.guidance_scale,
        "seed": args.seed,
        "thinking": args.thinking,
    }

    if args.mode:
        job_input["mode"] = args.mode
    if args.lyrics:
        job_input["lyrics"] = args.lyrics
    if args.bpm:
        job_input["bpm"] = args.bpm
    if args.key:
        job_input["key"] = args.key

    return {
        "id": os.environ.get("JOB_ID", str(uuid.uuid4())),
        "input": job_input,
    }


def main() -> None:
    """Entry point for local handler execution."""
    _configure_mps_high_watermark()
    _load_project_env()

    # For local runs without R2 configuration, default to keeping audio files on disk
    # instead of uploading to R2. If full R2 config is present, we leave
    # DISABLE_R2_UPLOAD unset so that uploads are enabled by default. Users can still
    # force-disable uploads by setting DISABLE_R2_UPLOAD=1/true/yes in their shell
    # or .env.
    if os.environ.get("DISABLE_R2_UPLOAD") is None and not _has_r2_config():
        os.environ["DISABLE_R2_UPLOAD"] = "1"
        logger.info(
            "DISABLE_R2_UPLOAD not set and R2 config not found; "
            "defaulting to 1 for local_run.py (no R2 uploads)."
        )

    args = _parse_args()
    if args.input_json:
        job = _load_job_from_file(args.input_json)
    else:
        job = _build_job_from_args(args)

    # Import after .env load so handler init sees the environment variables.
    from runpod_handler import generate_music_job

    result = generate_music_job(job)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

