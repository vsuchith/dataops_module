# Profile Evidence Matrix

Executable acceptance evidence for deployment profiles (`DATAOPS_MATURATION_PLAN` §9).

| Item | Value |
|------|--------|
| **Release** | `2.1.0-rc.1` (`pyproject.toml`) |
| **Maturity target** | **L2 adapter-ready** — not L3 |
| **Gate G3** | **APPROVED** (2026-07-31, codex) |
| **Harness decision** | `harness/engagements/modules/dataops-accelerator-maturity/checkpoints/gates/G3/decision.json` |

## Per-profile minimum evidence

| Profile | Required path (§9) | Evidence module | CI offline | Status |
|---|---|---|---|---|
| `local-lite` | store, resolve, version, quality, lineage, promote | `tests/operational/test_local_lite_operational.py` | yes | **PASS** |
| `core` | Compose config validates | `tests/operational/test_core_operational.py` | yes | **PASS** |
| `structured` | ingest, version, quality, transform, promote | `tests/operational/test_structured_operational.py` | yes | **PASS** |
| `fraud` | train/serve smoke via compatibility | `tests/operational/test_fraud_operational.py` | yes | **PASS** |
| `cvops` | manifest, annotation/dataset version, deterministic stub | `tests/operational/test_cvops_operational.py` | yes | **PASS** |
| `llmops` | corpus → elements → embed → index + lineage | `tests/operational/test_llmops_corpus_pipeline.py` | yes | **PASS** |
| `combined` | all capabilities load without import skips | `tests/operational/test_combined_operational.py` | yes | **PASS** |

### Run full offline matrix

```bash
cd dataops_module
RECREATE_VENV=1 INSTALL_CV=1 bash scripts/setup-dev-venv.sh
.venv/bin/python -m pytest tests/operational -q -m "not integration"
```

Equivalent release verification:

```bash
bash scripts/release-candidate-verify.sh
```

## ADR-009 promotion consistency

| Evidence | Test / artifact | Status |
|---|---|---|
| Compensating local transaction | `test_promotion_consistency.py` (8 tests) | **PASS** |
| Injected lineage failure (no partial state) | `test_promote_lineage_failure_leaves_no_partial_state` | **PASS** |
| Injected audit failure (no partial state) | `test_promote_audit_failure_leaves_no_partial_state` | **PASS** |
| Enterprise pin validation | `test_enterprise_promotion_validates_full_pin_set` | **PASS** |
| SEC-006 authorization (always required) | `test_promote_requires_authorization_always` | **PASS** |
| Metadata bypass guard | `test_put_cannot_rewrite_lifecycle_metadata` | **PASS** |
| Audit events (SEC-007) | `promotion_committed`, `promotion_rolled_back` | **PASS** |
| Transaction supplement | `docs/adr/ADR-009-enterprise-consistency-supplement.md` | **PASS** |

## Genera handoff (ADR-008) — downstream consumer evidence

| Artifact | Path |
|---|---|
| Handoff schema pin | `profiles/reference_corpus/handoff-pins.json` |
| Valid fixture | `tests/contract/fixtures/valid/corpus_version_ref.json` |
| Invalid fixtures | `tests/contract/fixtures/invalid/corpus_version_ref_*.json` |
| Model | `src/llmops/compatibility/handoff.py` (`schema_version == "1.0.0"`) |
| Operational producer | `tests/operational/test_llmops_corpus_pipeline.py` |

Contract regression:

```bash
.venv/bin/python -m pytest tests/contract/test_llmops_handoff_contracts.py -q
```

## Opt-in live smoke (not CI-offline)

| Profile | Path | Notes |
|---|---|---|
| `cvops` | `scripts/g2-cv-api-smoke.sh` | Requires running CV API stack |
| `fraud` | `tests/integration/test_fraud_api_integration.py` | `@pytest.mark.integration` |
| `structured` | `tests/integration/test_structured_ingest.py` | Offline by default; live Trino opt-in |

## CI release gate (`.github/workflows/ci.yml`)

| Job | Policy | Blocks release |
|---|---|---|
| `operational` | `pytest tests/operational -m "not integration"` | yes |
| `security` | `safety check` | yes |
| `image-scan` | Trivy `exit-code: 1` on CRITICAL/HIGH | yes |
| `release-candidate` | `scripts/release-candidate-verify.sh` | yes |
| `all-tests-pass` | needs operational, security, image-scan, release-candidate | yes |

## Deployment profile inventory

| Profile | Compose overlay | Health/readiness |
|---|---|---|
| `local-lite` | none (filesystem backend) | process-level |
| `core` | `docker-compose.core.yml` | MinIO, LakeFS, Nessie, Trino, Redis, Kafka healthchecks |
| `fraud` | `+ docker-compose.fraud.yml` | Fraud API `/health` |
| `cvops` | `+ docker-compose.cv.yml` | CV API `/health` |
| `llmops` | Dagster `PIPELINE_MODE=llmops` | corpus pipeline operational test |
| `combined` | full stack or `PIPELINE_MODE=combined` | characterization + combined operational |

## Related docs

- `docs/RELEASE_NOTES.md` — `2.1.0-rc.1` summary
- `docs/UPGRADE_GUIDE.md` — install, profiles, rollback
- `docs/DATAOPS_MATURATION_PLAN.md` — program authority
