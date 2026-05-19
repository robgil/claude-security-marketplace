"""Validate SKILL.md frontmatter for every skill in every plugin.

The skill `name:` field must be a kebab-case slug that matches the skill
directory. Title Case names with spaces (e.g. `Secure Container Creation`)
break Claude Code's `/<skill-name>` invocation, so this is a hard check.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

KEBAB_SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def _discover_skill_dirs(plugins_dir: Path) -> list[Path]:
    if not plugins_dir.is_dir():
        return []
    return sorted(
        skill
        for plugin in plugins_dir.iterdir()
        if plugin.is_dir() and (plugin / "skills").is_dir()
        for skill in (plugin / "skills").iterdir()
        if skill.is_dir()
    )


def _parse_frontmatter(skill_md: Path) -> dict[str, str]:
    """Parse the YAML frontmatter block — flat key: value pairs only.

    Avoids a PyYAML dependency since the SKILL.md frontmatter spec only
    needs simple scalars (name, description, version).
    """
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise AssertionError(f"{skill_md} is missing the opening '---' frontmatter fence")
    end = text.find("\n---", 4)
    if end == -1:
        raise AssertionError(f"{skill_md} is missing the closing '---' frontmatter fence")
    block = text[4:end]
    result: dict[str, str] = {}
    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise AssertionError(f"{skill_md} frontmatter line is not 'key: value': {line!r}")
        key, _, value = line.partition(":")
        result[key.strip()] = value.strip()
    return result


def pytest_generate_tests(metafunc):
    if "skill_dir" in metafunc.fixturenames:
        plugins_dir = Path(__file__).resolve().parent.parent / "plugins"
        skills = _discover_skill_dirs(plugins_dir)
        ids = [f"{s.parent.parent.name}/{s.name}" for s in skills]
        metafunc.parametrize("skill_dir", skills, ids=ids or ["<none>"])


class TestSkillFrontmatter:
    def test_skill_md_exists(self, skill_dir: Path) -> None:
        assert (skill_dir / "SKILL.md").is_file(), f"missing {skill_dir / 'SKILL.md'}"

    def test_frontmatter_has_name(self, skill_dir: Path) -> None:
        fm = _parse_frontmatter(skill_dir / "SKILL.md")
        assert "name" in fm and fm["name"], f"{skill_dir}/SKILL.md frontmatter missing 'name'"

    def test_name_is_kebab_case_slug(self, skill_dir: Path) -> None:
        """Reject Title Case / spaces / underscores — they break /<skill-name>."""
        fm = _parse_frontmatter(skill_dir / "SKILL.md")
        name = fm.get("name", "")
        assert KEBAB_SLUG.match(name), (
            f"{skill_dir}/SKILL.md name {name!r} must be kebab-case "
            f"(lowercase letters, digits, hyphens). "
            f"Names with spaces or Title Case break Claude Code's /<skill-name> invocation."
        )

    def test_name_matches_directory(self, skill_dir: Path) -> None:
        fm = _parse_frontmatter(skill_dir / "SKILL.md")
        assert fm.get("name") == skill_dir.name, (
            f"{skill_dir}/SKILL.md name {fm.get('name')!r} does not match "
            f"skill directory {skill_dir.name!r}"
        )

    def test_frontmatter_has_description(self, skill_dir: Path) -> None:
        fm = _parse_frontmatter(skill_dir / "SKILL.md")
        assert fm.get("description"), (
            f"{skill_dir}/SKILL.md frontmatter missing 'description' "
            f"(used by Claude Code to decide when to activate the skill)"
        )
