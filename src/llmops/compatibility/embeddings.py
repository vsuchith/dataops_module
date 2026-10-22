"""Deterministic local embeddings for CI and local-lite (E4)."""

from __future__ import annotations

import hashlib
import struct
from typing import Iterable

DEFAULT_EMBEDDING_DIM = 16
RECIPE_ID = "llmops.deterministic-hash-embed-v1"
RECIPE_VERSION = "1.0.0"


def deterministic_embed(text: str, *, dimensions: int = DEFAULT_EMBEDDING_DIM) -> list[float]:
    """Map text to a fixed-size unit vector derived from SHA-256 (no ML deps)."""
    if not text.strip():
        raise ValueError("cannot embed empty text")
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    while len(values) < dimensions:
        chunk = digest[: min(8, len(digest))]
        digest = hashlib.sha256(digest).digest()
        number = struct.unpack(">Q", chunk.ljust(8, b"\0"))[0]
        values.append((number % 10_000) / 10_000.0)
    total = sum(values) or 1.0
    return [v / total for v in values]


def embed_elements(
    elements: Iterable[tuple[str, str]],
    *,
    dimensions: int = DEFAULT_EMBEDDING_DIM,
) -> list[dict[str, object]]:
    """Embed (element_id, content) pairs deterministically."""
    records: list[dict[str, object]] = []
    for element_id, content in elements:
        records.append(
            {
                "element_id": element_id,
                "vector": deterministic_embed(content, dimensions=dimensions),
                "recipe_id": RECIPE_ID,
                "recipe_version": RECIPE_VERSION,
            }
        )
    return records
