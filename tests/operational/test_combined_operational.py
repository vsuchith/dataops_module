"""Operational acceptance: combined PIPELINE_MODE loads without import skips."""

import os
import subprocess
import sys
from pathlib import Path


def test_combined_profile_characterization_smoke() -> None:
    root = Path(__file__).resolve().parents[2]
    python = root / ".venv" / "bin" / "python"
    if not python.exists():
        python = Path(sys.executable)
    env = {**os.environ, "PIPELINE_MODE": "combined"}
    result = subprocess.run(
        [
            str(python),
            "-m",
            "pytest",
            "tests/characterization/test_pipeline_modes.py::TestPipelineModeLoading::test_combined_mode_loads_all_packs_when_cv_deps_available",
            "-q",
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
