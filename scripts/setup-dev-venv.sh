#!/usr/bin/env bash
# PEP 668-safe dev/CI install for dataops_module (E1 baseline).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if command -v python3.11 >/dev/null 2>&1; then
  PYTHON="${PYTHON:-python3.11}"
elif command -v /usr/bin/python3.12 >/dev/null 2>&1; then
  PYTHON="${PYTHON:-/usr/bin/python3.12}"
elif command -v python3.12 >/dev/null 2>&1; then
  PYTHON="${PYTHON:-python3.12}"
else
  PYTHON="${PYTHON:-python3}"
fi
VENV_DIR="${VENV_DIR:-.venv}"
EXTRAS="${INSTALL_EXTRAS:-dev,feast,monitoring}"
if [[ "${INSTALL_CV:-0}" == "1" ]]; then
  EXTRAS="${EXTRAS},cv"
fi
if [[ "${RECREATE_VENV:-0}" == "1" ]] && [[ -d "$VENV_DIR" ]]; then
  rm -rf "$VENV_DIR"
fi
if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON" -m venv "$VENV_DIR" --copies
fi
# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip wheel
python -m pip install -e ".[${EXTRAS}]"
echo "Installed into $VENV_DIR (extras: ${EXTRAS})"
echo "Activate with: source $VENV_DIR/bin/activate"
