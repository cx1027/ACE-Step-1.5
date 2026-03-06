"""RunPod serverless handler for ACE-Step music generation.

This handler processes RunPod serverless jobs to generate music using ACE-Step
and uploads the results to Cloudflare R2 storage.
"""

import json
import os
import uuid
from pathlib import Path
from typing import Any, Dict, Tuple
from urllib.error import URLError
from urllib.request import Request, urlopen

import boto3
import runpod

from acestep.handler import AceStepHandler
from acestep.inference import GenerationConfig, GenerationParams, generate_music
from acestep.llm_inference import LLMHandler
from loguru import logger

# Try to load .env file if available (optional dependency)
try:
    from dotenv import load_dotenv

    project_root = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(project_root, ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path, override=False)
        logger.info(f"Loaded environment variables from {env_path}")
except ImportError:
    # dotenv is optional - continue without it if not installed
    pass


def _get_project_root() -> str:
    """Get project root directory path.

    Returns:
        Project root path from environment variable or current working directory.
    """
    env_root = os.environ.get("ACESTEP_PROJECT_ROOT")
    if env_root:
        return os.path.abspath(env_root)
    return os.getcwd()


def _initialize_handlers() -> Tuple[AceStepHandler, LLMHandler]:
    """Initialize ACE-Step DiT and LLM handlers.

    Returns:
        Tuple of (dit_handler, llm_handler) initialized and ready for use.

    Raises:
        RuntimeError: If DiT handler initialization fails.
    """
    project_root = _get_project_root()
    dit_handler = AceStepHandler()
    llm_handler = LLMHandler()

    # Get configuration from environment variables
    config_path = os.getenv("ACESTEP_CONFIG_PATH", "acestep-v15-turbo")
    device = os.getenv("ACESTEP_DEVICE", "auto")
    use_flash_attention = os.getenv("ACESTEP_USE_FLASH_ATTENTION", "true").lower() in ("1", "true", "yes")
    compile_model = os.getenv("ACESTEP_COMPILE_MODEL", "false").lower() in ("1", "true", "yes")
    offload_to_cpu = os.getenv("ACESTEP_OFFLOAD_TO_CPU", "false").lower() in ("1", "true", "yes")
    offload_dit_to_cpu = os.getenv("ACESTEP_OFFLOAD_DIT_TO_CPU", "false").lower() in ("1", "true", "yes")

    # Initialize DiT handler
    logger.info(f"Initializing DiT model: {config_path} on {device}")
    status_msg, ok = dit_handler.initialize_service(
        project_root=project_root,
        config_path=config_path,
        device=device,
        use_flash_attention=use_flash_attention,
        compile_model=compile_model,
        offload_to_cpu=offload_to_cpu,
        offload_dit_to_cpu=offload_dit_to_cpu,
    )
    if not ok:
        raise RuntimeError(f"DiT initialization failed: {status_msg}")
    logger.info("DiT model loaded successfully")

    # Initialize LLM handler (optional, for CoT reasoning)
    checkpoint_dir = os.path.join(project_root, "checkpoints")
    lm_model_path = os.getenv("ACESTEP_LM_MODEL_PATH", "acestep-5Hz-lm-0.6B")
    backend = os.getenv("ACESTEP_LM_BACKEND", "vllm")
    lm_offload = os.getenv("ACESTEP_LM_OFFLOAD_TO_CPU", "false").lower() in ("1", "true", "yes")

    try:
        lm_status, lm_ok = llm_handler.initialize(
            checkpoint_dir=checkpoint_dir,
            lm_model_path=lm_model_path,
            backend=backend,
            device=device,
            offload_to_cpu=lm_offload,
            dtype=None,
        )
        if lm_ok:
            logger.info(f"LLM model loaded: {lm_model_path}")
        else:
            logger.warning(f"LLM initialization failed: {lm_status}")
    except Exception as e:
        logger.warning(f"LLM initialization error: {e}")

    return dit_handler, llm_handler


def _send_progress_update(
    callback_url: str | None,
    payload: Dict[str, Any],
) -> None:
    """Send a progress update to an external callback URL if provided.

    This is intended to be used by an external FastAPI (or any HTTP) service
    that wants to track RunPod job progress. The client should pass a
    ``callback_url`` field in the RunPod job ``input`` payload.
    """
    if not callback_url:
        return

    try:
        data = json.dumps(payload).encode("utf-8")
        request = Request(
            callback_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urlopen(request, timeout=5)
    except URLError as e:
        logger.warning(f"Failed to send progress update to {callback_url}: {e}")
    except Exception as e:  # pragma: no cover - defensive logging only
        logger.warning(f"Unexpected error when sending progress update: {e}")


# Initialize handlers at module load time
# This ensures models are loaded once and reused across requests
try:
    _DIT_HANDLER, _LLM_HANDLER = _initialize_handlers()
    logger.info("Handlers initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize handlers: {e}")
    _DIT_HANDLER = None
    _LLM_HANDLER = None


def generate_music_job(job: Dict[str, Any]) -> Dict[str, Any]:
    """Process a RunPod serverless job to generate music.

    Args:
        job: RunPod job dictionary containing input parameters:
            - prompt: Text prompt describing the music (default: "a beautiful melody")
            - duration: Target duration in seconds (default: 30)
            - Additional optional parameters (bpm, key, lyrics, etc.)

    Returns:
        Dictionary with:
            - output_url: Public URL to the generated music file
            - status: "success" or "error"
            - error: Error message if status is "error"
    """
    if _DIT_HANDLER is None:
        return {
            "status": "error",
            "error": "ACE-Step handlers not initialized. Check server logs.",
        }

    try:
        job_input = job.get("input", {})
        job_id = job.get("id") or job.get("job_id")
        callback_url = job_input.get("callback_url")

        # ------------------------------------------------------------------
        # Mode selection (optional): simple vs custom
        # ------------------------------------------------------------------
        # If `mode` is not provided, behave like the oficial acestep-api:
        # - `prompt`/`caption` describe the music
        # - `lyrics` is fully optional (empty or "[Instrumental]" both ok)
        #
        # If `mode` is provided:
        # - "simple": ignore any user-provided lyrics and force instrumental
        # - "custom": require explicit lyrics
        mode = job_input.get("mode")
        prompt = job_input.get("prompt") or job_input.get("caption") or "a beautiful melody"
        caption = job_input.get("caption", prompt)
        duration = job_input.get("duration", 30)

        if mode is None:
            # Default behavior: lyrics is optional, compatible with acestep-api
            lyrics = job_input.get("lyrics", "[Instrumental]")
        elif mode == "simple":
            lyrics = "[Instrumental]"
        elif mode == "custom":
            lyrics = job_input.get("lyrics")
            if not lyrics:
                return {
                    "status": "error",
                    "error": "Custom mode requires 'lyrics' in job input.",
                }
        else:
            return {
                "status": "error",
                "error": f"Invalid mode: {mode}. Use 'simple' or 'custom'.",
            }

        # Create temporary output directory
        output_dir = "/tmp/acestep_output"
        os.makedirs(output_dir, exist_ok=True)

        # Prepare generation parameters
        params = GenerationParams(
            task_type="text2music",
            caption=caption,
            lyrics=lyrics,
            duration=float(duration),
            bpm=job_input.get("bpm"),
            keyscale=job_input.get("key", ""),
            inference_steps=job_input.get("inference_steps", 8),
            guidance_scale=job_input.get("guidance_scale", 7.0),
            seed=job_input.get("seed", -1),
            thinking=job_input.get("thinking", True),
            use_cot_metas=job_input.get("use_cot_metas", True),
            use_cot_caption=job_input.get("use_cot_caption", True),
            use_cot_language=job_input.get("use_cot_language", True),
        )

        config = GenerationConfig(
            batch_size=1,
            use_random_seed=job_input.get("seed", -1) < 0,
            seeds=[job_input.get("seed")] if job_input.get("seed", -1) >= 0 else None,
            audio_format="mp3",  # Use MP3 for smaller file size
        )

        # Generate music
        logger.info(
            f"Generating music (mode={mode}): prompt='{prompt}', duration={duration}s",
        )
        _send_progress_update(
            callback_url,
            {
                "job_id": job_id,
                "status": "generating",
                "progress": 10,
                "mode": mode,
            },
        )
        result = generate_music(
            dit_handler=_DIT_HANDLER,
            llm_handler=_LLM_HANDLER,
            params=params,
            config=config,
            save_dir=output_dir,
        )

        if not result.success:
            error_msg = result.error or "Music generation failed"
            _send_progress_update(
                callback_url,
                {
                    "job_id": job_id,
                    "status": "error",
                    "progress": 100,
                    "error": error_msg,
                },
            )
            return {
                "status": "error",
                "error": error_msg,
            }

        if not result.audios:
            error_msg = "No audio files generated"
            _send_progress_update(
                callback_url,
                {
                    "job_id": job_id,
                    "status": "error",
                    "progress": 100,
                    "error": error_msg,
                },
            )
            return {
                "status": "error",
                "error": error_msg,
            }

        # Get the first generated audio file
        audio_info = result.audios[0]
        audio_path = audio_info.get("path", "")
        if not audio_path or not Path(audio_path).exists():
            return {
                "status": "error",
                "error": f"Generated audio file not found: {audio_path}",
            }

        # Upload to Cloudflare R2
        s3 = boto3.client(
            "s3",
            endpoint_url=os.environ["R2_ENDPOINT"],
            aws_access_key_id=os.environ["R2_ACCESS_KEY"],
            aws_secret_access_key=os.environ["R2_SECRET_KEY"],
            region_name="auto",
        )

        object_key = f"songs/{uuid.uuid4()}.mp3"
        bucket_name = os.environ["R2_BUCKET_NAME"]

        logger.info(f"Uploading to R2: {bucket_name}/{object_key}")
        _send_progress_update(
            callback_url,
            {
                "job_id": job_id,
                "status": "uploading",
                "progress": 80,
                "object_key": object_key,
            },
        )
        s3.upload_file(audio_path, bucket_name, object_key)

        play_url = f"{os.environ['R2_PUBLIC_URL']}/{object_key}"

        # Clean up local file
        try:
            os.remove(audio_path)
        except Exception as e:
            logger.warning(f"Failed to clean up local file {audio_path}: {e}")

        _send_progress_update(
            callback_url,
            {
                "job_id": job_id,
                "status": "success",
                "progress": 100,
                "output_url": play_url,
                "mode": mode,
            },
        )

        return {
            "output_url": play_url,
            "status": "success",
            "mode": mode,
        }

    except KeyError as e:
        error_msg = f"Missing required environment variable: {e}"
        _send_progress_update(
            job.get("input", {}).get("callback_url"),
            {
                "job_id": job.get("id") or job.get("job_id"),
                "status": "error",
                "progress": 100,
                "error": error_msg,
            },
        )
        return {
            "status": "error",
            "error": error_msg,
        }
    except Exception as e:
        logger.exception("Error in generate_music_job")
        _send_progress_update(
            job.get("input", {}).get("callback_url"),
            {
                "job_id": job.get("id") or job.get("job_id"),
                "status": "error",
                "progress": 100,
                "error": str(e),
            },
        )
        return {
            "status": "error",
            "error": str(e),
        }


# Start RunPod serverless handler
if __name__ == "__main__":
    runpod.serverless.start({"handler": generate_music_job})
