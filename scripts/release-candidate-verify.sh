#!/usr/bin/env bash
# Release candidate verification — offline-first (E5).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -x .venv/bin/python ]]; then
  RECREATE_VENV=1 bash scripts/setup-dev-venv.sh
fi

PY=".venv/bin/python"

echo "==> contract regression"
$PY -m pytest tests/contract -q

echo "==> operational profile matrix (offline)"
$PY -m pytest tests/operational -q -m "not integration"

echo "==> integration offline subset"
$PY -m pytest tests/integration -q -m "not integration"

echo "==> compose overlay config"
for f in core fraud cv litellm; do
  docker compose -f deploy/docker/compose/docker-compose.core.yml \
    -f "deploy/docker/compose/docker-compose.${f}.yml" config >/dev/null
done

echo "release-candidate-verify: PASS"
