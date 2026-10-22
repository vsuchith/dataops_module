"""Unit-test bootstrap: mock Dagster before pipeline-related imports."""

import os
import sys
from unittest.mock import MagicMock

os.environ.setdefault("PIPELINE_MODE", "mlops")

if "dagster" not in sys.modules:
    sys.modules["dagster"] = MagicMock()
    sys.modules["dagster_mlflow"] = MagicMock()
