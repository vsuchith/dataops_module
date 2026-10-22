"""
LLMOps Pipelines Module
=======================

Operational Dagster pipelines for the reference corpus profile (E4):
corpus ingest → deterministic embeddings → local reference index → handoff.

Usage:
    from src.llmops.pipelines import LLMOPS_ASSETS, LLMOPS_JOBS
"""

from src.llmops.pipelines.definitions import (
    llmops_init_lakefs,
    llmops_ingest_corpus,
    llmops_generate_embeddings,
    llmops_index_vectors,
    llmops_create_finetuning_data,
    llmops_full_job,
    LLMOPS_ASSETS,
    LLMOPS_JOBS,
)

__all__ = [
    "llmops_init_lakefs",
    "llmops_ingest_corpus",
    "llmops_generate_embeddings",
    "llmops_index_vectors",
    "llmops_create_finetuning_data",
    "llmops_full_job",
    "LLMOPS_ASSETS",
    "LLMOPS_JOBS",
]
