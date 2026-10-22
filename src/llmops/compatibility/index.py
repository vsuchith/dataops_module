"""Local reference index adapter (E4)."""

from __future__ import annotations

import json
from typing import Any

from src.llmops.compatibility.embeddings import RECIPE_ID, RECIPE_VERSION

INDEX_RECIPE_ID = "llmops.local-reference-index-v1"
INDEX_RECIPE_VERSION = "1.0.0"


def build_reference_index(
    *,
    corpus_id: str,
    corpus_version: str,
    embedding_records: list[dict[str, object]],
) -> dict[str, Any]:
    if not embedding_records:
        raise ValueError("reference index requires at least one embedding")
    return {
        "index_family": "local_reference",
        "corpus_id": corpus_id,
        "corpus_version": corpus_version,
        "recipe_id": INDEX_RECIPE_ID,
        "recipe_version": INDEX_RECIPE_VERSION,
        "embedding_recipe_id": RECIPE_ID,
        "embedding_recipe_version": RECIPE_VERSION,
        "entries": embedding_records,
        "entry_count": len(embedding_records),
    }


def serialize_index(index: dict[str, Any]) -> bytes:
    return json.dumps(index, sort_keys=True).encode("utf-8")
