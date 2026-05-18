from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def marketplace_path(repo_root: Path) -> Path:
    return repo_root / ".claude-plugin" / "marketplace.json"


@pytest.fixture(scope="session")
def plugins_dir(repo_root: Path) -> Path:
    return repo_root / "plugins"
