"""Validate marketplace.json and plugin manifests against JSON Schemas."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from tests.schemas import MARKETPLACE_SCHEMA, PLUGIN_MANIFEST_SCHEMA


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _format_errors(errors) -> str:
    lines = []
    for err in errors:
        location = "/".join(str(p) for p in err.absolute_path) or "<root>"
        lines.append(f"  - {location}: {err.message}")
    return "\n".join(lines)


def _validate(instance, schema, label: str) -> None:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))
    assert not errors, f"{label} failed schema validation:\n{_format_errors(errors)}"


class TestMarketplaceManifest:
    def test_marketplace_json_exists(self, marketplace_path: Path) -> None:
        assert marketplace_path.is_file(), f"missing {marketplace_path}"

    def test_marketplace_json_is_valid_json(self, marketplace_path: Path) -> None:
        _load_json(marketplace_path)

    def test_marketplace_json_matches_schema(self, marketplace_path: Path) -> None:
        data = _load_json(marketplace_path)
        _validate(data, MARKETPLACE_SCHEMA, "marketplace.json")

    def test_plugin_names_are_unique(self, marketplace_path: Path) -> None:
        data = _load_json(marketplace_path)
        names = [p["name"] for p in data["plugins"]]
        assert len(names) == len(set(names)), f"duplicate plugin names: {names}"

    def test_local_plugin_sources_exist(
        self, marketplace_path: Path, repo_root: Path
    ) -> None:
        data = _load_json(marketplace_path)
        for plugin in data["plugins"]:
            source = plugin["source"]
            if isinstance(source, str) and (
                source.startswith("./") or source.startswith("/")
            ):
                resolved = (repo_root / source).resolve()
                assert resolved.is_dir(), (
                    f"plugin '{plugin['name']}' source '{source}' does not exist"
                )

    def test_local_plugins_have_manifest(
        self, marketplace_path: Path, repo_root: Path
    ) -> None:
        data = _load_json(marketplace_path)
        for plugin in data["plugins"]:
            source = plugin["source"]
            if isinstance(source, str) and source.startswith("./"):
                manifest = (
                    repo_root / source / ".claude-plugin" / "plugin.json"
                ).resolve()
                assert manifest.is_file(), (
                    f"plugin '{plugin['name']}' is missing {manifest}"
                )


def _discover_plugin_manifests(plugins_dir: Path) -> list[Path]:
    if not plugins_dir.is_dir():
        return []
    return sorted(plugins_dir.glob("*/.claude-plugin/plugin.json"))


def pytest_generate_tests(metafunc):
    if "plugin_manifest" in metafunc.fixturenames:
        plugins_dir = Path(__file__).resolve().parent.parent / "plugins"
        manifests = _discover_plugin_manifests(plugins_dir)
        ids = [m.parent.parent.name for m in manifests]
        metafunc.parametrize("plugin_manifest", manifests, ids=ids or ["<none>"])


class TestPluginManifests:
    def test_plugin_json_is_valid_json(self, plugin_manifest: Path) -> None:
        _load_json(plugin_manifest)

    def test_plugin_json_matches_schema(self, plugin_manifest: Path) -> None:
        data = _load_json(plugin_manifest)
        _validate(data, PLUGIN_MANIFEST_SCHEMA, str(plugin_manifest))

    def test_plugin_name_matches_directory(self, plugin_manifest: Path) -> None:
        data = _load_json(plugin_manifest)
        plugin_dir = plugin_manifest.parent.parent
        assert data["name"] == plugin_dir.name, (
            f"plugin.json name '{data['name']}' does not match dir '{plugin_dir.name}'"
        )

    def test_plugin_components_at_root_not_under_claude_plugin(
        self, plugin_manifest: Path
    ) -> None:
        """Per the plugin spec, only plugin.json belongs in .claude-plugin/."""
        claude_plugin_dir = plugin_manifest.parent
        forbidden = {"skills", "commands", "agents", "hooks", "scripts"}
        stray = {p.name for p in claude_plugin_dir.iterdir() if p.is_dir()}
        leaked = stray & forbidden
        assert not leaked, (
            f"these directories must live at plugin root, not under .claude-plugin/: {sorted(leaked)}"
        )

    def test_skills_have_skill_md(self, plugin_manifest: Path) -> None:
        skills_dir = plugin_manifest.parent.parent / "skills"
        if not skills_dir.is_dir():
            pytest.skip("plugin has no skills/ directory")
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir():
                skill_md = skill_dir / "SKILL.md"
                assert skill_md.is_file(), f"missing {skill_md}"


class TestMarketplaceVsPlugins:
    def test_every_local_plugin_is_listed_in_marketplace(
        self, marketplace_path: Path, plugins_dir: Path
    ) -> None:
        data = _load_json(marketplace_path)
        listed = {p["name"] for p in data["plugins"]}
        on_disk = {
            p.parent.parent.name for p in _discover_plugin_manifests(plugins_dir)
        }
        missing = on_disk - listed
        assert not missing, (
            f"plugins on disk not registered in marketplace.json: {sorted(missing)}"
        )
