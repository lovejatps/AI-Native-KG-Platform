"""Embedding client for vLLM (NVIDIA) based models.

The client reads configuration from ``app.core.config.Settings`` which can be
populated via a ``.env`` file.  Required environment variables (with defaults) are:

```
VLLM_ENDPOINT=https://integrate.api.nvidia.com/v1
VLLM_API_KEY=   # your NVIDIA API key
VLLM_EMBED_MODEL=baai/bge-m3
```

If any of the above are missing or the request fails, the client falls back to
returning a zero‑vector of length ``DEFAULT_DIM`` (768).  This fallback keeps the
rest of the pipeline functional for CI or local development without network
access.
"""

import json
import os
from typing import List

import requests

from .config import get_settings
from .logger import get_logger

DEFAULT_DIM = 768  # matches the Milvus collection dimension

# Module‑level logger
_logger = get_logger(__name__)


class EmbeddingModel:
    def __init__(self):
        self.settings = get_settings()
        self.endpoint = getattr(
            self.settings, "VLLM_ENDPOINT", "https://integrate.api.nvidia.com/v1"
        )
        self.api_key = getattr(self.settings, "VLLM_API_KEY", "")
        self.model = getattr(self.settings, "VLLM_EMBED_MODEL", "baai/bge-m3")
        # Endpoint for embeddings – according to vLLM spec it's /embeddings
        self.url = f"{self.endpoint.rstrip('/')}/embeddings"
        self.dim = DEFAULT_DIM  # ensure dimension is defined for fallback vectors

    """Thin wrapper around the vLLM embedding endpoint.

    Usage::

        embedder = EmbeddingModel()
        vectors = embedder.embed(["text 1", "text 2"])
    """

    def _fallback_vector(self) -> List[float]:
        """Return a zero‑vector of the configured embedding dimension.
        This is used when the remote service cannot be reached.
        """
        return [0.0] * self.dim

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Return a list of embeddings for *texts*.

        The function sends a POST request with JSON payload::

            {"model": "<model>", "input": ["text1", "text2", ...]}

        and expects a response of the form::

            {"data": [{"embedding": [0.1, 0.2, ...]}, ...]}

        If the request fails (network error, non‑200 status, missing fields) a
        list of fallback zero‑vectors of matching length is returned.
        """
        if not self.api_key:
            # No credentials – immediately fallback
            return [self._fallback_vector() for _ in texts]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": self.model, "input": texts}
        try:
            resp = requests.post(self.url, headers=headers, json=payload, timeout=30)
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Embedding request failed with status {resp.status_code}"
                )
            data = resp.json()
            embeddings = [
                item.get("embedding", self._fallback_vector())
                for item in data.get("data", [])
            ]
            # Ensure we always return the same number of vectors as inputs
            if len(embeddings) != len(texts):
                # Pad or truncate to match input length
                embeddings = (embeddings + [self._fallback_vector()] * len(texts))[
                    : len(texts)
                ]
            return embeddings
        except Exception as e:
            # Log the error via the module logger
            _logger.error(f"[EmbeddingModel] fallback due to error: {e}")
            return [self._fallback_vector() for _ in texts]


# Convenience function for quick usage
def embed_texts(texts: List[str]) -> List[List[float]]:
    return EmbeddingModel().embed(texts)
