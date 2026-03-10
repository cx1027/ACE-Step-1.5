"""RunPod serverless handler for ACE-Step music generation.

This handler processes RunPod serverless jobs to generate music using ACE-Step
and uploads the results to Cloudflare R2 storage.

Supports async concurrent processing for RunPod Serverless with min_worker=0.
"""

import asyncio
import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, Tuple

import runpod

# Try to use httpx for async HTTP, fallback to asyncio.to_thread if not available
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

try:
    from r2_upload import verify_cloudflare_token, upload_file_to_r2, upload_file_to_r2_direct
except ImportError:
    # Fallback to boto3 if r2_upload module is not available
    import boto3
    from botocore.exceptions import ClientError
    r2_upload_available = False
else:
    r2_upload_available = True

from acestep.handler import AceStepHandler
from acestep.inference import GenerationConfig, GenerationParams, generate_music, create_sample
from acestep.llm_inference import LLMHandler
from acestep.api.server_utils import parse_description_hints
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

# Set RunPod volume paths for HuggingFace cache and model storage
os.environ["HF_HOME"] = "/runpod-volume/huggingface"
os.environ["ACESTEP_MODEL_DIR"] = "/runpod-volume/models"


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


async def _send_progress_update(
    callback_url: str | None,
    payload: Dict[str, Any],
) -> None:
    """Send a progress update to an external callback URL if provided.

    This is intended to be used by an external FastAPI (or any HTTP) service
    that wants to track RunPod job progress. The client should pass a
    ``callback_url`` field in the RunPod job ``input`` payload.

    Args:
        callback_url: URL to send progress update to, or None to skip.
        payload: Dictionary containing progress update data.
    """
    if not callback_url:
        return

    try:
        if HTTPX_AVAILABLE:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(callback_url, json=payload)
        else:
            # Fallback to asyncio.to_thread for synchronous urlopen
            from urllib.error import URLError
            from urllib.request import Request, urlopen

            def _sync_send():
                data = json.dumps(payload).encode("utf-8")
                request = Request(
                    callback_url,
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                urlopen(request, timeout=5)

            await asyncio.to_thread(_sync_send)
    except Exception as e:
        logger.warning(f"Failed to send progress update to {callback_url}: {e}")


# Initialize handlers at module load time
# This ensures models are loaded once and reused across requests
try:
    _DIT_HANDLER, _LLM_HANDLER = _initialize_handlers()
    logger.info("Handlers initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize handlers: {e}")
    _DIT_HANDLER = None
    _LLM_HANDLER = None

# Thread pool executor for running blocking operations
_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="acestep-worker")


def adjust_concurrency(current_concurrency: int) -> int:
    """Adjust worker concurrency level based on current load.

    This function is called by RunPod to determine how many concurrent
    requests a single worker can handle. Higher values allow more parallel
    processing within a single worker instance.

    Args:
        current_concurrency: Current concurrency level set by RunPod.

    Returns:
        Desired concurrency level. Default: 2 (allows 2 concurrent requests per worker).
    """
    # Allow 2 concurrent requests per worker by default
    # This can be adjusted via environment variable
    max_concurrency = int(os.environ.get("RUNPOD_MAX_CONCURRENCY", "2"))
    return max(1, min(max_concurrency, 10))  # Clamp between 1 and 10


async def generate_music_job(job: Dict[str, Any]) -> Dict[str, Any]:
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
        # Mode selection: simple, custom, or sample_query
        # ------------------------------------------------------------------
        # 1. Simple Mode (mode="simple"): Force instrumental, ignore user lyrics
        # 2. Custom Mode (mode="custom"): Require explicit lyrics
        # 3. sample_query Mode: Use LLM to generate metadata from natural language query
        #
        # If `mode` is not provided and no `sample_query`, behave like acestep-api:
        # - `prompt`/`caption` describe the music
        # - `lyrics` is fully optional (empty or "[Instrumental]" both ok)
        mode = job_input.get("mode")
        sample_query = job_input.get("sample_query") or job_input.get("sampleQuery") or ""
        has_sample_query = bool(sample_query and sample_query.strip())

        # Check if sample_query mode is requested
        if has_sample_query:
            # sample_query mode: Use LLM to generate complete metadata
            if _LLM_HANDLER is None or not _LLM_HANDLER.llm_initialized:
                return {
                    "status": "error",
                    "error": "sample_query mode requires LLM handler, but it's not initialized.",
                }

            # Parse language and instrumental hints from query
            parsed_language, parsed_instrumental = parse_description_hints(sample_query)

            # Use explicit vocal_language if provided, otherwise use parsed
            vocal_language = job_input.get("vocal_language") or job_input.get("vocalLanguage")
            if vocal_language and vocal_language not in ("en", "unknown", ""):
                sample_language = vocal_language
            else:
                sample_language = parsed_language

            # Get LM parameters
            lm_temperature = job_input.get("lm_temperature") or job_input.get("lmTemperature", 0.85)
            lm_top_p = job_input.get("lm_top_p") or job_input.get("lmTopP")
            lm_top_k = job_input.get("lm_top_k") or job_input.get("lmTopK")
            lm_top_p = lm_top_p if lm_top_p is not None and lm_top_p < 1.0 else None
            lm_top_k = lm_top_k if lm_top_k is not None and lm_top_k > 0 else None

            logger.info(f"Creating sample from query: '{sample_query}' (instrumental={parsed_instrumental}, language={sample_language})")

            # Call create_sample in executor (blocking operation)
            def _blocking_create_sample():
                return create_sample(
                    llm_handler=_LLM_HANDLER,
                    query=sample_query,
                    instrumental=parsed_instrumental,
                    vocal_language=sample_language,
                    temperature=lm_temperature,
                    top_k=lm_top_k,
                    top_p=lm_top_p,
                    use_constrained_decoding=True,
                )

            loop = asyncio.get_running_loop()
            sample_result = await loop.run_in_executor(_EXECUTOR, _blocking_create_sample)

            if not sample_result.success:
                error_msg = sample_result.error or sample_result.status_message or "Failed to create sample from query"
                await _send_progress_update(
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

            # Use generated metadata from sample_result
            caption = sample_result.caption
            lyrics = sample_result.lyrics
            bpm = sample_result.bpm
            keyscale = sample_result.keyscale
            time_signature = sample_result.timesignature
            # Prefer user-provided duration, fallback to sample_result, then default
            duration = job_input.get("duration") or job_input.get("audio_duration") or job_input.get("audioDuration")
            if duration is None:
                duration = sample_result.duration if sample_result.duration else 30
            vocal_language = sample_result.language or vocal_language or "en"

            logger.info(
                f"Sample created: caption='{caption[:50]}...', "
                f"bpm={bpm}, duration={duration}, keyscale={keyscale}, "
                f"language={vocal_language}"
            )

        else:
            # Standard mode: Use provided parameters or defaults
            prompt = job_input.get("prompt") or job_input.get("caption") or "a beautiful melody"
            caption = job_input.get("caption", prompt)
            duration = job_input.get("duration") or job_input.get("audio_duration") or job_input.get("audioDuration", 30)

            if mode is None:
                # Default behavior: lyrics is optional, compatible with acestep-api
                lyrics = job_input.get("lyrics", "[Instrumental]")
            elif mode == "simple":
                # Simple mode: Force instrumental
                lyrics = "[Instrumental]"
            elif mode == "custom":
                # Custom mode: Require explicit lyrics
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

            # Use provided metadata or defaults
            bpm = job_input.get("bpm")
            keyscale = job_input.get("key") or job_input.get("key_scale") or job_input.get("keyscale") or ""
            time_signature = job_input.get("time_signature") or job_input.get("timesignature") or ""
            vocal_language = job_input.get("vocal_language") or job_input.get("vocalLanguage") or "en"

        # Create temporary output directory
        output_dir = "/tmp/acestep_output"
        os.makedirs(output_dir, exist_ok=True)

        # Prepare generation parameters
        params = GenerationParams(
            task_type="text2music",
            caption=caption,
            lyrics=lyrics,
            duration=float(duration),
            bpm=bpm,
            keyscale=keyscale,
            timesignature=time_signature,
            vocal_language=vocal_language,
            inference_steps=job_input.get("inference_steps", 8),
            guidance_scale=job_input.get("guidance_scale", 7.0),
            seed=job_input.get("seed", -1),
            thinking=job_input.get("thinking", True),
            use_cot_metas=job_input.get("use_cot_metas", True) if not has_sample_query else False,
            use_cot_caption=job_input.get("use_cot_caption", True) if not has_sample_query else False,
            use_cot_language=job_input.get("use_cot_language", True) if not has_sample_query else False,
            lm_temperature=job_input.get("lm_temperature") or job_input.get("lmTemperature"),
            lm_cfg_scale=job_input.get("lm_cfg_scale") or job_input.get("lmCfgScale"),
            lm_top_k=job_input.get("lm_top_k") or job_input.get("lmTopK"),
            lm_top_p=job_input.get("lm_top_p") or job_input.get("lmTopP"),
        )

        # Get audio format (support both snake_case and camelCase)
        audio_format = job_input.get("audio_format") or job_input.get("audioFormat", "mp3")
        
        # Get batch size
        batch_size = job_input.get("batch_size") or job_input.get("batchSize", 1)
        
        config = GenerationConfig(
            batch_size=batch_size,
            use_random_seed=job_input.get("seed", -1) < 0,
            seeds=[job_input.get("seed")] if job_input.get("seed", -1) >= 0 else None,
            audio_format=audio_format,
        )

        # Generate music
        if has_sample_query:
            logger.info(
                f"Generating music (sample_query mode): query='{sample_query}', "
                f"caption='{caption[:50]}...', duration={duration}s"
            )
        else:
            logger.info(
                f"Generating music (mode={mode}): prompt='{caption}', duration={duration}s",
            )
        await _send_progress_update(
            callback_url,
            {
                "job_id": job_id,
                "status": "generating",
                "progress": 10,
                "mode": "sample_query" if has_sample_query else mode,
            },
        )

        # Run blocking generate_music in executor
        def _blocking_generate():
            return generate_music(
                dit_handler=_DIT_HANDLER,
                llm_handler=_LLM_HANDLER,
                params=params,
                config=config,
                save_dir=output_dir,
            )

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(_EXECUTOR, _blocking_generate)

        if not result.success:
            error_msg = result.error or "Music generation failed"
            await _send_progress_update(
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
            await _send_progress_update(
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

        # Optionally skip R2 upload in local/dev environments.
        if os.environ.get("DISABLE_R2_UPLOAD", "").lower() in {"1", "true", "yes"}:
            logger.info(
                "[generate_music_job] DISABLE_R2_UPLOAD set — skipping R2 upload and "
                "returning local audio path."
            )
            await _send_progress_update(
                callback_url,
                {
                    "job_id": job_id,
                    "status": "success",
                    "progress": 100,
                    "output_url": audio_path,
                    "mode": "sample_query" if has_sample_query else mode,
                },
            )
            return {
                "output_url": audio_path,
                "status": "success",
                "mode": "sample_query" if has_sample_query else mode,
            }

        # Upload to Cloudflare R2
        try:
            object_key = f"songs/{uuid.uuid4()}.mp3"
            bucket_name = os.environ["R2_BUCKET_NAME"]
            public_url_prefix = os.environ.get("R2_PUBLIC_URL", "")

            logger.info(f"Uploading to R2: {bucket_name}/{object_key}")
            await _send_progress_update(
                callback_url,
                {
                    "job_id": job_id,
                    "status": "uploading",
                    "progress": 80,
                    "object_key": object_key,
                },
            )

            # Determine which upload method to use
            # Priority: S3-compatible API (Method 1) > REST API (Method 2)
            # This allows users to use Method 1 exclusively by only configuring S3 credentials
            s3_endpoint = os.environ.get("R2_ENDPOINT")
            s3_access_key = os.environ.get("R2_ACCESS_KEY")
            s3_secret_key = os.environ.get("R2_SECRET_KEY")
            has_s3_config = s3_endpoint and s3_access_key and s3_secret_key

            account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
            api_token = os.environ.get("CLOUDFLARE_API_TOKEN")
            has_rest_api_config = r2_upload_available and account_id and api_token

            # Prefer S3-compatible API if configured (Method 1)
            if has_s3_config:
                logger.info("Using S3-compatible API for R2 upload (Method 1)")

                def _blocking_upload_s3():
                    import boto3
                    from botocore.exceptions import ClientError

                    s3 = boto3.client(
                        "s3",
                        endpoint_url=s3_endpoint,
                        aws_access_key_id=s3_access_key,
                        aws_secret_access_key=s3_secret_key,
                        region_name="auto",
                    )
                    s3.upload_file(audio_path, bucket_name, object_key)
                    return f"{public_url_prefix}/{object_key}" if public_url_prefix else f"https://{bucket_name}.r2.dev/{object_key}"

                loop = asyncio.get_running_loop()
                play_url = await loop.run_in_executor(_EXECUTOR, _blocking_upload_s3)

                # Clean up local file
                try:
                    os.remove(audio_path)
                except Exception as e:
                    logger.warning(f"Failed to clean up local file {audio_path}: {e}")

                await _send_progress_update(
                    callback_url,
                    {
                        "job_id": job_id,
                        "status": "success",
                        "progress": 100,
                        "output_url": play_url,
                        "mode": "sample_query" if has_sample_query else mode,
                    },
                )

                return {
                    "output_url": play_url,
                    "status": "success",
                    "mode": "sample_query" if has_sample_query else mode,
                }

            # Fallback to REST API if S3-compatible not configured (Method 2)
            elif has_rest_api_config:
                logger.info("Using Cloudflare REST API for R2 upload (Method 2)")
                # Run blocking upload operations in executor
                def _blocking_upload_r2():
                    return upload_file_to_r2(
                        audio_path,
                        bucket_name,
                        object_key,
                        account_id,
                        api_token,
                        public_url_prefix,
                    )

                def _blocking_upload_r2_direct():
                    return upload_file_to_r2_direct(
                        audio_path,
                        bucket_name,
                        object_key,
                        account_id,
                        api_token,
                        public_url_prefix,
                    )

                loop = asyncio.get_running_loop()
                # Try pre-signed URL method first
                success, play_url = await loop.run_in_executor(_EXECUTOR, _blocking_upload_r2)

                # If pre-signed URL method fails, try direct PUT
                if not success:
                    logger.info("Pre-signed URL method failed, trying direct PUT")
                    success, play_url = await loop.run_in_executor(_EXECUTOR, _blocking_upload_r2_direct)

                if success and play_url:
                    # Clean up local file
                    try:
                        os.remove(audio_path)
                    except Exception as e:
                        logger.warning(f"Failed to clean up local file {audio_path}: {e}")

                    await _send_progress_update(
                        callback_url,
                        {
                        "job_id": job_id,
                        "status": "success",
                        "progress": 100,
                        "output_url": play_url,
                        "mode": "sample_query" if has_sample_query else mode,
                    },
                )

                    return {
                        "output_url": play_url,
                        "status": "success",
                        "mode": "sample_query" if has_sample_query else mode,
                    }
                else:
                    # REST API upload failed
                    raise Exception("REST API upload failed")

            else:
                # No valid R2 configuration found
                raise Exception(
                    "No valid R2 configuration found. "
                    "Either set R2_ENDPOINT + R2_ACCESS_KEY + R2_SECRET_KEY (Method 1: S3-compatible) "
                    "or CLOUDFLARE_ACCOUNT_ID + CLOUDFLARE_API_TOKEN (Method 2: REST API)"
                )

        except Exception as upload_error:
            # Check if it's an authentication/authorization error
            error_code = None
            error_msg = str(upload_error).lower()

            # Try to extract error code from ClientError (for boto3 fallback)
            try:
                from botocore.exceptions import ClientError
                import boto3
                if isinstance(upload_error, ClientError):
                    error_code = upload_error.response.get("Error", {}).get("Code", "")
                elif isinstance(upload_error, boto3.exceptions.S3UploadFailedError):
                    if hasattr(upload_error, "last_exception") and isinstance(
                        upload_error.last_exception, ClientError
                    ):
                        error_code = upload_error.last_exception.response.get("Error", {}).get("Code", "")
            except (ImportError, AttributeError):
                pass

            # Check error message for common auth error patterns
            if any(keyword in error_msg for keyword in ["unauthorized", "invalidaccesskeyid", "signaturedoesnotmatch", "401", "403"]):
                error_code = "Unauthorized"

            if error_code in ("Unauthorized", "InvalidAccessKeyId", "SignatureDoesNotMatch") or (
                error_code is None and any(keyword in error_msg for keyword in ["unauthorized", "invalidaccesskeyid", "401", "403"])
            ):
                logger.warning(
                    f"R2 upload failed due to authentication error ({error_code or 'authentication failed'}). "
                    f"Falling back to local file path. Set DISABLE_R2_UPLOAD=1 to skip upload attempts, "
                    f"or configure valid R2 credentials in your .env file."
                )
                # Fall back to returning local path
                await _send_progress_update(
                    callback_url,
                    {
                        "job_id": job_id,
                        "status": "success",
                        "progress": 100,
                        "output_url": audio_path,
                        "mode": "sample_query" if has_sample_query else mode,
                    },
                )
                return {
                    "output_url": audio_path,
                    "status": "success",
                    "mode": "sample_query" if has_sample_query else mode,
                }
            else:
                # Re-raise other upload errors
                raise

    except KeyError as e:
        error_msg = f"Missing required environment variable: {e}"
        await _send_progress_update(
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
        await _send_progress_update(
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
    runpod.serverless.start(
        {
            "handler": generate_music_job,
            "concurrency_modifier": adjust_concurrency,
        }
    )
