"""Audio-code parsing and conversion helpers for handler decomposition."""

import re
import traceback
from typing import List, Optional

import torch
from loguru import logger


class AudioCodesMixin:
    """Mixin containing audio-code parsing and latent conversion helpers.

    Depends on host members:
    - Attributes: ``model``, ``vae``, ``device``, ``dtype``, ``silence_latent``.
    - Methods: ``_load_model_context``, ``process_src_audio``, ``is_silence``,
      ``_encode_audio_to_latents``.
    """

    def _parse_audio_code_string(self, code_str: str) -> List[int]:
        """Extract integer audio codes from tokens like ``<|audio_code_123|>``."""
        if not code_str:
            return []
        try:
            max_audio_code = 63999
            codes = []
            clamped_count = 0
            for x in re.findall(r"<\|audio_code_(\d+)\|>", code_str):
                code_value = int(x)
                clamped_value = max(0, min(code_value, max_audio_code))
                if clamped_value != code_value:
                    clamped_count += 1
                    logger.warning(
                        f"[_parse_audio_code_string] Clamped audio code value from {code_value} to {clamped_value}"
                    )
                codes.append(clamped_value)
            if clamped_count > 0:
                logger.warning(
                    f"[_parse_audio_code_string] Clamped {clamped_count} audio code value(s) "
                    f"to valid range [0, {max_audio_code}]"
                )
            return codes
        except Exception as e:
            logger.debug(f"[_parse_audio_code_string] Failed to parse audio code string: {e}")
            return []

    def _decode_audio_codes_to_latents(self, code_str: str) -> Optional[torch.Tensor]:
        """Convert serialized audio-code string into 25Hz latents."""
        if self.model is None or not hasattr(self.model, "tokenizer") or not hasattr(self.model, "detokenizer"):
            return None

        code_ids = self._parse_audio_code_string(code_str)
        if len(code_ids) == 0:
            return None

        # On MPS, previous diffusion/conditioning work plus MLX allocations can push the
        # allocator close to its high-watermark limit. Proactively clear any cached MPS
        # blocks before allocating tensors for audio-code decoding to avoid spurious
        # OOMs when only a tiny amount of additional memory is actually required.
        empty_cache = getattr(self, "_empty_cache", None)
        if callable(empty_cache):
            try:
                empty_cache()
            except Exception:
                # Cache clearing is a best-effort optimization; failures should not
                # break decoding, and will be surfaced via the subsequent operation.
                logger.debug("[_decode_audio_codes_to_latents] Failed to empty cache before decoding")

        with self._load_model_context("model"):
            quantizer = self.model.tokenizer.quantizer
            detokenizer = self.model.detokenizer

            # On macOS MPS we intentionally keep this tiny ``indices`` tensor and the
            # associated quantizer/codebooks *and* detokenizer on CPU instead of
            # ``self.device`` (``mps``). The MPS allocator uses a high-watermark scheme
            # and can report OOM when attempting to allocate even a few bytes if
            # previous kernels/MLX allocations have fragmented memory. Decoding audio
            # codes is lightweight compared to diffusion, so moving this step to CPU
            # avoids spurious MPS OOM without impacting overall performance. The
            # resulting 25Hz latents remain on CPU and are later moved to the target
            # device by the batching helpers.
            tensor_device = self.device
            try:
                is_mps = str(tensor_device).startswith("mps")
            except Exception:
                is_mps = False

            if is_mps:
                tensor_device = "cpu"
                # Best-effort move of quantizer parameters/codebooks to CPU so that
                # downstream ``vector_quantize_pytorch`` operations (such as stacking
                # codebooks) do not allocate on MPS.
                if hasattr(quantizer, "to"):
                    try:
                        quantizer = quantizer.to("cpu")
                    except Exception:
                        logger.debug(
                            "[_decode_audio_codes_to_latents] Failed to move quantizer to CPU; "
                            "continuing with original device"
                        )

                # Likewise, move the detokenizer to CPU so that its internal Linear
                # layers and embeddings operate entirely on CPU tensors, preventing
                # device-mismatch errors when ``quantized`` is kept on CPU.
                if hasattr(detokenizer, "to"):
                    try:
                        detokenizer = detokenizer.to("cpu")
                    except Exception:
                        logger.debug(
                            "[_decode_audio_codes_to_latents] Failed to move detokenizer to CPU; "
                            "continuing with original device"
                        )

            indices = torch.tensor(code_ids, device=tensor_device, dtype=torch.long)
            indices = indices.unsqueeze(0).unsqueeze(-1)

            quantized = quantizer.get_output_from_indices(indices)
            if quantized.dtype != self.dtype:
                quantized = quantized.to(self.dtype)
            lm_hints_25hz = detokenizer(quantized)
            return lm_hints_25hz

    def convert_src_audio_to_codes(self, audio_file) -> str:
        """Convert uploaded source audio into serialized audio code tokens."""
        if audio_file is None:
            return "❌ Please upload source audio first"
        if self.model is None or self.vae is None:
            return "❌ Model not initialized. Please initialize the service first."

        try:
            processed_audio = self.process_src_audio(audio_file)
            if processed_audio is None:
                return "❌ Failed to process audio file"

            with torch.inference_mode():
                with self._load_model_context("vae"):
                    if self.is_silence(processed_audio.unsqueeze(0)):
                        return "❌ Audio file appears to be silent"
                    latents = self._encode_audio_to_latents(processed_audio)

                attention_mask = torch.ones(latents.shape[0], dtype=torch.bool, device=self.device)
                with self._load_model_context("model"):
                    hidden_states = latents.unsqueeze(0)
                    _, indices, _ = self.model.tokenize(
                        hidden_states, self.silence_latent, attention_mask.unsqueeze(0)
                    )
                    indices_flat = indices.flatten().cpu().tolist()
                    codes_string = "".join([f"<|audio_code_{idx}|>" for idx in indices_flat])
                    logger.info(f"[convert_src_audio_to_codes] Generated {len(indices_flat)} audio codes")
                    return codes_string
        except Exception as e:
            error_msg = f"❌ Error converting audio to codes: {str(e)}\n{traceback.format_exc()}"
            logger.exception("[convert_src_audio_to_codes] Error converting audio to codes")
            return error_msg
