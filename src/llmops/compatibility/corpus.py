"""Corpus ingest via DataOps kernel ports (E4)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Optional

from src.dataops.domain.artifact import ArtifactKind, ArtifactRef, ArtifactState
from src.dataops.domain.dataset import DatasetModality, DatasetVersion
from src.dataops.domain.errors import ArtifactNotFoundError
from src.dataops.domain.lineage import LineageEdge, LineageOperation
from src.dataops.integrations.local import LocalBackend
from src.dataops.integrations.local.filesystem_store import LocalFilesystemArtifactStore
from src.llmops.compatibility.embeddings import RECIPE_ID, RECIPE_VERSION, embed_elements
from src.llmops.compatibility.handoff import (
    CorpusVersionRef,
    DerivedArtifactRef,
    DocumentEntry,
    DocumentManifestRef,
    ElementSetRef,
    HANDOFF_SCHEMA_VERSION,
)
from src.llmops.compatibility.index import (
    INDEX_RECIPE_ID,
    INDEX_RECIPE_VERSION,
    build_reference_index,
    serialize_index,
)
from src.llmops.compatibility.corpus_quality import enforce_profile_quality_checks
from src.llmops.compatibility.parsers import load_documents_from_glob, parse_document
from src.llmops.compatibility.quality_store import load_quality_report, persist_quality_report
from src.llmops.compatibility.specs import DocumentSourceSpec, ReferenceCorpusProfile


def ref_pin(artifact_id: str, version: str) -> str:
    return f"{artifact_id}@{version}"


def corpus_version_id(manifest_checksum: str, element_checksum: str) -> str:
    digest = hashlib.sha256(f"{manifest_checksum}:{element_checksum}".encode()).hexdigest()[:16]
    return f"v-{digest}"


def _put_json_artifact(
    store: LocalFilesystemArtifactStore,
    *,
    artifact_id: str,
    version: str,
    payload: dict[str, Any],
    kind: ArtifactKind,
    producer_run_id: Optional[str],
    metadata: Optional[dict[str, str]] = None,
) -> ArtifactRef:
    content = json.dumps(payload, sort_keys=True).encode("utf-8")
    checksum = LocalFilesystemArtifactStore.checksum(content)
    ref = ArtifactRef(
        artifact_id=artifact_id,
        version=version,
        kind=kind,
        uri=f"file:///{artifact_id}/{version}",
        checksum=checksum,
        state=ArtifactState.VALIDATED,
        media_type="application/json",
        producer_run_id=producer_run_id,
        metadata=metadata or {},
    )
    return store.put(ref, content)


def build_document_manifest(
    profile: ReferenceCorpusProfile,
    documents: list[tuple[Path, str, DocumentSourceSpec]],
    *,
    version_id: str,
) -> DocumentManifestRef:
    entries: list[DocumentEntry] = []
    for path, source_id, source in documents:
        content = path.read_bytes()
        checksum = LocalFilesystemArtifactStore.checksum(content).value
        entries.append(
            DocumentEntry(
                source_id=source_id,
                uri=str(path),
                checksum=checksum,
                media_type=source.format.value,
            )
        )
    corpus = profile.dataset("corpus")
    return DocumentManifestRef(
        manifest_id=f"{corpus.corpus_id}.manifest",
        version=version_id,
        documents=entries,
    )


def build_element_set(
    profile: ReferenceCorpusProfile,
    documents: list[tuple[Path, str, DocumentSourceSpec]],
    *,
    version_id: str,
    manifest_ref: str,
) -> ElementSetRef:
    elements = []
    for path, source_id, source in documents:
        elements.extend(parse_document(path, source, source_id))
    corpus = profile.dataset("corpus")
    return ElementSetRef(
        element_set_id=f"{corpus.corpus_id}.elements",
        version=version_id,
        parent_manifest_ref=manifest_ref,
        extraction_profile=profile.parser_profile,
        elements=elements,
    )


def register_corpus_dataset(
    backend: LocalBackend,
    profile: ReferenceCorpusProfile,
    *,
    artifact_ref: ArtifactRef,
    version_id: str,
    quality_report_id: Optional[str] = None,
) -> DatasetVersion:
    corpus = profile.dataset("corpus")
    version = DatasetVersion(
        dataset_id=corpus.corpus_id,
        version_id=version_id,
        modality=DatasetModality.TEXT_CORPUS,
        physical_artifact_ids=[artifact_ref.artifact_id],
        schema_or_manifest_ref=corpus.schema_ref,
        quality_report_id=quality_report_id,
    )
    return backend.dataset_catalog.register(version)


def record_corpus_lineage(
    backend: LocalBackend,
    *,
    profile: ReferenceCorpusProfile,
    source_artifact_id: str,
    source_version: str,
    target_ref: ArtifactRef,
    run_id: str,
    operation: LineageOperation,
) -> LineageEdge:
    edge = LineageEdge(
        source_artifact_id=source_artifact_id,
        source_version=source_version,
        target_artifact_id=target_ref.artifact_id,
        target_version=target_ref.version,
        operation=operation,
        run_id=run_id,
        metadata={"profile_id": profile.profile_id},
    )
    return backend.lineage_store.record_edge(edge)


def _evaluate_and_persist(
    backend: LocalBackend,
    artifact_ref: ArtifactRef,
    content: bytes,
) -> str:
    report = backend.quality_evaluator.evaluate(artifact_ref, content)
    persist_quality_report(backend, report)
    loaded = load_quality_report(backend, report.report_id, report.artifact_version)
    assert loaded.report_id == report.report_id
    assert loaded.pass_fail == report.pass_fail
    return report.report_id


def ingest_corpus_documents(
    backend: LocalBackend,
    profile: ReferenceCorpusProfile,
    documents: list[tuple[Path, str, DocumentSourceSpec]],
    *,
    version_id: str,
    run_id: str,
    source_artifact_id: str = "llm.raw.documents",
    source_version: str = "v0",
) -> dict[str, str]:
    corpus = profile.dataset("corpus")
    manifest = build_document_manifest(profile, documents, version_id=version_id)
    manifest_ref = ref_pin(manifest.manifest_id, manifest.version)
    element_set = build_element_set(
        profile,
        documents,
        version_id=version_id,
        manifest_ref=manifest_ref,
    )
    enforce_profile_quality_checks(profile, manifest, element_set)

    manifest_artifact = _put_json_artifact(
        backend.artifact_store,
        artifact_id=f"{corpus.corpus_id}.document_manifest",
        version=version_id,
        payload=manifest.model_dump(),
        kind=ArtifactKind.GENERIC,
        producer_run_id=run_id,
        metadata={"document_count": str(len(manifest.documents))},
    )
    _, manifest_bytes = backend.artifact_store.get(
        manifest_artifact.artifact_id, manifest_artifact.version
    )
    manifest_quality_id = _evaluate_and_persist(backend, manifest_artifact, manifest_bytes)

    element_artifact = _put_json_artifact(
        backend.artifact_store,
        artifact_id=f"{corpus.corpus_id}.element_set",
        version=version_id,
        payload=element_set.model_dump(),
        kind=ArtifactKind.GENERIC,
        producer_run_id=run_id,
        metadata={"element_count": str(len(element_set.elements))},
    )
    _, element_bytes = backend.artifact_store.get(element_artifact.artifact_id, element_artifact.version)
    element_quality_id = _evaluate_and_persist(backend, element_artifact, element_bytes)

    handoff_artifact = _put_json_artifact(
        backend.artifact_store,
        artifact_id=corpus.artifact_id,
        version=version_id,
        payload={"manifest_ref": manifest_ref, "element_set_ref": ref_pin(element_set.element_set_id, version_id)},
        kind=ArtifactKind.GENERIC,
        producer_run_id=run_id,
    )
    _, handoff_bytes = backend.artifact_store.get(handoff_artifact.artifact_id, handoff_artifact.version)
    handoff_quality_id = _evaluate_and_persist(backend, handoff_artifact, handoff_bytes)

    dataset_version = register_corpus_dataset(
        backend,
        profile,
        artifact_ref=handoff_artifact,
        version_id=version_id,
        quality_report_id=handoff_quality_id,
    )
    record_corpus_lineage(
        backend,
        profile=profile,
        source_artifact_id=source_artifact_id,
        source_version=source_version,
        target_ref=manifest_artifact,
        run_id=run_id,
        operation=LineageOperation.INGEST,
    )
    record_corpus_lineage(
        backend,
        profile=profile,
        source_artifact_id=manifest_artifact.artifact_id,
        source_version=manifest_artifact.version,
        target_ref=element_artifact,
        run_id=run_id,
        operation=LineageOperation.TRANSFORM,
    )
    record_corpus_lineage(
        backend,
        profile=profile,
        source_artifact_id=element_artifact.artifact_id,
        source_version=element_artifact.version,
        target_ref=handoff_artifact,
        run_id=run_id,
        operation=LineageOperation.INGEST,
    )

    return {
        "kernel_manifest_artifact_id": manifest_artifact.artifact_id,
        "kernel_element_artifact_id": element_artifact.artifact_id,
        "kernel_handoff_artifact_id": handoff_artifact.artifact_id,
        "kernel_dataset_id": dataset_version.dataset_id,
        "kernel_dataset_version": dataset_version.version_id,
        "kernel_quality_report_id": handoff_quality_id,
        "manifest_quality_report_id": manifest_quality_id,
        "element_quality_report_id": element_quality_id,
        "document_count": str(len(manifest.documents)),
        "element_count": str(len(element_set.elements)),
        "manifest_ref": manifest_ref,
        "element_set_ref": ref_pin(element_set.element_set_id, version_id),
    }


def generate_embeddings(
    backend: LocalBackend,
    profile: ReferenceCorpusProfile,
    *,
    version_id: str,
    run_id: str,
) -> dict[str, str]:
    corpus = profile.dataset("corpus")
    element_artifact_id = f"{corpus.corpus_id}.element_set"
    _, element_bytes = backend.artifact_store.get(element_artifact_id, version_id)
    element_payload = json.loads(element_bytes.decode("utf-8"))
    elements = element_payload["elements"]
    embedding_records = embed_elements((e["element_id"], e["content"]) for e in elements)
    payload = {
        "corpus_id": corpus.corpus_id,
        "version": version_id,
        "recipe_id": RECIPE_ID,
        "recipe_version": RECIPE_VERSION,
        "records": embedding_records,
    }
    embedding_artifact = _put_json_artifact(
        backend.artifact_store,
        artifact_id=f"{corpus.corpus_id}.embeddings",
        version=version_id,
        payload=payload,
        kind=ArtifactKind.GENERIC,
        producer_run_id=run_id,
        metadata={"embedding_count": str(len(embedding_records))},
    )
    _, content = backend.artifact_store.get(embedding_artifact.artifact_id, embedding_artifact.version)
    quality_id = _evaluate_and_persist(backend, embedding_artifact, content)
    record_corpus_lineage(
        backend,
        profile=profile,
        source_artifact_id=element_artifact_id,
        source_version=version_id,
        target_ref=embedding_artifact,
        run_id=run_id,
        operation=LineageOperation.EMBED,
    )
    derived = DerivedArtifactRef(
        artifact_id=embedding_artifact.artifact_id,
        version=version_id,
        recipe_id=RECIPE_ID,
        recipe_version=RECIPE_VERSION,
        producer="llmops",
        input_refs=[ref_pin(element_artifact_id, version_id)],
        output_uri=embedding_artifact.uri,
        checksum=embedding_artifact.checksum.value,
        semantic_owner="llmops",
    )
    return {
        "embedding_artifact_id": embedding_artifact.artifact_id,
        "embedding_count": str(len(embedding_records)),
        "embedding_quality_report_id": quality_id,
        "embedding_derived_ref": derived.model_dump_json(),
    }


def build_local_index(
    backend: LocalBackend,
    profile: ReferenceCorpusProfile,
    *,
    version_id: str,
    run_id: str,
) -> dict[str, str]:
    corpus = profile.dataset("corpus")
    embedding_artifact_id = f"{corpus.corpus_id}.embeddings"
    _, embedding_bytes = backend.artifact_store.get(embedding_artifact_id, version_id)
    embedding_payload = json.loads(embedding_bytes.decode("utf-8"))
    index_payload = build_reference_index(
        corpus_id=corpus.corpus_id,
        corpus_version=version_id,
        embedding_records=embedding_payload["records"],
    )
    index_artifact = _put_json_artifact(
        backend.artifact_store,
        artifact_id=f"{corpus.corpus_id}.reference_index",
        version=version_id,
        payload=index_payload,
        kind=ArtifactKind.GENERIC,
        producer_run_id=run_id,
        metadata={"entry_count": str(index_payload["entry_count"])},
    )
    _, content = backend.artifact_store.get(index_artifact.artifact_id, index_artifact.version)
    quality_id = _evaluate_and_persist(backend, index_artifact, content)
    record_corpus_lineage(
        backend,
        profile=profile,
        source_artifact_id=embedding_artifact_id,
        source_version=version_id,
        target_ref=index_artifact,
        run_id=run_id,
        operation=LineageOperation.INDEX,
    )
    derived = DerivedArtifactRef(
        artifact_id=index_artifact.artifact_id,
        version=version_id,
        recipe_id=INDEX_RECIPE_ID,
        recipe_version=INDEX_RECIPE_VERSION,
        producer="llmops",
        input_refs=[ref_pin(embedding_artifact_id, version_id)],
        output_uri=index_artifact.uri,
        checksum=index_artifact.checksum.value,
        semantic_owner="llmops",
    )
    return {
        "index_artifact_id": index_artifact.artifact_id,
        "index_entry_count": str(index_payload["entry_count"]),
        "index_quality_report_id": quality_id,
        "index_derived_ref": derived.model_dump_json(),
    }


def publish_corpus_version_ref(
    backend: LocalBackend,
    profile: ReferenceCorpusProfile,
    *,
    version_id: str,
    run_id: str,
    ingest_meta: dict[str, str],
    embedding_meta: dict[str, str],
    index_meta: dict[str, str],
) -> dict[str, str]:
    corpus = profile.dataset("corpus")
    manifest_checksum = backend.artifact_store.get(
        f"{corpus.corpus_id}.document_manifest", version_id
    )[0].checksum.value
    element_checksum = backend.artifact_store.get(f"{corpus.corpus_id}.element_set", version_id)[0].checksum.value
    checksum = hashlib.sha256(f"{manifest_checksum}:{element_checksum}".encode()).hexdigest()

    handoff = CorpusVersionRef(
        corpus_id=corpus.corpus_id,
        version=version_id,
        schema_version=HANDOFF_SCHEMA_VERSION,
        document_manifest_refs=[ingest_meta["manifest_ref"]],
        element_set_refs=[ingest_meta["element_set_ref"]],
        embedding_set_refs=[ref_pin(embedding_meta["embedding_artifact_id"], version_id)],
        index_ref=ref_pin(index_meta["index_artifact_id"], version_id),
        checksum=checksum,
        parser_profile=profile.parser_profile,
        security_labels=list(profile.security_labels),
        quality_report_id=ingest_meta["kernel_quality_report_id"],
        lineage_run_id=None,
    )
    handoff_artifact_id = f"{corpus.corpus_id}.corpus_version_ref"
    handoff_payload = handoff.model_dump()
    handoff_artifact: ArtifactRef
    try:
        existing_ref, existing_bytes = backend.artifact_store.get(
            handoff_artifact_id,
            version_id,
        )
        existing = CorpusVersionRef.model_validate(json.loads(existing_bytes.decode("utf-8")))
        if existing.checksum == checksum:
            handoff_artifact = existing_ref
        else:
            handoff_artifact = _put_json_artifact(
                backend.artifact_store,
                artifact_id=handoff_artifact_id,
                version=version_id,
                payload=handoff_payload,
                kind=ArtifactKind.GENERIC,
                producer_run_id=run_id,
            )
    except ArtifactNotFoundError:
        handoff_artifact = _put_json_artifact(
            backend.artifact_store,
            artifact_id=handoff_artifact_id,
            version=version_id,
            payload=handoff_payload,
            kind=ArtifactKind.GENERIC,
            producer_run_id=run_id,
        )
    record_corpus_lineage(
        backend,
        profile=profile,
        source_artifact_id=index_meta["index_artifact_id"],
        source_version=version_id,
        target_ref=handoff_artifact,
        run_id=run_id,
        operation=LineageOperation.INGEST,
    )
    return {
        "corpus_version_ref": handoff.model_dump_json(),
        "corpus_checksum": checksum,
        "handoff_artifact_id": handoff_artifact.artifact_id,
    }


def create_finetuning_export(
    backend: LocalBackend,
    profile: ReferenceCorpusProfile,
    *,
    version_id: str,
    run_id: str,
) -> dict[str, str]:
    corpus = profile.dataset("corpus")
    _, element_bytes = backend.artifact_store.get(f"{corpus.corpus_id}.element_set", version_id)
    elements = json.loads(element_bytes.decode("utf-8"))["elements"]
    lines = [
        json.dumps({"instruction": "Summarize", "input": e["content"], "output": e["content"][:120]})
        for e in elements
    ]
    content = "\n".join(lines).encode("utf-8")
    checksum = LocalFilesystemArtifactStore.checksum(content)
    ref = ArtifactRef(
        artifact_id=f"{corpus.corpus_id}.finetuning",
        version=version_id,
        kind=ArtifactKind.GENERIC,
        uri=f"file:///{corpus.corpus_id}.finetuning/{version_id}",
        checksum=checksum,
        state=ArtifactState.VALIDATED,
        media_type="application/x-ndjson",
        producer_run_id=run_id,
        metadata={"training_samples": str(len(lines))},
    )
    stored = backend.artifact_store.put(ref, content)
    record_corpus_lineage(
        backend,
        profile=profile,
        source_artifact_id=f"{corpus.corpus_id}.element_set",
        source_version=version_id,
        target_ref=stored,
        run_id=run_id,
        operation=LineageOperation.TRANSFORM,
    )
    return {"training_samples": str(len(lines)), "finetuning_artifact_id": stored.artifact_id}


def load_profile_documents(
    root: Path,
    profile: ReferenceCorpusProfile,
) -> list[tuple[Path, str, DocumentSourceSpec]]:
    documents: list[tuple[Path, str, DocumentSourceSpec]] = []
    for source in profile.sources:
        for path, source_id in load_documents_from_glob(root, source):
            documents.append((path, source_id, source))
    if not documents:
        raise FileNotFoundError("profile sources produced no documents")
    return documents


def run_corpus_pipeline(
    profile: ReferenceCorpusProfile,
    documents: list[tuple[Path, str, DocumentSourceSpec]],
    *,
    run_id: str,
    version_id: Optional[str] = None,
    backend_root: Optional[Path] = None,
) -> dict[str, str]:
    manifest_digest = hashlib.sha256(
        json.dumps(
            [
                {
                    "path": str(path),
                    "source_id": source_id,
                    "checksum": LocalFilesystemArtifactStore.checksum(path.read_bytes()).value,
                }
                for path, source_id, _ in documents
            ],
            sort_keys=True,
        ).encode()
    ).hexdigest()[:16]
    resolved_version = version_id or f"v-{manifest_digest}"

    backend = LocalBackend.create(backend_root)
    try:
        ingest_meta = ingest_corpus_documents(
            backend,
            profile,
            documents,
            version_id=resolved_version,
            run_id=run_id,
        )
        embedding_meta = generate_embeddings(
            backend, profile, version_id=resolved_version, run_id=run_id
        )
        index_meta = build_local_index(
            backend, profile, version_id=resolved_version, run_id=run_id
        )
        handoff_meta = publish_corpus_version_ref(
            backend,
            profile,
            version_id=resolved_version,
            run_id=run_id,
            ingest_meta=ingest_meta,
            embedding_meta=embedding_meta,
            index_meta=index_meta,
        )
        finetune_meta = create_finetuning_export(
            backend, profile, version_id=resolved_version, run_id=run_id
        )
        result = {**ingest_meta, **embedding_meta, **index_meta, **handoff_meta, **finetune_meta}
        result["corpus_version_id"] = resolved_version
        return result
    finally:
        backend.close()
