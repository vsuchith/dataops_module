"""Profile-driven corpus quality enforcement (E4)."""

from __future__ import annotations

from src.llmops.compatibility.handoff import DocumentManifestRef, ElementSetRef
from src.llmops.compatibility.specs import QualityCheckSpec, ReferenceCorpusProfile


class CorpusQualityError(ValueError):
    """Raised when corpus content fails a configured profile quality check."""


def _check_unique(values: list[str], label: str) -> None:
    if len(values) != len(set(values)):
        raise CorpusQualityError(f"quality check failed: duplicate {label}")


def enforce_profile_quality_checks(
    profile: ReferenceCorpusProfile,
    manifest: DocumentManifestRef,
    element_set: ElementSetRef,
) -> None:
    """Execute configured profile quality checks and fail closed on violations."""
    context = {
        "corpus_non_empty": len(element_set.elements) > 0,
        "unique_source_ids": len({d.source_id for d in manifest.documents})
        == len(manifest.documents),
        "unique_document_checksums": len({d.checksum for d in manifest.documents})
        == len(manifest.documents),
        "unique_element_ids": len({e.element_id for e in element_set.elements})
        == len(element_set.elements),
    }

    for check in profile.quality_checks:
        passed = _evaluate_check(check, context)
        if not passed and check.severity == "critical":
            raise CorpusQualityError(
                f"quality check {check.name!r} failed ({check.rule})"
            )


def _evaluate_check(check: QualityCheckSpec, context: dict[str, bool]) -> bool:
    if check.name in context:
        return context[check.name]
    if check.rule == "count(elements) > 0":
        return context.get("corpus_non_empty", False)
    if check.severity == "critical":
        raise CorpusQualityError(
            f"unsupported critical quality check {check.name!r} ({check.rule})"
        )
    return True
