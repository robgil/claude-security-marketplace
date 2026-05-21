import shutil
import subprocess
from pathlib import Path


def test_workflows_pass_zizmor(repo_root: Path) -> None:
    workflows_dir = repo_root / ".github" / "workflows"
    assert workflows_dir.is_dir(), f"missing {workflows_dir}"

    zizmor = shutil.which("zizmor")
    assert zizmor is not None, "zizmor binary not on PATH — check requirements.txt"

    result = subprocess.run(
        [
            zizmor,
            "--offline",
            "--persona=regular",
            "--format=plain",
            "--no-progress",
            str(workflows_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, (
        "zizmor found security issues in GitHub Actions workflows:\n"
        f"--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )
