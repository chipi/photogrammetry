from pathlib import Path

import pytest

import recon

REPO = Path(__file__).resolve().parent.parent


@pytest.mark.unit
def test_version() -> None:
    assert recon.__version__ == "0.0.0"


@pytest.mark.unit
def test_data_dir_is_outside_repo(data_dir: Path) -> None:
    assert REPO not in data_dir.resolve().parents
