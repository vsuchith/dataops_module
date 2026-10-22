# Release Notes — dagster-unified-platform (DataOps accelerator)

## 2.1.0-rc.1 — 2026-07-31 (G3 release candidate)

**Maturity:** L2 adapter-ready (engagement `dataops-accelerator-maturity`, gate **G3 APPROVED**).  
**Not claimed:** L3 consumer adoption, [company project] profile, Genera runtime integration.

### Highlights

- **DataOps kernel** (`src/dataops/`): artifact lifecycle, lineage, quality, compensating promotion (ADR-009)
- **Profiles:** `local-lite`, `core`, `structured`, `fraud`, `cvops`, `llmops`, `combined` — executable operational evidence
- **LLMOps handoff freeze:** `CorpusVersionRef` schema `1.0.0` (ADR-008) for Genera G1
- **Security:** SEC-006 authorization on every promotion; SEC-007 audit inside transaction boundary
- **CI release gate:** `security` + `image-scan` (Trivy fail-closed) + `release-candidate` verification

### Upgrade from pre-maturation builds

See `docs/UPGRADE_GUIDE.md`. Verify with:

```bash
RECREATE_VENV=1 INSTALL_CV=1 bash scripts/setup-dev-venv.sh
bash scripts/release-candidate-verify.sh
```

### Genera consumer pin

Handoff fixtures and pins:

- `profiles/reference_corpus/handoff-pins.json`
- `tests/contract/fixtures/valid/corpus_version_ref.json`
- `src/llmops/compatibility/handoff.py` (`HANDOFF_SCHEMA_VERSION = "1.0.0"`)

### Harness evidence

- Gate decision: `harness/engagements/modules/dataops-accelerator-maturity/checkpoints/gates/G3/decision.json`
- Profile matrix: `docs/PROFILE_EVIDENCE_MATRIX.md`

### Known limitations

- Enterprise lakehouse promotion uses local reference + enterprise pin validation; production LakeFS/Iceberg/Nessie drivers are profile integrations behind `PromotionConsistencyPort`.
- Live integration tests remain opt-in (`@pytest.mark.integration`).
- Legacy `src/mlops/` paths remain; use compatibility layer for new kernel-aligned work.

---

## 2.1.0 (pre-RC)

Brownfield baseline before E5 operational hardening and G3 gate evidence.
