# fraud_detection profile

Representative structured fraud detection path using generic DataOps kernel ingest.

## Fixtures

- `fixtures/transactions_sample.csv` — offline batch source

## Acceptance evidence

```bash
pytest tests/operational/test_fraud_operational.py -q
pytest tests/integration/test_structured_ingest.py -q
```

## Promotion policy

Configured in `profile.yaml` (`promotion_policy`). Enterprise lakehouse promotion uses
ADR-009 consistency pins via `PromotionService` (see `tests/operational/test_promotion_consistency.py`).

## Live smoke (opt-in)

Requires core + fraud Compose stack and running Fraud API:

```bash
pytest tests/integration/test_fraud_api_integration.py -m integration
```
