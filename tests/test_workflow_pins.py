"""Enforce that every GitHub Actions `uses:` ref is pinned to a 40-char commit SHA.

Tag refs like `@v4` or branch refs like `@main` are mutable and can be retargeted
by a compromised maintainer; commit SHAs cannot. Pinning to a SHA is the OpenSSF
Scorecard `pinned-dependencies` requirement.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"

USES_LINE_RE = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)\s*(?:#.*)?$")
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")


def _discover_workflows() -> list[Path]:
    if not WORKFLOWS_DIR.is_dir():
        return []
    return sorted(p for p in WORKFLOWS_DIR.iterdir() if p.suffix in {".yml", ".yaml"})


def _extract_uses(workflow: Path) -> list[tuple[int, str]]:
    refs: list[tuple[int, str]] = []
    for lineno, raw in enumerate(workflow.read_text(encoding="utf-8").splitlines(), start=1):
        m = USES_LINE_RE.match(raw)
        if m:
            refs.append((lineno, m.group(1)))
    return refs


def pytest_generate_tests(metafunc):
    if "workflow_uses" in metafunc.fixturenames:
        params: list[tuple[Path, int, str]] = []
        for wf in _discover_workflows():
            for lineno, ref in _extract_uses(wf):
                params.append((wf, lineno, ref))
        ids = [f"{wf.name}:{ln}:{ref}" for wf, ln, ref in params] or ["<none>"]
        metafunc.parametrize("workflow_uses", params or [None], ids=ids)


class TestWorkflowPins:
    def test_uses_is_pinned_to_commit_sha(self, workflow_uses) -> None:
        if workflow_uses is None:
            return
        workflow, lineno, ref = workflow_uses

        if ref.startswith("./") or ref.startswith("../"):
            return
        if ref.startswith("docker://"):
            assert "@sha256:" in ref, (
                f"{workflow.name}:{lineno}: docker:// uses ref must be pinned with @sha256: "
                f"(got {ref!r})"
            )
            return

        assert "@" in ref, (
            f"{workflow.name}:{lineno}: uses ref {ref!r} has no @<ref> — pin to a commit SHA"
        )
        _action, _, gitref = ref.partition("@")
        assert SHA40_RE.match(gitref), (
            f"{workflow.name}:{lineno}: uses ref {ref!r} is not pinned to a 40-char commit SHA. "
            f"Tags and branches (e.g. @v4, @main) are mutable. "
            f"Use a SHA and put the version in a trailing comment, e.g. "
            f"`uses: actions/checkout@<sha> # v4.3.1`."
        )
