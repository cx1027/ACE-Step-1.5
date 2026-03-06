"""Tests for ``AudioCodesMixin`` audio-code decoding behavior."""

from contextlib import contextmanager
from types import SimpleNamespace
import unittest
from unittest import mock

import torch

from acestep.core.generation.handler import audio_codes as audio_codes_mod


AudioCodesMixin = audio_codes_mod.AudioCodesMixin


class _DummyQuantizer:
    """Minimal quantizer stub returning deterministic tensors."""

    def __init__(self):
        self.last_to_device = None

    def get_output_from_indices(self, indices: torch.Tensor) -> torch.Tensor:
        # Return a small CPU tensor; content is irrelevant for this test.
        length = int(indices.numel())
        return torch.zeros(1, max(1, length), 1, dtype=torch.float32)

    def to(self, device: str):
        """Record the requested device and behave like nn.Module.to()."""
        self.last_to_device = device
        return self


class _DummyHost(AudioCodesMixin):
    """Host implementing only the members required by ``_decode_audio_codes_to_latents``."""

    def __init__(self, device: str):
        self.device = device
        self.dtype = torch.float32
        self.model = SimpleNamespace(
            tokenizer=SimpleNamespace(quantizer=_DummyQuantizer()),
            detokenizer=lambda x: x,
        )

    @contextmanager
    def _load_model_context(self, *_args, **_kwargs):
        """No-op context manager used by the mixin."""
        yield


class DecodeAudioCodesToLatentsTests(unittest.TestCase):
    """Verify device-selection behavior for audio-code decoding."""

    def test_mps_uses_cpu_for_indices_and_quantizer(self):
        """On MPS, indices and quantizer are allocated on CPU to avoid MPS OOM."""
        host = _DummyHost(device="mps")
        code_str = "<|audio_code_1|><|audio_code_2|>"

        with mock.patch.object(
            audio_codes_mod.torch, "tensor", wraps=audio_codes_mod.torch.tensor
        ) as mock_tensor:
            latents = host._decode_audio_codes_to_latents(code_str)

        # Decoding should succeed and return a tensor.
        self.assertIsInstance(latents, torch.Tensor)

        # The tensor factory should have been called with device="cpu" when host.device=="mps".
        _args, kwargs = mock_tensor.call_args
        self.assertEqual(kwargs.get("device"), "cpu")

        # Quantizer should have been moved to CPU as well.
        self.assertEqual(host.model.tokenizer.quantizer.last_to_device, "cpu")


if __name__ == "__main__":
    unittest.main()

