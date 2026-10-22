# ADR-009 Enterprise Consistency Supplement

**Status:** Accepted (E5 G3 remediation)  
**Date:** 2026-07-31  
**Parent:** `harness/.../docs/adr/ADR-009-lakehouse-consistency-deferred.md`

## Context

ADR-009 requires an explicit lakehouse promotion transaction boundary for E5.
The local reference backend must prove compensating semantics before any
production LakeFS/Iceberg/Nessie adapter claims operational maturity.

## Decision

### Transaction phases

Every promotion executes these phases in order:

1. **Validate** — artifact state, consistency pins, authorization (SEC-006).
2. **Snapshot** — capture artifact head + prior checkpoint.
3. **Lineage** — record `PROMOTE` edge with `run_id` and `correlation_id`.
4. **Checkpoint** — persist `ConsistencyCheckpoint` pins.
5. **Publish** — commit lifecycle metadata (`state=published`, `provider_replay`).
6. **Audit** — append SEC-007 events (final phase; failure triggers compensation).

On failure after phase 3, the implementation **compensates** by deleting the
lineage edge (when supported) and restoring the snapshot artifact + checkpoint.
A `FAILED` receipt must leave **no partial published state**, including when audit
persistence fails after lineage/checkpoint/publish.

### Implementations

| Profile | Class | Path |
|---|---|---|
| `local-lite` | `LocalPromotionConsistency` | `src/dataops/integrations/local/promotion_consistency.py` |
| `core` / lakehouse | `EnterpriseLakehousePromotionConsistency` | `src/dataops/integrations/enterprise/lakehouse_promotion.py` |

The enterprise adapter validates the full pin set (`lakefs_repo`, `lakefs_branch`,
`lakefs_commit`, `iceberg_snapshot`, `nessie_ref`) and delegates to the same
compensating transaction used offline. Production store coordination plugs in
behind `PromotionConsistencyPort` without changing `PromotionService`.

### Authorization and immutability

- `PromotionService` requires `authorized_by` on **every** promotion (SEC-006).
- `LocalFilesystemArtifactStore.put()` is content-addressed and immutable;
  lifecycle updates use `commit_lifecycle()` only.

## Evidence

| Test | Command |
|---|---|
| Atomic promotion + rollback | `pytest tests/operational/test_promotion_consistency.py -q` |
| Injected lineage failure | `test_promote_lineage_failure_leaves_no_partial_state` |
| Enterprise pin validation | `test_enterprise_promotion_validates_full_pin_set` |
| SEC-006 negative | `test_promote_requires_authorization_always` |
| Metadata bypass guard | `test_put_cannot_rewrite_lifecycle_metadata` |

## Consequences

- G3 may cite local + enterprise adapter evidence without claiming full
  production lakehouse coordination is deployed in CI.
- Future LakeFS/Iceberg/Nessie drivers implement `PromotionConsistencyPort`
  using the same phase contract and compensation rules.
