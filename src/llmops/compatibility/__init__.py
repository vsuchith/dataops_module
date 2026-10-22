"""LLMOps compatibility layer — corpus factory and Genera handoff (E4)."""

from src.llmops.compatibility.handoff import (
    CorpusVersionRef,
    DerivedArtifactRef,
    DocumentManifestRef,
    ElementSetRef,
    parse_handoff_contract,
)

__all__ = [
    "CorpusVersionRef",
    "DerivedArtifactRef",
    "DocumentManifestRef",
    "ElementSetRef",
    "parse_handoff_contract",
]
