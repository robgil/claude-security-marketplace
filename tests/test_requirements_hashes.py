"""Enforce supply-chain hardening for Python dependencies.

`requirements.txt` is the lockfile installed by the test container with
`pip install --require-hashes`. Every entry must be exact-pinned
(`name==version`) and carry at least one `--hash=sha256:` digest.
Top-level deps live in `requirements.in`; regenerate the lockfile with
`make lock` after editing.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS_IN = REPO_ROOT / "requirements.in"
REQUIREMENTS_TXT = REPO_ROOT / "requirements.txt"

PIN_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([A-Za-z0-9._+!-]+)\s*(?:\\)?$")
HASH_RE = re.compile(r"^\s*--hash=sha256:[0-9a-f]{64}\s*(?:\\)?$")
TOP_LEVEL_NAME_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)")


def _normalize(name: str) -> str:
    """PEP 503 normalized name for cross-file comparison."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _parse_lockfile(text: str) -> list[tuple[str, str, list[str], int]]:
    """Return [(name, version, [sha256, ...], starting_line_no), ...].

    Continuation lines (trailing `\\`) are collapsed into the parent record.
    Comment lines and blank lines are skipped.
    """
    records: list[tuple[str, str, list[str], int]] = []
    current: dict | None = None
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        pin = PIN_RE.match(line)
        if pin:
            if current is not None:
                records.append(
                    (current["name"], current["version"], current["hashes"], current["lineno"])
                )
            current = {
                "name": pin.group(1),
                "version": pin.group(2),
                "hashes": [],
                "lineno": lineno,
            }
            continue
        h = HASH_RE.match(line)
        if h:
            assert current is not None, (
                f"requirements.txt:{lineno}: --hash line with no preceding package pin"
            )
            current["hashes"].append(line.strip().rstrip("\\").strip())
            continue
        raise AssertionError(
            f"requirements.txt:{lineno}: unrecognized line {raw!r} "
            f"(every line must be a comment, a 'name==version' pin, or a '--hash=sha256:...' entry)"
        )
    if current is not None:
        records.append((current["name"], current["version"], current["hashes"], current["lineno"]))
    return records


def _top_level_names() -> set[str]:
    names: set[str] = set()
    for raw in REQUIREMENTS_IN.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = TOP_LEVEL_NAME_RE.match(line)
        assert m, f"requirements.in: cannot parse package name from {raw!r}"
        names.add(_normalize(m.group(1)))
    return names


class TestRequirementsLockfile:
    def test_requirements_in_exists(self) -> None:
        assert REQUIREMENTS_IN.is_file(), (
            "requirements.in is missing — top-level deps must live there, "
            "and requirements.txt is regenerated from it via `make lock`."
        )

    def test_requirements_txt_exists(self) -> None:
        assert REQUIREMENTS_TXT.is_file(), "requirements.txt is missing"

    def test_no_editable_or_url_installs(self) -> None:
        text = REQUIREMENTS_TXT.read_text(encoding="utf-8")
        for lineno, raw in enumerate(text.splitlines(), start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            assert not line.startswith("-e "), (
                f"requirements.txt:{lineno}: editable installs (-e) bypass hash checking"
            )
            assert "://" not in line or line.startswith("--hash="), (
                f"requirements.txt:{lineno}: URL/VCS installs are not allowed in the lockfile"
            )

    def test_every_entry_is_exact_pinned_and_hashed(self) -> None:
        records = _parse_lockfile(REQUIREMENTS_TXT.read_text(encoding="utf-8"))
        assert records, "requirements.txt has no package entries"
        for name, version, hashes, lineno in records:
            assert hashes, (
                f"requirements.txt:{lineno}: {name}=={version} has no --hash=sha256: entry. "
                f"Regenerate the lockfile with `make lock`."
            )

    def test_top_level_deps_present_in_lockfile(self) -> None:
        top = _top_level_names()
        locked = {
            _normalize(name)
            for name, _v, _h, _ln in _parse_lockfile(REQUIREMENTS_TXT.read_text(encoding="utf-8"))
        }
        missing = top - locked
        assert not missing, (
            f"requirements.in declares {sorted(missing)!r} but they are not in the lockfile. "
            f"Run `make lock` to regenerate requirements.txt."
        )
