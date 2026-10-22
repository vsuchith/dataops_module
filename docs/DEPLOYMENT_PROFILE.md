# Deployment Profile Reference (dataops_module)

Current profile inventory aligned with engagement `DEPLOYMENT_PROFILE.md` (E5 refresh).

| Profile | Status | Evidence |
|---|---|---|
| `local-lite` | **Implemented** — `LocalBackend` (ADR-007) | `tests/operational/test_local_lite_operational.py` |
| `core` | **Configured** — Compose validates | `tests/operational/test_core_operational.py` |
| `structured` | **Implemented** — generic ingest via profile config | `tests/operational/test_structured_operational.py` |
| `fraud` | **Implemented** — compatibility APIs + profile | `tests/operational/test_fraud_operational.py` |
| `cvops` | **Implemented** — manifest ingest + CV API | `tests/operational/test_cvops_operational.py` |
| `llmops` | **Operational** — corpus pipeline (E4) | `tests/operational/test_llmops_corpus_pipeline.py` |
| `combined` | **Configured** — fail-closed capability registry | `tests/operational/test_combined_operational.py` |

Full matrix: `docs/PROFILE_EVIDENCE_MATRIX.md`.

## llmops (updated E5)

- Dagster assets no longer stub on acceptance path (E4 closed).
- Deterministic corpus → elements → embed → local index with `CorpusVersionRef` handoff.
- Optional LiteLLM overlay: `docker-compose.litellm.yml`.

## Health / readiness

- **local-lite:** no external deps; artifact store + catalog in-process.
- **core:** infrastructure healthchecks in `docker-compose.core.yml`.
- **fraud / cvops:** API `/health` and `/metrics` endpoints documented in engagement ARCHITECTURE.
