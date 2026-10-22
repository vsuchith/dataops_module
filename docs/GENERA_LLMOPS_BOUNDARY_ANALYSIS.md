# Genera and LLMOps Boundary Analysis

**Status:** Proposed architecture analysis
**Date:** 2026-07-30
**Repositories reviewed:** `genera`, `dataops_module`
**Scope:** Multimodal corpus ingestion, RAG index construction, and online RAG
serving. No runtime implementation is included.

## 1. Verdict

Genera and DataOps/LLMOps currently overlap around document ingestion,
partitioning, chunking, embeddings, and index lifecycle. They should be
restructured, but not by moving the complete Genera ingest pipeline into
LLMOps.

The correct separation has three executable products:

1. **DataOps/LLMOps offline corpus factory**
   acquires, versions, parses, enriches, validates, and publishes canonical
   multimodal corpus artifacts.
2. **Genera offline RAG index builder**
   applies Genera-owned retrieval chunking, contextualization, embedding, and
   index projection recipes to a published corpus version.
3. **Genera online RAG runtime**
   performs query embedding, routing, retrieval, reranking, augmentation,
   generation, grounding, sessions, and API/MCP/UI serving against an activated
   index version.

A **multimodal RAG profile** binds the LLMOps corpus recipe to the Genera index
recipe and runtime configuration. The profile contains configuration, version
pins, acceptance thresholds, and deployment composition. It does not contain
copied ingestion or RAG implementation.

```text
OFFLINE
Sources
  -> DataOps artifact/version services
  -> LLMOps multimodal corpus build
  -> CorpusVersion
  -> Genera RAG index build recipe
  -> RetrievalIndexVersion
  -> evaluation and promotion
  -> active index alias

ONLINE
Query
  -> Genera route/retrieve/rerank
  -> active RetrievalIndexVersion
  -> augment/generate/ground
  -> answer
```

This removes duplicate ingestion without forcing reusable document processing
or RAG-specific retrieval policy into the wrong accelerator.

## 2. Current Genera Design

### 2.1 Existing strengths

- Offline ingest and online query code do not directly import each other.
- Compose already runs ingestion as a one-shot profile separate from the app.
- The PDF path is genuinely multimodal: text, tables, figures, captions, dense
  vectors, image vectors, and sparse vectors.
- Ingest supports PDF hashes, content-derived chunk IDs, delta mode, job
  checkpoints, enrichment jobs, per-paper savepoints, and audit rows.
- Online code has useful separation around routing, retrieval, augmentation,
  grounding, and route-specific handlers.
- Refactor packages for connectors, partitioning, manifests, retrieval,
  augmentation, routing, governance, and adapters already exist.

### 2.2 Important implementation reality

The refactor is compatibility-first rather than complete:

- `rag_ingest.py` is still the authoritative 2,382-line ingest pipeline.
- `rag/ingestion/*` contains DTOs and scheduler/watermark contracts, not the
  production pipeline.
- native image, DOCX, and spreadsheet partitioners fail closed by design;
- the index-manifest migration remains a draft and is not part of the active
  `rag_schema.sql`;
- current PDF ingest writes directly into the tables read by online serving;
- app and ingest use the same Docker image and dependency lock;
- the active CI workflow emphasizes route/evaluation checks and runs only an
  ingest lazy-import test, not a multimodal ingest integration suite.

The architecture documents describe the right direction, but their proposed
offline/online boundary is not yet the operational boundary on disk.

### 2.3 Focused verification performed

The analysis ran dependency-light checks only:

- `python3 _test_ingest_lazy_import.py`: PASS, 1 test.
- `PYTHONPATH=. python3 rag/tests/refactor/_test_phase2_phase7_contracts.py`:
  PASS, 5 tests.
- `PYTHONPATH=. python3 rag/tests/refactor/_test_manifest_contracts.py`:
  PASS, 3 tests.
- `python3 rag/tests/refactor/_test_ingest_cli_contract.py`: command passed but
  its only test skipped because `psycopg` is unavailable in the current
  environment.

Running nested refactor scripts without `PYTHONPATH=.` fails to resolve the
top-level `rag` package. That invocation detail should be normalized in the
future test runner. No full extraction, database, model, Docker, or online
query integration test was run for this analysis.

## 3. Current Genera Flow, Step by Step

| Step | Current implementation | Primary bottleneck | Target owner |
|---|---|---|---|
| 1. Source discovery | `rag_ingest.py::_iter_papers()` expects matching arXiv JSON and PDF files | ArXiv-specific pairing, no live connector/watermark implementation | DataOps/LLMOps |
| 2. Change detection | paper existence, PDF hash, `--delta`, `--force`, ingest job rows | Paper-specific identity; no generic source version, tombstone, or active document manifest | DataOps/LLMOps |
| 3. Metadata registration | sidecar JSON is written to `papers` before chunks | Metadata and RAG storage are coupled; no immutable source artifact reference | DataOps/LLMOps |
| 4. Extraction-profile selection | many CLI flags choose GROBID, Docling, MinerU, Dolphin, Nougat, TATR/OCR, Camelot, pdffigures2, and VLM paths | Option/fallback explosion is embedded in one command | Profile selects; LLMOps executes |
| 5. Text extraction | GROBID/Docling/PyMuPDF/Nougat produce chunk-shaped tuples | Extraction emits RAG-ready chunks before a neutral document/element representation exists | LLMOps canonical elements |
| 6. Section and citation extraction | GROBID plus regex/page heuristics | Useful document intelligence is tied to `paper_id`, page, and Genera chunk assembly | LLMOps canonical elements |
| 7. Figure extraction | pdffigures2 crops figures and table regions to local/shared paths | Local path identity, JVM dependency, no governed artifact reference | LLMOps artifact pipeline |
| 8. Table extraction | Docling primary with GROBID caption patching and optional MinerU/Dolphin/TATR/Camelot/VLM fallbacks | Expensive fallback chain, inconsistent confidence, table creation coupled to RAG DB | LLMOps canonical table artifacts |
| 9. Generic enrichment | OCR and VLM descriptions update text and metadata | Active records are mutated and re-embedded; some refresh errors are swallowed | LLMOps creates a new derived version |
| 10. Canonicalization | `ChunkRow` is assembled directly with Genera fields | No stable `Document -> Element -> Artifact` handoff exists | LLMOps publishes `CorpusVersion` |
| 11. Retrieval chunking | text split, front matter, table compaction, figure caption text, element links | Generic extraction and retrieval tuning are interleaved | Genera index recipe |
| 12. Contextual text | deterministic or LLM-generated retrieval prefix | LLM mode embeds once, regenerates context, then embeds the corpus again | Genera recipe; LLMOps worker executes |
| 13. Dense/image embeddings | TEI/local BGE and CLIP-style embedding | Same code/models/dependencies serve batch and latency-sensitive query paths | Offline LLMOps worker; online Genera query embedder |
| 14. Sparse indexing | Qdrant points are written after Postgres commit | Cross-store update is not atomic; failure leaves repair/reindex work | Genera index builder |
| 15. Persistence | papers, chunks, tables, vectors, jobs, audit, conversations, and sessions share one schema | Offline writes and online state have unclear ownership and DB roles | Split corpus, index, and online schemas |
| 16. Activation | current writes become visible after DB commit; index manifest/alias is still draft | Online queries can observe changing content/index state; rollback is weak | Profile promotion over Genera index manifest |
| 17. Online query embedding | `RAGEngine.embedder` uses the configured corpus embedding family | No enforced binding to the exact built index manifest | Genera online |
| 18. Retrieval | pgvector, FTS/BM25, Qdrant sparse, image, table, citation, fusion, reranking | Active index version is implicit; some compatibility facades remain large | Genera online |
| 19. Routing and augmentation | route classification, handlers, evidence selection, context packing | Large query orchestration surface but correctly RAG-specific | Genera online |
| 20. Generation and grounding | LLM/VLM, citations, NLI, exactness, audit/debug | Evaluation is separate but promotion is not bound to an index release | Genera result + EvalPlatform evidence + profile/M6 policy |

## 4. Main Bottlenecks

### 4.1 Correctness and consistency

1. **No neutral corpus boundary.** Extraction output becomes `ChunkRow` directly,
   so reusable document intelligence cannot be consumed without adopting
   Genera's schema.
2. **No active manifest binding in production.** The manifest DTO and SQL draft
   exist, but the active schema and runtime do not consistently bind queries to
   an immutable index version.
3. **Postgres/Qdrant drift.** Postgres commits before sparse Qdrant sync. The
   ingest stops on a hard sparse failure, but the committed dense/text state
   already exists.
4. **Mutable enrichment.** VLM/OCR enrichment updates chunks and indexes in
   place. A query can observe old/new combinations, and failed embedding refresh
   can leave text and vectors inconsistent.
5. **Model/index mismatch risk.** Runtime configuration compares expected model
   names, but the online query embedder is not selected from a promoted index
   manifest.
6. **Graceful degradation can hide evidence loss.** Broad exception handling
   keeps jobs running but can suppress audit, enrichment, or optional index
   failures.

### 4.2 Performance and resource isolation

1. App and ingest share one large Python image containing UI, PDF parsing,
   OCR/table, model, Java, and GPU-oriented dependencies.
2. Offline ingestion and online serving share TEI, Ollama, Qdrant, Postgres, and
   caches without workload classes or resource isolation.
3. The LLM contextual mode computes initial embeddings and then recomputes all
   embeddings after contextual prefix generation.
4. Table extraction can cascade through several heavy parsers/models for one
   document.
5. Paper-level and modality-level thread pools can oversubscribe CPU/GPU memory
   when heavy extractors also parallelize internally.
6. Figure artifacts are shared through filesystem/volume paths rather than
   immutable object references.

### 4.3 Extensibility

1. Production source discovery is tied to arXiv sidecars.
2. `paper_id`, integer pages, and four chunk types dominate the active schema.
3. Native image/DOCX/XLSX support is contract-only and intentionally disabled.
4. Extractor fallback policy is encoded in `rag_ingest.py` instead of a
   versioned build profile.
5. `rag/db.py`, `rag/vlm.py`, `rag/embed.py`, and sparse indexing combine
   offline and online concerns.

### 4.4 Verification

1. Ingest has useful audit tables but lacks a representative multimodal
   end-to-end CI fixture.
2. Refactor contract tests pass when invoked with the correct repository import
   path, but several are not included in the active CI workflow.
3. The ingest CLI test can skip when `psycopg` is absent, so it does not prove
   extraction, persistence, or index consistency.
4. Existing evaluation is rich for query routing and answering but does not
   gate corpus/index promotion as one versioned release.

## 5. Ownership Split

### 5.1 DataOps core

DataOps owns:

- source and artifact identity;
- immutable original and derived artifact storage;
- checksums, versions, retention, and deletion;
- run records, lineage, quality reports, and promotion records;
- generic scheduling, retries, watermarks, and tombstones;
- object-store, catalog, event, and orchestrator ports.

DataOps does not know Genera routes, retrieval weights, contextual retrieval
prompts, pgvector query SQL, or Qdrant retrieval policy.

### 5.2 LLMOps capability pack

LLMOps owns the reusable offline corpus factory:

- filesystem/object/document-system connectors;
- PDF, image, DOCX, and spreadsheet partitioning;
- text, heading, section, citation, table, figure, OCR, and region extraction;
- deterministic normalization and canonical document/element models;
- extraction confidence, provenance, and quality gates;
- generic VLM/OCR enrichment as versioned derived artifacts;
- batch embedding execution and provider/model run metadata;
- build orchestration, retries, audit, lineage, and corpus release;
- publication of `CorpusVersionRef`, `DocumentManifestRef`,
  `ElementSetRef`, and `ArtifactRef`.

LLMOps may execute RAG chunking/embedding plugins, but it does not own their
retrieval semantics.

### 5.3 Genera offline RAG index builder

Genera retains an offline component because not every offline operation is
generic:

- retrieval-specific chunk recipes;
- section overlap and table/figure chunk projection;
- contextual retrieval prefixes and their prompts;
- element links needed by Genera route handlers;
- dense/sparse/image embedding specification for a Genera index family;
- pgvector/FTS/Qdrant projection and index writer behavior;
- RAG index validation, recall checks, and active alias;
- `RAGIndexManifest` and compatibility with Genera retrieval readers.

The builder consumes an immutable `CorpusVersionRef`; it must not rediscover or
overwrite source documents.

### 5.4 Genera online runtime

Genera online retains:

- query and optional image-query embedding;
- routing and route policy;
- dense, sparse, lexical, image, table, citation, and graph retrieval;
- fusion, reranking, and query correction;
- evidence selection and context packing;
- generation, streaming, grounding, citations, and answer audit;
- sessions, research memory, MCP, API, CLI query, and UI adapters.

Online serving receives read-only access to an activated index. It never parses
documents, runs corpus OCR, writes document embeddings, or rebuilds an index.
Every production query receives an authenticated `AccessContext` and a single
mandatory, fail-closed `AccessFilter`. The same filter must constrain dense,
sparse, lexical, table, figure, citation, deterministic SQL, debug, and export
paths before evidence reaches reranking or context packing. Application-layer
filtering is authoritative across stores; datastore RLS or payload filters are
defense-in-depth.

### 5.5 Profile and EvalPlatform

The profile owns configuration and composition:

- source and access-policy defaults;
- extraction profile and fallback order;
- Genera chunk/index recipe pin;
- embedding, sparse, image, reranker, LLM, and VLM version pins;
- index target/alias;
- offline and online resource profiles;
- quality, retrieval, grounding, latency, and access-control thresholds.

EvalPlatform evaluates a candidate `RetrievalIndexVersion` and returns evidence
plus an evaluation threshold outcome. The profile, and later M6, converts that
evidence into the final promotion policy decision. DataOps validates and records
the authorization and promotion; Genera performs technical activation of the
approved index. EvalPlatform does not own ingestion, index storage, promotion
state, or activation.

## 6. What Can Move from Genera

Movement means extraction behind a versioned contract, followed by compatibility
adapters. It must not mean copying files and creating two owners.

### Move to DataOps/LLMOps after characterization

| Current Genera area | Target |
|---|---|
| `rag/connectors/*` contracts and future implementations | LLMOps connector ports/adapters |
| `rag/ingestion/jobs.py`, `scheduler.py`, `watermarks.py`, `tombstones.py` | DataOps run/watermark/tombstone services |
| `rag/partitioning/*` contracts | LLMOps canonical partitioning contracts |
| generic portions of `rag/pdf_extract.py` and `rag/grobid.py` | LLMOps PDF text/section/citation processors |
| `rag/docling_extract.py`, `mineru_extract.py`, `dolphin_extract.py`, `nougat.py`, `pdffigures2.py`, `table_ocr.py` | LLMOps document-processing integrations |
| generic portions of `rag/ingest/text.py`, `figures.py`, `tables.py`, `sections.py`, `enrichment.py` | LLMOps corpus build stages |
| source hashes, artifact paths, extraction audit, and quality signals | DataOps artifact, lineage, and quality records |

### Split rather than move wholesale

| Current Genera area | Offline part | Genera part |
|---|---|---|
| `rag_ingest.py` | source/job/extraction orchestration moves to LLMOps | compatibility CLI and Genera index-build invocation remain |
| `rag/db.py` | corpus/write/manifests repositories move behind DataOps/LLMOps ports | retrieval readers and online session repositories remain |
| `rag/embed.py` | batch model execution adapters move to LLMOps | query-embedding protocol/client remains online |
| `rag/sparse_retrieval.py` | sparse index writer moves to Genera index builder | sparse retriever remains online |
| `rag/vlm.py` | figure/table description worker moves to LLMOps | query-time visual answer runtime remains Genera |
| `rag/prompts.py` | extraction prompts become versioned LLMOps processor config | routing/generation/contextual-index prompts remain Genera |
| `rag/table_semantics.py` | extraction-time column type/unit/stat inference can move | query intent and table retrieval scoring remain Genera |
| `rag_schema.sql` | corpus/artifact/manifests become separate schema | RAG indexes and online session state remain Genera schemas |

### Remain in Genera

- `rag/query/*`
- `rag/retrieval/*`
- `rag/routing/*`
- `rag/augmentation/*`
- `rag/table_lookup/*`
- query-side `rag/search.py` compatibility facade
- generation, grounding, session, MCP, API, UI, and online observability
- RAG index recipe, writers, manifest compatibility, and active index reader

## 7. Contract Boundary

### 7.1 LLMOps corpus output

```text
CorpusVersionRef
  corpus_id
  version
  source_snapshot
  document_manifest_ref
  element_manifest_ref
  artifact_root_ref
  extraction_profile_id
  processor_versions
  quality_report_ref
  lineage_ref
  security_policy_ref
```

Canonical elements include text, heading, list, table, table cell, figure,
chart, image, OCR block, formula, citation, and metadata. They preserve raw and
normalized values, page/section/bbox, confidence, extraction method, parent
element, artifact references, and security labels.

### 7.2 Genera index-build input

```text
RAGIndexBuildRequest
  corpus_version_ref
  rag_build_recipe_ref
  target_index_family
  previous_index_version optional
  build_mode: full | document_delta | tombstone
```

`rag_build_recipe_ref` pins:

- chunker and contextualization policy;
- text/image embedding models and dimensions;
- sparse model;
- table/figure projection rules;
- element-link rules;
- vector/lexical/index target configuration;
- schema and writer versions.

### 7.3 Genera index-build output

```text
RetrievalIndexVersion
  index_id
  version
  source_corpus_version_ref
  recipe_ref
  dense_alias
  sparse_alias
  image_alias
  table_projection_ref
  document_versions
  build_quality_report_ref
  status: building | validated | active | retired | failed
```

### 7.4 Online binding

Every query records or resolves:

- active `RetrievalIndexVersion`;
- embedding family and model version;
- access policy version;
- RAG runtime profile version;
- trace and audit IDs.

The online query embedder must be constructed from the active manifest rather
than an unrelated environment default.

## 8. Multimodal PDF RAG Profile

Suggested logical profile:

```text
profiles/multimodal-pdf-rag/
  profile.yaml
  sources.yaml
  extraction.yaml
  corpus-quality.yaml
  rag-index-recipe.yaml
  online-runtime.yaml
  deployment.yaml
  acceptance/
```

The profile composes:

```text
DataOps core
  + LLMOps multimodal corpus factory
  + Genera offline index builder
  + Genera online runtime
  + EvalPlatform evaluation evidence
  + profile/M6 promotion policy
  + optional M2 trace export
```

For the current research-paper behavior, profile pins may select:

- arXiv filesystem/sidecar connector;
- GROBID plus Docling extraction;
- pdffigures2 figure crops;
- MinerU/TATR/OCR fallback policy;
- BGE-M3 text embeddings;
- CLIP-style image embeddings;
- Qdrant sparse index;
- Genera section/table/figure chunk recipe;
- Genera route/retrieval/generation defaults.

A different profile can reuse the same LLMOps corpus factory with DOCX,
scanned-image, or object-store sources and a different Genera index recipe.

## 9. Physical Offline/Online Separation

### Offline deployment

- source connector workers;
- DataOps artifact and metadata services;
- LLMOps parser/OCR/VLM workers;
- batch embedding workers;
- Genera index builder;
- candidate index stores/collections;
- quality and evaluation workers;
- profile/M6 promotion-policy controller and DataOps promotion recorder.

Offline workers may scale to zero and use throughput-oriented GPU/CPU pools.

### Online deployment

- Genera query API/MCP/UI;
- low-latency query embedding endpoint;
- reranker;
- LLM/VLM answer endpoints;
- read-only retrieval clients;
- online sessions and caches.

Online instances must not include Java, Ghostscript, Docling, MinerU, OCR/table
models, or corpus-build commands unless a selected online feature explicitly
needs them.

### Shared but role-separated infrastructure

- object storage: offline writes versioned artifacts; online reads governed
  evidence artifacts;
- manifest/catalog database: offline publishes; online reads active bindings;
- retrieval stores: index builder writes candidate versions; online role reads
  active aliases only;
- tracing/metrics: both emit correlated events with separate service names.

Using the same physical Postgres or Qdrant deployment is acceptable initially,
but schemas, credentials, aliases, and write permissions must remain separate.

## 10. Migration Plan

### Phase 0: Freeze Genera ingest behavior

- Add representative multimodal PDF fixtures.
- Characterize text, section, citation, figure, table, element-link, dense,
  image, sparse, and audit outputs.
- Record current CLI/config and Compose compatibility.
- Add an ingest integration command to CI.

### Phase 1: Publish a canonical corpus sidecar

- Define the neutral corpus contracts in DataOps/LLMOps.
- Make existing Genera PDF extraction emit a canonical manifest alongside
  current DB writes.
- Do not change online retrieval or active schema.
- Compare canonical output against current `ChunkRow` inputs.

### Phase 2: Introduce a Genera index-builder boundary

- Extract `CorpusVersionRef -> RetrievalIndexVersion` behind a stable API.
- Split generic elements from Genera retrieval chunks.
- Split dense/sparse/image writers from online retrievers.
- Add candidate index aliases and build validation.

### Phase 3: Move generic corpus execution to LLMOps

- Run the characterized PDF processors under LLMOps orchestration.
- Store originals and derived artifacts through DataOps.
- Preserve `rag_ingest.py` as a compatibility CLI that submits an offline
  build and waits/reports status.
- Keep Genera's index recipe and writer plugin in Genera.

### Phase 4: Activate manifest-based online reads

- Build candidate indexes without changing the active alias.
- Run extraction, retrieval, grounding, and access-control evaluations.
- Apply profile/M6 promotion policy to the evidence.
- Record promotion in DataOps, then atomically activate the approved Genera
  manifest.
- Bind online query embedding to the active manifest.
- Prove rollback to the prior manifest.

### Phase 5: Split deployment and dependencies

- Build separate offline and online images.
- Give online services read-only corpus/index credentials.
- Separate throughput and latency embedding endpoints.
- Remove document-processing dependencies from the online image.

### Phase 6: Add the multimodal RAG profile

- Compose LLMOps, Genera index builder, Genera online, and evaluation.
- Pin every processor/model/recipe contract.
- Prove PDF behavior parity.
- Enable new image/DOCX inputs through profile changes and new fixtures, not
  edits to the Genera online runtime.

## 11. Acceptance Criteria

- One source document is acquired and versioned once, not independently by
  LLMOps and Genera.
- LLMOps publishes a retrieval-neutral canonical corpus version.
- Genera can rebuild two index recipes from the same corpus without reparsing
  source documents.
- Online serving performs no corpus parsing, OCR, VLM description, document
  embedding, or index write.
- Candidate index builds are invisible until promotion.
- A query is bound to one immutable index version and matching query-embedding
  model.
- Postgres, Qdrant, table, image, and artifact projections cannot be promoted
  in a mixed version.
- Enrichment creates a new document/corpus/index version instead of mutating
  active evidence in place.
- Tombstones and access-label changes propagate through corpus and index
  versions.
- Current arXiv multimodal PDF behavior passes parity fixtures.
- Online image size and startup no longer require offline parser/OCR packages.
- The profile contains configuration and pins only; no copied implementation.

## 12. Required Plan Correction

The DataOps maturation plan should not state that LLMOps unconditionally owns
RAG chunk and index semantics. It should state:

- DataOps/LLMOps owns canonical corpus preparation and the lifecycle/execution
  of derived artifacts.
- Genera owns retrieval-specific chunking, contextualization, index projection,
  and online behavior.
- the multimodal RAG profile selects and binds the Genera recipe to the LLMOps
  corpus build;
- EvalPlatform evaluates a candidate Genera index version and returns evidence;
- the profile, and later M6, decides promotion policy;
- DataOps records promotion and Genera activates the approved index.

This correction keeps offline and online separated while also separating
generic offline processing from RAG-specific offline index construction.
