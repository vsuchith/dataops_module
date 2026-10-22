# reference_corpus profile

Deterministic LLMOps corpus path for local-lite and handoff to Genera (ADR-008 boundary).

## Fixtures

- `fixtures/doc_*.md`, `doc_*.txt`, `doc_*.html`
- `handoff-pins.json` — valid/invalid `CorpusVersionRef` contract pins

## Acceptance evidence

```bash
pytest tests/operational/test_llmops_corpus_pipeline.py -q
pytest tests/contract/test_llmops_handoff_contracts.py -q
```

## Security

Corpus artifacts carry `security_labels: [internal]` before handoff (AI-SEC-005).

## Dagster entry

`PIPELINE_MODE=llmops` or `combined` loads reference corpus assets from `src/llmops/`.
