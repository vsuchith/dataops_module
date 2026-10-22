# DataOps Accelerator Brownfield Maturation Plan

**Status:** Proposed
**Date:** 2026-07-29
**Repository:** `dataops_module`
**Scope:** DataOps accelerator only. Genera/RAG and EvalPlatform follow as separate
accelerator maturation efforts.

## 1. Objective

Mature `dataops_module` from a fraud-centered MLOps implementation into a
standalone, reusable data and AI operations accelerator that:

- supports structured and unstructured data through the same artifact,
  versioning, lineage, quality, and promotion concepts;
- keeps the current fraud, CVOps, and deployment paths working while migration
  proceeds;
- turns fraud detection into an example profile rather than a core platform
  assumption;
- completes an honest, executable LLMOps data path instead of claiming maturity
  from infrastructure and stubs;
- exposes a stable native boundary that a later
  `adapter-dataops-artifacts` engagement can map to platform contracts;
- remains an independent repository and does not move into harness engagement
  source trees.

This is a brownfield maturation. It is not a rewrite.

## 2. Architectural Decisions

1. **Keep one standalone accelerator repository.** DataOps, MLOps, CVOps, and
   LLMOps share infrastructure and lifecycle concepts, so splitting repositories
   now would add coordination before the common boundary is stable.
2. **Introduce a domain-neutral DataOps kernel.** Artifact identity, dataset
   versioning, lineage, quality, run state, and promotion must not mention fraud,
   images, prompts, or a specific vendor.
3. **Implement capability packs above the kernel.** Structured data, MLOps,
   CVOps, and LLMOps remain separately selectable and testable.
4. **Move use-case assumptions into profiles.** Fraud detection, object
   detection, and a reference corpus become profiles/examples with their own
   configuration and fixtures.
5. **Depend on infrastructure through ports.** LakeFS, Iceberg, Nessie, MinIO,
   Trino, Dagster, Kafka, Feast, MLflow, Label Studio, LiteLLM, and vector stores
   are adapters, not domain primitives.
6. **Preserve compatibility before cleanup.** Existing imports, environment
   names, `PIPELINE_MODE` values, and Compose entry points remain supported until
   replacement paths have parity tests and a documented deprecation release.
7. **Keep platform contracts outside the accelerator core.** The future adapter
   translates native DataOps types to platform envelopes. The accelerator does
   not copy platform schemas or depend on SAIL.
8. **Do not claim LLMOps operational maturity from stubs.** Its acceptance path
   must ingest a corpus, publish canonical multimodal elements, execute
   versioned embedding/index jobs, and expose lineage using deterministic local
   components. Target-specific chunk and index semantics remain owned by the
   consuming accelerator recipe.

## 3. Evidence-Based Current State

### Strengths to preserve

- A real lakehouse stack exists around LakeFS, Iceberg/Nessie, MinIO, Trino,
  Dagster, Kafka, Feast, MLflow, Redis, and monitoring.
- MLOps includes ingestion, Bronze/Gold processing, feature generation,
  retraining, drift/performance checks, promotion, rollback, and serving.
- CVOps includes ingestion, assets, checks, sensors, annotation integration,
  model lineage, API serving, and deployment configuration.
- Deployment is already separated into core, fraud, CV, LiteLLM, monitoring,
  and full Compose overlays.
- Shared configuration, lineage, monitoring, and resource code provide useful
  extraction points for a generic kernel.

### Gaps that prevent a generic maturity claim

- `MLOpsSettings`, API request/response models, scoring, streaming rules,
  feature registry, tests, Helm, dashboards, and deployment defaults contain
  fraud-specific concepts.
- Fraud terminology appears across more than one hundred source, configuration,
  deployment, script, notebook, and test files. A global rename would be unsafe.
- `src/core/resources/connections.py` aggregates many providers in one large
  module, making optional capability boundaries difficult to test.
- CVOps has meaningful implementation but is tightly oriented to YOLO object
  detection and contains large assets/sensors modules.
- LLMOps Dagster assets currently return `status: stub`; document loading,
  embedding generation, vector indexing, and fine-tuning preparation are TODOs.
- Optional imports can silently remove selected capabilities. A requested
  operating mode should fail with an actionable capability error instead.
- CI points lint and coverage at stale `api/` and `pipelines/` paths, Docker
  builds point at stale Dockerfile paths, and security/integration failures are
  allowed to pass.
- The checked environment does not have `pytest` installed, so the current test
  baseline could not be executed locally. This is an environment gap, not a
  conclusion that the tests fail.

**Maturity evidence rule:** README claims, configured CI jobs, deployment
complexity, and service startup are inventory inputs, not maturity evidence.
Claims require executable commands, current-path tests, valid produced
artifacts, and recorded results. See
`harness/docs/modular/ACCELERATOR_MATURATION_INDEPENDENT_REVIEW_2026-07-30.md`.

## 4. Scope and Responsibility Model

| Area | Owns | Does not own |
|---|---|---|
| DataOps kernel | Artifact/dataset identity, versions, lineage, quality, run records, promotion | Model algorithms, prompts, retrieval, domain labels |
| Structured pack | Tables, schemas, partitions, batch/CDC ingestion, transformations | Fraud rules or transaction fields |
| MLOps pack | Features, training runs, model registration, deployment metadata, drift | Fraud as a mandatory use case |
| CVOps pack | Media manifests, annotations, dataset splits, CV training/inference lifecycle | Generic artifact persistence internals |
| LLMOps pack | Corpus ingestion, canonical multimodal extraction, derived-artifact execution, embedding/index job lifecycle, prompt/model run metadata | RAG-specific chunk/index semantics, retrieval, or answer generation |
| Profiles | Fraud, object-detection, and corpus configuration, fixtures, thresholds, role/classification mappings | Shared infrastructure implementations |
| Provider adapters | Vendor SDKs, storage/query/orchestrator integrations | Domain policy |
| Future platform adapter | Native type to platform-envelope mapping | Accelerator internals or SAIL logic |

The later RAG accelerator owns its retrieval-specific chunking,
contextualization, index projection, retrieval strategy, grounding, generation,
and runtime behavior. DataOps LLMOps owns canonical corpus preparation and the
lifecycle/execution of derived artifacts. A multimodal RAG profile binds a
Genera-owned index recipe to an LLMOps corpus version. EvalPlatform executes
scoring and returns evaluation evidence and a threshold outcome. The profile,
and later M6, owns final promotion policy; DataOps validates the resulting
authorization, performs promotion, and records evaluation references and
lineage. See `docs/GENERA_LLMOPS_BOUNDARY_ANALYSIS.md`.

## 5. Target Architecture

```text
Profiles and examples
  fraud_detection | object_detection | reference_corpus
                         |
Capability packs         |
  structured | mlops | cvops | llmops
                         |
DataOps application services
  ingest | validate | transform | version | lineage | promote | observe
                         |
Domain-neutral kernel and ports
  artifacts | datasets | runs | quality | lineage | promotion
                         |
Infrastructure adapters
  local | LakeFS | Iceberg/Nessie | MinIO | Trino | Dagster | Kafka
  Feast | MLflow | Label Studio | vector store | LiteLLM
```

### Core native types

- `ArtifactRef`: id, kind, URI, version, checksum, media type, schema reference,
  producer run, metadata.
- `DatasetRef` and `DatasetVersion`: logical dataset identity, modality,
  physical artifacts, schema/manifest, partitions, parent versions.
- `PipelineRun`: run id, capability, state, inputs, outputs, timestamps, error
  summary.
- `QualityReport`: checks, results, severity, pass/fail state, evidence URI.
- `LineageEdge`: source artifact, target artifact, operation, run id.
- `PromotionRequest`: artifact version, source stage, target stage, policy
  result, approver metadata.
- `ModelRef`, `FeatureSetRef`, `AnnotationSetRef`, `CorpusVersionRef`,
  `DocumentManifestRef`, and `ElementSetRef`: capability-specific references
  built on `ArtifactRef`.
- `DerivedArtifactRef`: records lifecycle and lineage for outputs such as
  embedding sets and indexes. The producing Genera or model recipe owns their
  semantic schema; DataOps does not define retrieval behavior.

### Initial ports

- `ArtifactStore`
- `DatasetCatalog`
- `VersionControl`
- `AnalyticalQueryEngine`
- `EventBus`
- `Orchestrator`
- `LineageStore`
- `DataQualityEvaluator`
- `FeatureStore`
- `ModelRegistry`
- `AnnotationStore`
- `DerivedArtifactExecutor`

Ports should be small and capability-oriented. A single universal storage
interface would hide important semantics and recreate the current resource
aggregation problem.

### Intended package shape

```text
src/
  dataops/
    domain/
    application/
    ports/
    integrations/
    composition/
  mlops/
  cvops/
  llmops/
  compatibility/
  core/                 # compatibility facade during the migration
profiles/
  fraud_detection/
  object_detection/
  reference_corpus/
examples/
tests/
  characterization/
  contract/
  unit/
  integration/
  operational/
```

This is a target shape, not an instruction to move all files in one change.

## 6. Integration Strategy

Integrations are a first-class maturation workstream. The implementation must
not introduce a second owner for an existing lifecycle concept merely to make
the package structure uniform.

### Existing stack ownership

| Integration | Authoritative ownership and required behavior |
|---|---|
| MinIO + LakeFS + Iceberg + Nessie + Trino | MinIO stores objects, LakeFS versions object/data changes, Iceberg owns table snapshots, Nessie owns catalog references, and Trino is the query layer. `ArtifactRef` must retain the identifiers needed to reproduce a read. |
| Dagster + DataOps application services | Dagster schedules and observes application operations. Domain state, promotion policy, and lineage semantics remain outside Dagster assets. |
| MySQL + Debezium + Kafka | CDC boundaries require source identifiers, schema versions, offsets, deduplication, replay, and dead-letter behavior. Kafka is transport, not the permanent record. |
| Kafka + ksqlDB + Redis | ksqlDB derives streaming features and Redis serves transient online state. Durable source and lineage references remain in DataOps stores. |
| Feast + Trino + Redis | Feast owns feature definitions and materialization. Offline and online feature values must link back to dataset and feature-set versions. |
| MLflow + LakeFS | MLflow owns experiment, run, model, and registry lifecycle. LakeFS owns data versions. Lineage connects the model run to immutable training inputs. |
| Label Studio + CVOps | Label Studio is the annotation workspace. Exported annotation sets become immutable, versioned DataOps artifacts. |
| MLflow/LiteLLM + LLMOps | These own model gateway and observability concerns. Canonical corpus and derived-artifact execution/lifecycle remain LLMOps/DataOps responsibilities; consumer recipes own retrieval semantics. |
| Prometheus + Grafana | These own operational metrics and visualization, not durable lineage, audit, or run state. |

The LakeFS/Iceberg/Nessie relationship requires a dedicated ADR. Promotion and
rollback are unsafe until object commits, table snapshots, and catalog references
have an explicit consistency model.

### New internal integrations

1. Add a deterministic local reference backend using filesystem storage plus
   SQLite or DuckDB metadata so contract and operational tests run offline.
2. Connect all capability packs through native artifact references. Structured
   tables, image manifests, annotation sets, corpora, embeddings, indexes,
   features, and models share identity and lineage, not payload schemas.
3. Store unstructured content in object storage and represent collections with
   versioned manifests. Do not put large content in metadata or event messages.
4. Attach tenant/project scope, controlled security labels, retention,
   redaction, and tombstone state to canonical artifacts so every downstream
   projection can fail closed and remove revoked content.
5. Treat vector indexes as rebuildable derivatives. The corpus, chunks,
   embedding provider/model version, and embedding artifacts are authoritative.
6. Normalize structured and unstructured checks into `QualityReport` while
   preserving modality-specific check details.

### Future accelerator and platform integrations

| Consumer | Boundary |
|---|---|
| Genera/RAG | Consumes `CorpusVersionRef`; a Genera-owned offline recipe produces `RetrievalIndexVersion`, while retrieval and generation remain outside DataOps. |
| EvalPlatform | Consumes dataset/model/output references and returns evaluation evidence; DataOps records resulting artifact lineage. |
| M2 tracing | Receives run events through an optional adapter; DataOps core does not import M2. |
| M8 evaluation | Receives evaluation requests through the future adapter, not provider-specific DataOps code. |
| M1 tool registry | May expose approved DataOps operations as tools after authorization and idempotency semantics are defined. |
| platform-contracts | A future release may add artifact envelopes. Native DataOps schemas remain owned here and are mapped by an adapter. |

### Integration acceptance rules

- Name one authoritative owner for every identity, version, state, and policy.
- Define native input/output fixtures and version pins for every boundary.
- Specify correlation IDs, idempotency keys, timeout, retry, replay, and
  partial-failure behavior.
- Keep provider types inside integration adapters.
- Require offline deterministic tests and separately runnable provider smoke
  tests where a real provider is part of the supported profile.
- Characterize existing integrations before wrapping or moving them.
- Do not add a new infrastructure product until the existing stack cannot meet
  a documented requirement.
- Never make a future platform adapter a dependency of the accelerator core.

## 7. Compatibility and Migration Rules

1. Add new generic APIs alongside old fraud APIs.
2. Characterize existing public behavior before changing an import or endpoint.
3. Keep `mlops`, `cvops`, `llmops`, and `combined` as mode aliases during the
   compatibility release.
4. Keep existing Compose overlays executable while new profiles are introduced.
5. Wrap current resources behind ports before splitting their files.
6. Move fraud configuration one vertical slice at a time: source, dataset,
   features, model, serving, streaming, then deployment.
7. Keep compatibility adapters thin and emit deprecation warnings only after
   the replacement path passes parity tests.
8. Use an additive minor release for the first generic boundary. Reserve a
   major release for removal of legacy imports/configuration.
9. Never silently skip a selected capability. Optional unselected integrations
   may be absent; a selected mode must report a clear dependency/configuration
   failure.

## 8. Brownfield Harness Plan

Create a module-lane engagement such as
`engagements/modules/dataops-accelerator-maturity/`. The engagement owns
analysis, decisions, checkpoints, and acceptance evidence. Runtime changes stay
in `dataops_module`.

### P1/P2: Discovery and analysis

Deliver:

- brownfield inventory and dependency map;
- current deployment topology and operational baseline;
- domain model for structured and unstructured artifacts;
- integration map for all providers;
- public API/config/import compatibility inventory;
- capability matrix for DataOps, MLOps, CVOps, and LLMOps;
- prioritized fraud-coupling register;
- open questions with blocking/non-blocking classification.

**G-A exit:** scope and domain boundaries are accepted; no unresolved P0 issue
about ownership, compatibility, or what "operational" means.

### P3/P4: Architecture and implementation planning

Required ADRs:

1. Domain-neutral kernel and capability-pack boundaries.
2. Artifact identity, version, checksum, and lineage semantics.
3. Structured table versus unstructured manifest modeling.
4. Orchestrator independence and Dagster adapter ownership.
5. Compatibility and deprecation policy.
6. Optional capability loading and failure semantics.
7. Deterministic local reference backend.
8. LLMOps canonical corpus boundary, Genera offline index-recipe ownership, and
   profile composition versus the online RAG runtime.
9. LakeFS/Iceberg/Nessie consistency and the enterprise promotion/rollback
   transaction.

Also deliver security, observability, testing, deployment, migration, and
release plans.

**G-B exit:** staged implementation is approved and no package refactor starts
before this gate. If enterprise promotion or rollback appears in an early
implementation stage, ADR 9 must be accepted before G-B. If it is deferred, the
approved plan must limit early execution to the deterministic local backend and
name enterprise promotion/rollback as deferred scope.

### E1: Stabilize and characterize

- Repair CI paths, Dockerfile paths, coverage targets, and false-green jobs.
- Establish lock/reproducible dependency installation for supported Python.
- Add import, configuration, and pipeline-composition characterization tests.
- Validate every existing Compose overlay with `docker compose config`.
- Record current API and profile smoke behavior.
- Add a capability registry so selected modes fail explicitly when incomplete.

**G1 exit:** the brownfield baseline is repeatable and existing operational
paths are protected before structural changes.

### E2.1: Introduce the generic DataOps kernel

- Add core native types and ports.
- Implement deterministic local artifact, catalog, lineage, and quality
  adapters for offline tests.
- Wrap LakeFS, MinIO, Trino, and Dagster through the new ports without changing
  existing behavior.
- Add native contract fixtures for valid and invalid artifacts, versions,
  lineage, quality, and promotion.

### E2.2: Generalize structured DataOps and isolate fraud

- Replace hard-coded transaction/table defaults with `SourceSpec`,
  `DatasetSpec`, `TransformSpec`, and profile configuration.
- Support at least CSV/Parquet batch ingestion and one CDC/event source shape.
- Make schema, primary keys, labels, partitions, quality checks, and promotion
  policies configurable.
- Move fraud defaults and fixtures into `profiles/fraud_detection`.
- Preserve the current fraud API and pipeline through a compatibility layer.
- Make MLOps feature/training/serving services consume generic dataset and
  artifact references.

### E3: Add unstructured data and preserve CVOps

- Add object manifests, media metadata, annotation sets, dataset splits, and
  content checks.
- Migrate one CVOps vertical slice to the generic artifact/version/lineage
  services.
- Split oversized CVOps assets and sensors by lifecycle responsibility.
- Preserve current CV API and Compose profile.
- Prove structured and unstructured artifacts can share version, lineage,
  quality, and promotion services without sharing domain-specific payloads.

**G2 exit:** DataOps structured and unstructured boundaries are integrated;
fraud and CVOps compatibility paths pass.

### E4: Make LLMOps operational

- Implement TXT/Markdown/HTML corpus ingestion first; PDF can be an optional
  parser adapter.
- Add deterministic parsing, canonical document/element partitioning,
  embedding execution, and a local reference index adapter.
- Version corpus, document-manifest, element-set, embedding-set, and reference
  index artifacts with lineage.
- Add rerun/idempotency behavior and quality checks for empty, duplicate, or
  malformed content.
- Keep LiteLLM and hosted embedding providers optional.
- Accept versioned consumer build recipes without defining their semantics in
  LLMOps.
- Expose `CorpusVersionRef` for a future Genera index builder without
  implementing Genera retrieval chunking, index projection, or generation in
  this repository.

**Program D4 / E4 handoff exit:** freeze and version the minimum
`CorpusVersionRef` and canonical element semantics, publish valid/invalid
handoff fixtures, and record the schema/version pin. Genera P1/P2 analysis may
start earlier, but Genera G1 implementation waits for and pins this handoff.

### E5: Operational hardening and release

- Provide `local-lite`, `core`, `structured`, `fraud`, `cvops`, `llmops`, and
  `combined` deployment profiles.
- Add health/readiness checks per selected capability.
- Add secret handling, dependency scanning, image scanning, backup/restore,
  migration, and rollback evidence.
- Publish native API/config documentation and an upgrade guide.
- Produce a versioned release candidate and a clean install/run verification.

**G3/T6 exit:** the accelerator is deployable through documented profiles with
honest maturity evidence. L3 is claimed only after an independent consumer runs
the native contract and operational suites.

## 9. Required Operational Acceptance Matrix

| Profile | Minimum executable evidence |
|---|---|
| `local-lite` | Store, resolve, version, quality-check, lineage, and promote artifacts without external services |
| `structured` | Ingest CSV/Parquet, materialize a versioned table, run quality checks, transform, and promote |
| `fraud` | Existing representative train/serve or documented smoke path passes through compatibility APIs |
| `cvops` | Ingest image manifest, create annotation/dataset version, run a deterministic model stub in CI, and run an opt-in real model smoke |
| `llmops` | Ingest corpus, publish canonical elements, embed deterministically, materialize a local reference index, and verify lineage |
| `combined` | Load all selected capability definitions without hidden import skips or resource collisions |

Each profile needs:

- unit tests for domain/application logic;
- native boundary fixture tests;
- an offline deterministic integration path;
- an opt-in provider integration path where applicable;
- configuration validation;
- health/readiness evidence;
- documented failure and recovery behavior.

Deterministic stubs are acceptable for CI only when they exercise the real
boundary and are paired with a separately runnable provider smoke test. Returning
`status: stub` without producing a valid artifact is not acceptance evidence.

## 10. Maturity Target

The first target is **L2 adapter-ready**:

- stable native boundary;
- generic structured and unstructured fixtures;
- compatibility-tested fraud and CVOps paths;
- executable LLMOps reference path;
- documented deployment profiles;
- no SAIL or platform-specific logic.

Operational deployment evidence may be completed in the same program, but L3
must not be inferred from deployment complexity. L3 requires independent
consumer adoption and repeatable evidence.

Only after the native boundary is stable should
`adapter-dataops-artifacts` map `ArtifactRef`, lineage, and promotion results to
platform contracts. If platform contracts lack an artifact envelope, that
change requires its own compatibility ADR and release.

## 11. Non-Goals

- Rewriting the accelerator from scratch.
- Moving accelerator runtime code under `harness/engagements/`.
- Implementing the Genera/RAG runtime.
- Implementing EvalPlatform scoring or evaluation policy.
- Implementing SAIL or procurement-specific logic.
- Making every provider mandatory.
- Renaming all fraud symbols in one release.
- Replacing proven infrastructure merely to make the architecture look uniform.
- Claiming LLMOps maturity from LiteLLM deployment or MLflow tracing alone.

## 12. Recommended First Action

Start the brownfield harness engagement and complete **P2 only**. The first
review packet should contain:

1. `BROWNFIELD_INVENTORY.md`
2. `BRD_ANALYSIS.md`
3. `DOMAIN_MODEL.md`
4. `INTEGRATION_MAP.md`
5. `DEPLOYMENT_PROFILE.md`
6. `COMPATIBILITY_INVENTORY.md`
7. `OPERATIONAL_BASELINE.md`
8. `CAPABILITY_MATURITY_MATRIX.md`

The first implementation after G-B should be E1 stabilization and
characterization, not package movement. That gives every later refactor a
reliable signal that DataOps, fraud, CVOps, and the selected deployment modes
remain operational.
