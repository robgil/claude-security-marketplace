# Claude Security Marketplace

A [Claude Code plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces) hosting security-focused plugins.

## Layout

```
.
├── .claude-plugin/
│   └── marketplace.json        # Marketplace manifest
├── plugins/
│   └── secure-container/       # Plugin: Dockerfile security analysis
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── skills/
│       │   └── secure-container/
│       │       ├── SKILL.md
│       │       └── references/
│       ├── scripts/
│       └── tests/
├── tests/                      # Schema validation tests (pytest)
├── Dockerfile                  # Chainguard-based test runner
├── Makefile
└── requirements.txt
```

## Plugins

| Name | Description |
| --- | --- |
| [secure-container](plugins/secure-container/) | Analyze Dockerfiles and recommend hardening per Chainguard best practices. |

## Installing the marketplace in Claude Code

```
/plugin marketplace add <git-url-or-local-path>
/plugin install secure-container@claude-security-marketplace
```

## Development

All testing runs inside a Chainguard Python container — no host Python or Node required.

```bash
make test       # build the container and run the schema validation suite
make build      # build the container only
make clean      # remove the container image
```

The test suite (`tests/`) validates:

- `.claude-plugin/marketplace.json` against the marketplace JSON Schema.
- Every `plugins/*/.claude-plugin/plugin.json` against the plugin manifest schema.
- That plugin names are unique, match their directory, and that local `source` paths resolve.
- That plugin components (`skills/`, `commands/`, `agents/`, `hooks/`, `scripts/`) live at the plugin root and not under `.claude-plugin/`.
- That every plugin on disk is registered in `marketplace.json`.

Python is used **only** to validate the manifest schemas; runtime plugin behavior lives in the skill prompts.

## License

Apache-2.0
