"""
LLMOps Pipeline - Large Language Model Operations
Text corpus → Embeddings → RAG/Fine-tuning data (E4 operational)
"""

import os
from pathlib import Path

from dagster import (
    AssetExecutionContext,
    AssetSelection,
    MaterializeResult,
    asset,
    define_asset_job,
)

from src.core.config import LLMOPS_CONFIG
from src.core.resources import LakeFSResource
from src.dataops.integrations.local import LocalBackend
from src.llmops.compatibility.corpus import (
    build_local_index,
    create_finetuning_export,
    generate_embeddings,
    ingest_corpus_documents,
    load_profile_documents,
    publish_corpus_version_ref,
    ref_pin,
    run_corpus_pipeline,
)
from src.llmops.compatibility.settings_bridge import load_reference_corpus_profile


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _backend_root() -> Path:
    return Path(os.getenv("LLMOPS_KERNEL_ROOT", ".dataops-local"))


def _resolve_version(profile, root: Path) -> tuple[str, list]:
    documents = load_profile_documents(root, profile)
    import hashlib
    import json

    from src.dataops.integrations.local.filesystem_store import LocalFilesystemArtifactStore

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
    return f"v-{manifest_digest}", documents


@asset(group_name="llmops_init", description="Initialize LLMOps LakeFS structure")
def llmops_init_lakefs(lakefs: LakeFSResource) -> MaterializeResult:
    """Create LLM data repository."""
    repo = LLMOPS_CONFIG["repo"]
    branch = LLMOPS_CONFIG["branch"]

    lakefs.ensure_repo(repo, f"s3://lakefs/{repo}")
    lakefs.create_branch(repo, branch)

    return MaterializeResult(
        metadata={"repo": repo, "branch": branch, "status": "initialized"}
    )


@asset(
    group_name="llmops_bronze",
    deps=["llmops_init_lakefs"],
    description="Ingest text corpus via kernel ports",
)
def llmops_ingest_corpus(context: AssetExecutionContext) -> MaterializeResult:
    profile = load_reference_corpus_profile()
    root = _repo_root()
    run_id = str(context.run_id) if context.run_id else "llmops-corpus"
    version_id, documents = _resolve_version(profile, root)

    if os.getenv("LLMOPS_KERNEL_CORPUS", "true").lower() in ("1", "true", "yes"):
        backend = LocalBackend.create(_backend_root())
        try:
            metadata = ingest_corpus_documents(
                backend,
                profile,
                documents,
                version_id=version_id,
                run_id=run_id,
            )
        finally:
            backend.close()
    else:
        metadata = run_corpus_pipeline(
            profile,
            documents,
            run_id=run_id,
            version_id=version_id,
            backend_root=_backend_root(),
        )

    context.log.info(
        "Ingested %s documents, %s elements",
        metadata.get("document_count", "0"),
        metadata.get("element_count", "0"),
    )
    return MaterializeResult(
        metadata={
            **metadata,
            "status": "ingested",
            "corpus_version_id": version_id,
        }
    )


@asset(
    group_name="llmops_silver",
    deps=["llmops_ingest_corpus"],
    description="Generate deterministic embeddings",
)
def llmops_generate_embeddings(context: AssetExecutionContext) -> MaterializeResult:
    profile = load_reference_corpus_profile()
    run_id = str(context.run_id) if context.run_id else "llmops-embeddings"
    version_id, _ = _resolve_version(profile, _repo_root())

    backend = LocalBackend.create(_backend_root())
    try:
        metadata = generate_embeddings(
            backend, profile, version_id=version_id, run_id=run_id
        )
    finally:
        backend.close()

    return MaterializeResult(
        metadata={
            **metadata,
            "status": "embedded",
            "corpus_version_id": version_id,
        }
    )


@asset(
    group_name="llmops_silver",
    deps=["llmops_generate_embeddings"],
    description="Materialize local reference index",
)
def llmops_index_vectors(context: AssetExecutionContext) -> MaterializeResult:
    profile = load_reference_corpus_profile()
    run_id = str(context.run_id) if context.run_id else "llmops-index"
    version_id, _ = _resolve_version(profile, _repo_root())

    backend = LocalBackend.create(_backend_root())
    try:
        index_meta = build_local_index(
            backend, profile, version_id=version_id, run_id=run_id
        )
        corpus = profile.dataset("corpus")
        dataset_version = backend.dataset_catalog.get(corpus.corpus_id, version_id)
        ingest_meta = {
            "manifest_ref": ref_pin(f"{corpus.corpus_id}.document_manifest", version_id),
            "element_set_ref": ref_pin(f"{corpus.corpus_id}.element_set", version_id),
            "kernel_quality_report_id": dataset_version.quality_report_id or "",
        }
        embedding_meta = {
            "embedding_artifact_id": f"{corpus.corpus_id}.embeddings",
        }
        handoff_meta = publish_corpus_version_ref(
            backend,
            profile,
            version_id=version_id,
            run_id=run_id,
            ingest_meta=ingest_meta,
            embedding_meta=embedding_meta,
            index_meta=index_meta,
        )
        metadata = {**index_meta, **handoff_meta}
    finally:
        backend.close()

    return MaterializeResult(
        metadata={
            **metadata,
            "status": "indexed",
            "corpus_version_id": version_id,
        }
    )


@asset(
    group_name="llmops_gold",
    deps=["llmops_index_vectors"],
    description="Create fine-tuning dataset export",
)
def llmops_create_finetuning_data(context: AssetExecutionContext) -> MaterializeResult:
    profile = load_reference_corpus_profile()
    run_id = str(context.run_id) if context.run_id else "llmops-finetune"
    version_id, _ = _resolve_version(profile, _repo_root())

    backend = LocalBackend.create(_backend_root())
    try:
        metadata = create_finetuning_export(
            backend, profile, version_id=version_id, run_id=run_id
        )
    finally:
        backend.close()

    return MaterializeResult(
        metadata={
            **metadata,
            "status": "exported",
            "corpus_version_id": version_id,
        }
    )


llmops_full_job = define_asset_job(
    name="llmops_full_pipeline",
    selection=AssetSelection.groups(
        "llmops_init", "llmops_bronze", "llmops_silver", "llmops_gold"
    ),
    description="Full LLMOps corpus pipeline (E4 operational)",
)

LLMOPS_ASSETS = [
    llmops_init_lakefs,
    llmops_ingest_corpus,
    llmops_generate_embeddings,
    llmops_index_vectors,
    llmops_create_finetuning_data,
]

LLMOPS_JOBS = [
    llmops_full_job,
]
