#!/usr/bin/env bash
# G2 live CV API smoke — Compose-backed exp-cv-api on port 8002.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HARNESS_G2="${ROOT}/../harness/engagements/modules/dataops-accelerator-maturity/checkpoints/gates/G2"
PYTHON="${PYTHON:-/usr/bin/python3.12}"
COMPOSE=(docker compose -f deploy/docker/compose/docker-compose.core.yml -f deploy/docker/compose/docker-compose.cv.yml)
cd "$ROOT"
mkdir -p "$HARNESS_G2"
LOG="$HARNESS_G2/live-cv-api-smoke.log"
: >"$LOG"

log() {
  echo "$@" | tee -a "$LOG"
}

cleanup() {
  if [[ "${KEEP_COMPOSE:-}" != "1" ]]; then
    "${COMPOSE[@]}" stop exp-cv-api >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

log "== Compose config (core + cv) =="
"${COMPOSE[@]}" config >/dev/null
log "compose_config: ok"

log "== Build exp-cv-api (with .dockerignore) =="
"${COMPOSE[@]}" build exp-cv-api 2>&1 | tee -a "$LOG"

log "== Start exp-cv-api and dependencies =="
"${COMPOSE[@]}" up -d exp-mlflow exp-kafka exp-trino exp-cv-api 2>&1 | tee -a "$LOG"

log "== Compose service state =="
"${COMPOSE[@]}" ps exp-cv-api exp-mlflow exp-kafka exp-trino 2>&1 | tee -a "$LOG"

log "== Wait for CV API health =="
for _ in $(seq 1 120); do
  if curl -sf http://127.0.0.1:8002/health >/dev/null; then
    log "cv_api_health: ok"
    break
  fi
  sleep 2
done
curl -sf http://127.0.0.1:8002/health >/dev/null || {
  log "cv_api_health: failed"
  "${COMPOSE[@]}" logs --tail=80 exp-cv-api 2>&1 | tee -a "$LOG"
  exit 1
}

export CV_API_URL="${CV_API_URL:-http://127.0.0.1:8002}"
log "== Live CV API integration smoke (Compose-backed) =="
"$PYTHON" -m pytest tests/integration/test_cv_api_integration.py -v -m integration 2>&1 | tee -a "$LOG"
log "Recorded: checkpoints/gates/G2/live-cv-api-smoke.log"
