# CLAUDE.md

Project-specific instructions for Claude Code working in this repository.

## Testing — container only

**Never run `pytest` directly on the host.** All test execution must go through the Chainguard container defined in [Dockerfile](Dockerfile).

- Run the full suite: `make test`
- Build the image only: `make build`
- Remove the image: `make clean`

Do not run `pytest`, `python -m pytest`, `pip install -r requirements.txt`, or any other host-Python commands to validate changes. The repo has no host virtualenv and the test image pins exact dependency versions for reproducibility — host runs will drift.

If a test fails inside the container, fix the code and re-run `make test`. Do not "quickly check" by invoking pytest locally.

## Dependencies — hash-pinned, always

All Python dependencies installed in the test container must be locked to an exact version and at least one `sha256` hash. This is non-negotiable — it prevents supply-chain attacks where a malicious release of a transitive dep could land in our test image.

- Edit top-level deps in [requirements.in](requirements.in) only
- Regenerate the lockfile with `make lock` (runs `pip-compile --generate-hashes` inside the Chainguard container — never on the host)
- Commit `requirements.in` and `requirements.txt` together
- The Dockerfile uses `pip install --require-hashes`, so any unhashed or unpinned entry will fail the container build
- [tests/test_requirements_hashes.py](tests/test_requirements_hashes.py) enforces this on every `make test` run

Do not hand-edit `requirements.txt`. Do not add `pip install` lines elsewhere in the Dockerfile that bypass `--require-hashes`. The Chainguard base image in [Dockerfile](Dockerfile) must also stay pinned to a `sha256:` digest, never a floating tag like `:latest-dev`.

## CI — GitHub Actions pinned to commit SHAs

Every `uses:` ref in [.github/workflows/](.github/workflows/) must be pinned to a full 40-character commit SHA, not a tag or branch. Tags can be force-pushed by a compromised maintainer; commit SHAs cannot.

Keep the human-readable version as a trailing comment so reviewers know what they're looking at:

```yaml
- uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6.0.2
```

Resolve a tag to its SHA with `gh api repos/<owner>/<repo>/git/refs/tags/<tag> --jq '.object.sha'`. [tests/test_workflow_pins.py](tests/test_workflow_pins.py) rejects any `uses:` ref that isn't a 40-char hex SHA (local `./...` paths and `docker://...@sha256:` refs are also allowed).

## Skill naming

Skill `name:` frontmatter fields must be **kebab-case slugs** (`^[a-z0-9]+(-[a-z0-9]+)*$`) and must match the skill directory name. Title Case names with spaces break Claude Code's `/<skill-name>` invocation. This is enforced by [tests/test_skill_frontmatter.py](tests/test_skill_frontmatter.py); changes that violate it will fail `make test`.

The plugin directory, the plugin.json `name`, the marketplace.json entry, and the skill directory should all use the same slug.

## Commits — Conventional Commits, always

Every commit message must follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/):

```
<type>(<optional scope>): <description>

[optional body]

[optional footer(s)]
```

- **Allowed types**: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`
- **Scope**: the plugin or area touched, e.g. `feat(secure-container-review): ...`, `chore(tests): ...`, `docs(readme): ...`
- **Breaking changes**: append `!` after the type/scope (`feat(secure-container-review)!: ...`) **and** add a `BREAKING CHANGE:` footer explaining the break
- Description: imperative mood, lowercase, no trailing period

This is non-negotiable — do not write `update X` or `misc fixes` style messages.

## Versioning — SemVer

Plugin versions in `plugin.json` and `marketplace.json` follow [Semantic Versioning 2.0.0](https://semver.org/):

- **MAJOR** (`X.0.0`): backwards-incompatible changes — renamed/removed skills, renamed plugin, changed install slug, removed rules, changed finding output format in a way consumers must adapt to
- **MINOR** (`0.X.0`): backwards-compatible additions — new skills, new rules, new optional config flags, expanded framework citations
- **PATCH** (`0.0.X`): backwards-compatible fixes — typo fixes, prose clarifications, doc-only changes, internal refactors with identical behavior

When bumping a plugin's version, bump it in **both** `plugins/<plugin>/.claude-plugin/plugin.json` and the corresponding entry in `.claude-plugin/marketplace.json` — they must stay in sync.

The Conventional Commits type maps to the SemVer bump: `fix` → PATCH, `feat` → MINOR, anything with `!` or `BREAKING CHANGE:` → MAJOR. `docs`/`chore`/`test`/`ci`/`build`/`refactor` without behavior change → no version bump.

## Repo layout reminders

- Marketplace manifest: [.claude-plugin/marketplace.json](.claude-plugin/marketplace.json)
- Plugin manifests live at `plugins/<plugin>/.claude-plugin/plugin.json`
- Skill components (`skills/`, `commands/`, `agents/`, `hooks/`, `scripts/`) live at the plugin root, **not** under `.claude-plugin/` — this is enforced by [tests/test_schemas.py](tests/test_schemas.py)
- Every plugin on disk must be registered in `marketplace.json`
