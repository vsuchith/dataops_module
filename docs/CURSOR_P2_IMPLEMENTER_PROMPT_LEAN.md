# Cursor Implementer Prompt (Lean) — DataOps Brownfield P1/P2

Token-optimized variant. Full checklist and analysis requirements remain in
`CURSOR_P2_IMPLEMENTER_PROMPT.md` and `DATAOPS_MATURATION_PLAN.md` §8 (P1/P2).
Use this for routine sessions; use the full prompt only when recovering from a
failed gate or ambiguous scope.

Copy the block below into a **new** Cursor Agent session.

- **Implementer:** `cursor-composer`
- **Reviewer:** `codex` (separate session — never the same context)

````markdown
# P1/P2 Analysis — dataops-accelerator-maturity

**Implementer:** cursor-composer | **Reviewer:** codex (independent)
**Harness:** `/home/suchithgoud/Downloads/Modular/harness`
**Engagement:** `engagements/modules/dataops-accelerator-maturity/`
**Accelerator (read-only):** `/home/suchithgoud/Downloads/Modular/dataops_module`

## Authority (read, do not overwrite)

| Doc | Role |
|---|---|
| `dataops_module/docs/DATAOPS_MATURATION_PLAN.md` | P1/P2 deliverables, scope, compatibility |
| `harness/docs/modular/ACCELERATOR_MATURATION_MASTER_PLAN.md` | Program sequencing, ownership |
| `dataops_module/docs/GENERA_LLMOPS_BOUNDARY_ANALYSIS.md` | Genera/LLMOps split |

Skim on first session only: `harness/execution/GATE_PROTOCOL.md` (G-A),
`harness/knowledge/guides/PORTABLE_ENGAGEMENT_LANES.md`.

## Hard boundaries

- Write analysis **only** under `harness/engagements/modules/dataops-accelerator-maturity/`
- **No** changes to `dataops_module/src/`, deployments, CI, or dependencies
- **No** `src/` under the engagement; **no** Genera/EvalPlatform/[company project]/adapters
- **No** platform-contract schema copies into the accelerator
- **No** LLMOps operational claims while assets return `status: stub`
- **No** L3/L4 claims — target is **L2 adapter-ready**
- **Do not** approve G-A — reviewer `codex` records the decision

## Task

Complete P1/P2 per `DATAOPS_MATURATION_PLAN.md` §8. Produce evidence-backed
analysis artifacts; pass G-A machine preflight; stop at review packet (no P3/P4).

## Init (only if engagement missing)

```bash
cd /home/suchithgoud/Downloads/Modular/harness
test -f engagements/modules/dataops-accelerator-maturity/engagement.json || \
  python3 tools/harness.py init dataops-accelerator-maturity --kind module --maturity-target L2
```

## Required artifacts

Write under the engagement (remove all `{{...}}` from G-A-checked docs):

1. `brd/BRIEF.md`
2. `docs/BRD_ANALYSIS.md` — include Open Questions (no unresolved **P0**)
3. `docs/DOMAIN_MODEL.md`
4. `docs/INTEGRATION_MAP.md` — mark LakeFS/Iceberg/Nessie as G-B ADR unless resolved
5. `docs/DEPLOYMENT_PROFILE.md`
6. `docs/BROWNFIELD_INVENTORY.md`
7. `docs/COMPATIBILITY_INVENTORY.md`
8. `docs/OPERATIONAL_BASELINE.md`
9. `docs/CAPABILITY_MATURITY_MATRIX.md`
10. `docs/MODULE_CHARTER.md` (P2 draft)

**Machine G-A checks placeholders in docs 2–5 only.** Artifacts 6–10 are
required for human review per the maturation plan.

## Evidence rule

README, Compose complexity, and service startup ≠ maturity. Every claim needs
**file path** and/or **command result** (`PASS` / `FAIL` / `NOT RUN` + reason).
Never use `|| true` on evidence commands. Do not install packages or start the
full stack merely to look green.

## Brownfield spot-checks (representative — expand in BROWNFIELD_INVENTORY)

| Risk | Path |
|---|---|
| PIPELINE_MODE / silent imports | `src/pipelines/__init__.py` |
| LLMOps stubs | `src/llmops/pipelines/definitions.py` |
| Fraud defaults | `src/core/config/settings.py` |
| Lineage (not generic yet) | `src/core/lineage/tracker.py` |
| Provider aggregation | `src/core/resources/connections.py` |
| Stale CI paths | `.github/workflows/ci.yml` |
| Compose overlays | `deploy/docker/compose/docker-compose.*.yml` |

## Operational baseline (non-destructive)

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

Record each as PASS / FAIL / NOT RUN in `OPERATIONAL_BASELINE.md`.

## Exit commands

```bash
cd /home/suchithgoud/Downloads/Modular/harness
python3 tools/harness.py validate --engagement modules/dataops-accelerator-maturity
python3 tools/harness.py verify node G-A --engagement modules/dataops-accelerator-maturity
python3 tools/harness.py gate preflight G-A --engagement modules/dataops-accelerator-maturity
```

On failure: fix **analysis artifacts only**, rerun the failed command.

## Completion report (keep short)

1. Files changed (paths only)
2. Capability one-liners (with evidence pointer)
3. Command results table
4. P1/P2 open questions (confirm no P0)
5. Confirm `dataops_module` runtime unchanged
6. Handoff: `checkpoints/gates/G-A/review-packet.md` → reviewer `codex`

Do **not** approve G-A. Do **not** start P3/P4.
````

## When to use full prompt

- First engagement of this type on a new accelerator
- G-A rejected with architecture/ownership findings
- Recovery after preflight regression on artifacts 6–10

Full prompt: `dataops_module/docs/CURSOR_P2_IMPLEMENTER_PROMPT.md`
