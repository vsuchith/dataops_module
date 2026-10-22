# Cursor Implementer Prompt - DataOps Brownfield P1/P2

Copy the prompt below into a new Cursor Agent session. Use
`cursor-composer` as the implementer identity. Codex is the independent gate
reviewer and must not share the implementation session.

````markdown
# IMPLEMENTATION MODE - P1/P2 Analysis - dataops-accelerator-maturity

You are the **P1/P2 analysis implementer** for the brownfield module-lane
engagement `dataops-accelerator-maturity`.

**Implementer identity:** `cursor-composer`
**Independent reviewer:** `codex`
**Workspace root:** `/home/suchithgoud/Downloads/Modular`
**Harness root:** `/home/suchithgoud/Downloads/Modular/harness`
**Brownfield accelerator:** `/home/suchithgoud/Downloads/Modular/dataops_module`

## Mission

Create and complete the P1/P2 harness analysis for maturing `dataops_module`
from a fraud-centered implementation into a generic structured and unstructured
DataOps accelerator while preserving its existing fraud, CVOps, MLOps, and
deployment behavior.

This session ends at a passing **G-A machine preflight** and a review packet for
Codex. It must not perform architecture implementation or approve the gate.

## Hard boundaries

- Do not add or modify runtime code under `dataops_module/src/`.
- Do not move, rename, or delete accelerator packages.
- Do not repair CI, add dependencies, or refactor integrations in P1/P2.
- Do not create `src/` under the harness engagement.
- Do not implement Genera/RAG, EvalPlatform, adapters, platform contracts, or
  SAIL.
- Do not copy platform-contract schemas into the accelerator.
- Do not claim that LLMOps is operational while its pipeline assets remain
  stubs.
- Do not claim L3/L4. The engagement target is L2 adapter-ready.
- Write engagement analysis and evidence only under
  `harness/engagements/modules/dataops-accelerator-maturity/`.
- Treat `dataops_module/docs/DATAOPS_MATURATION_PLAN.md` as the accepted planning
  source for this phase. Do not overwrite it.
- Treat `harness/docs/modular/ACCELERATOR_MATURATION_MASTER_PLAN.md` as the
  cross-repo ownership and sequencing authority. Do not overwrite it.
- Do not approve or reject G-A. Reviewer `codex` records that decision later.

## Initialize safely

From the harness root, first check whether the engagement already exists.
Initialize it only when absent:

```bash
cd /home/suchithgoud/Downloads/Modular/harness
test -f engagements/modules/dataops-accelerator-maturity/engagement.json || \
  python3 tools/harness.py init dataops-accelerator-maturity \
    --kind module --maturity-target L2
```

Do not reinitialize or overwrite an existing engagement.

## Mandatory read order

### 1. Cross-program architecture

- `docs/modular/ACCELERATOR_MATURATION_MASTER_PLAN.md`
- `docs/modular/ACCELERATOR_MATURATION_INDEPENDENT_REVIEW_2026-07-30.md`
- `docs/modular/MODULE_INDEPENDENCE_CONTRACT.md`
- `docs/modular/ACCELERATOR_AS_MODULE_PROPOSAL.md`

Pay particular attention to:

- inter-accelerator versus intra-accelerator modularity;
- canonical document elements versus Genera retrieval chunks;
- EvalPlatform evidence, profile/M6 policy, DataOps promotion, and Genera
  activation as four separate responsibilities;
- accelerator maturation before adapters and SAIL;
- the future artifact-reference contract and distributable schema bundle.

### 2. Accepted DataOps plan

- `../dataops_module/docs/DATAOPS_MATURATION_PLAN.md`
- `../dataops_module/docs/GENERA_LLMOPS_BOUNDARY_ANALYSIS.md`
- `../genera/docs/refactor/RAG_MODULE_ARCHITECTURE_PROPOSAL.md` (index,
  ingestion-mode, and access-control sections)
- `../genera/docs/refactor/RAG_MODULE_ARCHITECTURE_OBSERVATIONS.md`

Pay particular attention to:

- architectural decisions;
- scope and responsibility model;
- target native types and ports;
- integration strategy and authoritative ownership;
- compatibility rules;
- P1/P2 deliverables and G-A exit;
- maturity target and non-goals.

### 3. Harness rules

- `execution/GATE_PROTOCOL.md`
- `knowledge/guides/PORTABLE_ENGAGEMENT_LANES.md`
- `knowledge/guides/SDLC.md` (P1/P2 and G-A)
- `HARNESS_CORE.md` (three planes and lifecycle)

### 4. Brownfield accelerator evidence

- `../dataops_module/README.md`
- `../dataops_module/pyproject.toml`
- `../dataops_module/.github/workflows/ci.yml`
- `../dataops_module/src/core/config/settings.py`
- `../dataops_module/src/core/config/domain_configs.py`
- `../dataops_module/src/core/api/models.py`
- `../dataops_module/src/core/lineage/tracker.py`
- `../dataops_module/src/core/monitoring/metrics.py`
- `../dataops_module/src/core/resources/connections.py`
- `../dataops_module/src/pipelines/__init__.py`
- `../dataops_module/src/mlops/`
- `../dataops_module/src/cvops/`
- `../dataops_module/src/llmops/pipelines/definitions.py`
- `../dataops_module/config/`
- `../dataops_module/feature_registry/`
- `../dataops_module/deploy/`
- `../dataops_module/tests/`
- `../dataops_module/Architecture_Dia/`

Read representative implementation files rather than assuming README claims are
true. Record file evidence for every maturity conclusion.

## Required P1/P2 artifacts

Complete the scaffolded G-A documents and add the brownfield evidence documents:

1. `brd/BRIEF.md`
2. `docs/BRD_ANALYSIS.md`
3. `docs/DOMAIN_MODEL.md`
4. `docs/INTEGRATION_MAP.md`
5. `docs/DEPLOYMENT_PROFILE.md`
6. `docs/BROWNFIELD_INVENTORY.md`
7. `docs/COMPATIBILITY_INVENTORY.md`
8. `docs/OPERATIONAL_BASELINE.md`
9. `docs/CAPABILITY_MATURITY_MATRIX.md`
10. `docs/MODULE_CHARTER.md` as a P2 draft with purpose, native boundary,
    ownership, L2 target, and non-goals

Remove all unfilled `{{...}}` placeholders from required G-A documents.

## Required analysis content

### Problem and scope

- Define DataOps as artifact/dataset lifecycle, ingestion, versioning, quality,
  lineage, promotion, and observability.
- Separate generic DataOps from MLOps, CVOps, and LLMOps capability packs.
- State that fraud detection becomes a compatibility profile/example.
- Define LLMOps as the canonical multimodal corpus factory and
  derived-artifact execution/lifecycle owner.
- Keep Genera-owned retrieval chunking, contextualization, index projection,
  retrieval/generation, and EvalPlatform scoring outside this engagement.
- State that a future multimodal RAG profile binds an immutable
  `CorpusVersionRef` to a Genera-owned index-build recipe.

### Brownfield inventory

- Map source packages, APIs, pipelines, resources, configuration, deployments,
  scripts, notebooks, and tests.
- Identify public imports, environment variables, `PIPELINE_MODE` values,
  Compose entry points, ports, and API endpoints that need compatibility.
- Identify fraud-specific assumptions by subsystem. Do not propose a global
  rename.
- Identify oversized/provider-aggregating modules and optional-import behavior.

### Domain model

At minimum analyze:

- `ArtifactRef`
- `DatasetRef` and `DatasetVersion`
- `PipelineRun`
- `QualityReport`
- `LineageEdge`
- `PromotionRequest`
- `ModelRef`
- `FeatureSetRef`
- `AnnotationSetRef`
- `CorpusVersionRef`
- `DocumentManifestRef`
- `ElementSetRef`
- `DerivedArtifactRef`, including recorded embedding/index artifacts whose
  semantics remain owned by the producer recipe

Distinguish stable generic fields from structured, CV, and LLM extensions.
For retrieval chunks, embeddings, and indexes, distinguish generic
lifecycle/execution metadata from Genera-owned semantics. LLMOps must not own
Genera's retrieval recipe merely because it executes an offline build.
This is analysis, not a final schema implementation.

### Integration map

For every integration, document:

- authoritative owner;
- native input/output;
- identifiers and version pins;
- consistency/transaction boundary;
- correlation and idempotency;
- timeout, retry, replay, dead-letter, and partial-failure behavior;
- offline test double;
- real-provider smoke path;
- observability and security concerns;
- current evidence and known gap.

Cover at minimum:

- MinIO, LakeFS, Iceberg, Nessie, and Trino;
- Dagster and DataOps application services;
- MySQL, Debezium, Kafka, ksqlDB, and Redis;
- Feast, Trino, Redis, MLflow, and LakeFS lineage;
- Label Studio and CVOps annotation exports;
- MLflow/LiteLLM and LLMOps artifacts;
- Prometheus/Grafana;
- deterministic local filesystem plus SQLite/DuckDB reference backend;
- future Genera corpus/index handoff, Genera online RAG, EvalPlatform, M1, M2,
  M8, and platform-contract adapters.

For the Genera boundary, explicitly separate:

- DataOps/LLMOps canonical corpus preparation;
- Genera offline RAG index construction;
- Genera online query serving;
- EvalPlatform evaluation evidence;
- profile/M6 promotion policy;
- DataOps promotion record and Genera technical activation;
- profile-owned version pins and thresholds.

Mark the LakeFS/Iceberg/Nessie consistency model as a required G-B ADR unless
the existing repository already resolves it unambiguously.

### Deployment profile

Analyze current and target profiles:

- `local-lite`
- `core`
- `structured`
- `fraud`
- `cvops`
- `llmops`
- `combined`

For each profile, name dependencies, health/readiness expectations, offline
availability, and minimum executable acceptance path. Do not mark current
LLMOps as operational merely because LiteLLM or MLflow starts.

### Operational baseline

Run only non-destructive checks available in the current environment. Candidate
checks include:

```bash
cd /home/suchithgoud/Downloads/Modular/dataops_module
python3 -m pytest tests/unit -q
python3 -m pytest tests/integration -q
docker compose -f deploy/docker/compose/docker-compose.core.yml config
docker compose -f deploy/docker/compose/docker-compose.core.yml \
  -f deploy/docker/compose/docker-compose.fraud.yml config
docker compose -f deploy/docker/compose/docker-compose.core.yml \
  -f deploy/docker/compose/docker-compose.cv.yml config
docker compose -f deploy/docker/compose/docker-compose.core.yml \
  -f deploy/docker/compose/docker-compose.litellm.yml config
```

Do not install packages or start the full stack merely to make P2 look green.
Record each command as PASS, FAIL, or NOT RUN with the exact reason. Missing
tools/dependencies are baseline findings, not permission to weaken checks.
Never use `|| true` in evidence commands.

### Capability maturity matrix

Assess DataOps core, structured DataOps, MLOps/fraud, CVOps, LLMOps,
observability, security, deployment, and test automation independently.
Separate:

- implemented;
- configured but unverified;
- stubbed;
- absent;
- operationally evidenced.

Do not convert stack complexity or README statements into a maturity claim.

### Open questions

Classify every question as:

- P0: blocks G-A;
- P1: must be resolved by G-B ADR/plan;
- P2: may be resolved during a named execution stage.

Before requesting G-A review, there must be no unresolved P0 question. Do not
hide blockers in prose.

## Required G-A checks

From the harness root:

```bash
cd /home/suchithgoud/Downloads/Modular/harness
python3 tools/harness.py validate \
  --engagement modules/dataops-accelerator-maturity
python3 tools/harness.py verify node G-A \
  --engagement modules/dataops-accelerator-maturity
python3 tools/harness.py gate preflight G-A \
  --engagement modules/dataops-accelerator-maturity
```

If validation, verification, or preflight fails, fix only the P1/P2 analysis
artifacts and rerun the exact failed command. Do not bypass checks.

## Completion requirements

Stop after G-A preflight passes and `checkpoints/gates/G-A/review-packet.md`
exists.

Report:

1. files created or changed;
2. current-state findings by capability;
3. integration ownership decisions and G-B ADR candidates;
4. exact commands and results;
5. remaining P1/P2 questions;
6. confirmation that no runtime source or deployment files were changed;
7. the independent review handoff for `codex`.

Do not approve G-A. Do not begin P3/P4.
````
