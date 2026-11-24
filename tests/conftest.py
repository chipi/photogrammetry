import os
from pathlib import Path

import pytest


@pytest.fixture
def data_dir() -> Path:
    """Local cache for datasets and captures; never inside the repository."""
    return Path(os.environ.get("PG_DATA_DIR", "~/.cache/photogrammetry")).expanduser()
