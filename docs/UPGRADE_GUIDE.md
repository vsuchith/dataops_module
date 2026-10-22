# Upgrade Guide

## Version pin

Current release candidate: **2.1.0-rc.1** (`pyproject.toml`).  
Gate **G3 APPROVED** (2026-07-31) — see `docs/RELEASE_NOTES.md` and `docs/PROFILE_EVIDENCE_MATRIX.md`.

## Clean install (offline-first)

```bash
cd dataops_module
RECREATE_VENV=1 INSTALL_CV=1 bash scripts/setup-dev-venv.sh
bash scripts/release-candidate-verify.sh
```

## Profile selection

| Goal | Environment | Entry |
|---|---|---|
| Offline development | none | `LocalBackend` / `PIPELINE_MODE=mlops` |
| Lakehouse stack | Docker | `docker compose -f deploy/docker/compose/docker-compose.core.yml up -d` |
| Fraud end-to-end | core + fraud overlay | add `-f docker-compose.fraud.yml` |
| CV detection | core + cv overlay | add `-f docker-compose.cv.yml` |
| LLM corpus path | local-lite | `profiles/reference_corpus/` fixtures |
| All capabilities | combined | `PIPELINE_MODE=combined` |

## Breaking changes (E4 → E5)

- `CorpusVersionRef` semantics frozen (ADR-008) — do not change handoff schema.
- Promotion now requires explicit consistency pins and authorization (ADR-009, SEC-006).
- Published artifacts are immutable; metadata updates allowed only when content checksum unchanged.

## Rollback

1. Stop deployment (`docker compose down` for stack profiles).
2. Restore previous image tag or git ref.
3. For lakehouse promotion rollback, use `PromotionService.rollback()` with the committed receipt.
   See `docs/adr/ADR-009-enterprise-consistency-supplement.md` for the transaction phases and
   `EnterpriseLakehousePromotionConsistency` for full lakehouse pin validation.

## Verification

```bash
.venv/bin/python -m pytest tests/operational -q -m "not integration"
.venv/bin/python -m pytest tests/contract -q
```

Evidence matrix: `docs/PROFILE_EVIDENCE_MATRIX.md`.
