"""JSON Schemas for Claude Code plugin marketplace manifests.

These schemas describe the structure documented at:
  https://code.claude.com/docs/en/plugin-marketplaces
  https://code.claude.com/docs/en/plugins-reference
"""

KEBAB_CASE = r"^[a-z0-9]+(-[a-z0-9]+)*$"

OWNER_SCHEMA = {
    "type": "object",
    "required": ["name"],
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "email": {"type": "string", "format": "email"},
        "url": {"type": "string", "format": "uri"},
    },
    "additionalProperties": True,
}

PLUGIN_SOURCE_OBJECT_SCHEMA = {
    "type": "object",
    "required": ["source"],
    "properties": {
        "source": {"type": "string", "enum": ["github", "git", "directory"]},
        "repo": {"type": "string"},
        "url": {"type": "string"},
        "path": {"type": "string"},
        "branch": {"type": "string"},
        "tag": {"type": "string"},
        "commit": {"type": "string"},
    },
    "additionalProperties": True,
}

MARKETPLACE_PLUGIN_ENTRY_SCHEMA = {
    "type": "object",
    "required": ["name", "source"],
    "properties": {
        "name": {"type": "string", "pattern": KEBAB_CASE},
        "source": {
            "oneOf": [
                {"type": "string", "minLength": 1},
                PLUGIN_SOURCE_OBJECT_SCHEMA,
            ]
        },
        "description": {"type": "string"},
        "version": {"type": "string"},
        "category": {"type": "string"},
        "author": OWNER_SCHEMA,
        "homepage": {"type": "string", "format": "uri"},
        "keywords": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
        },
        "dependencies": {"type": "array"},
    },
    "additionalProperties": True,
}

MARKETPLACE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["name", "owner", "plugins"],
    "properties": {
        "name": {"type": "string", "pattern": KEBAB_CASE},
        "owner": OWNER_SCHEMA,
        "plugins": {
            "type": "array",
            "minItems": 1,
            "items": MARKETPLACE_PLUGIN_ENTRY_SCHEMA,
        },
        "allowCrossMarketplaceDependenciesOn": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "additionalProperties": True,
}

PLUGIN_MANIFEST_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["name"],
    "properties": {
        "name": {"type": "string", "pattern": KEBAB_CASE},
        "version": {
            "type": "string",
            "pattern": r"^\d+\.\d+\.\d+(-[0-9A-Za-z\.-]+)?(\+[0-9A-Za-z\.-]+)?$",
        },
        "description": {"type": "string"},
        "author": OWNER_SCHEMA,
        "homepage": {"type": "string", "format": "uri"},
        "license": {"type": "string"},
        "keywords": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
        },
    },
    "additionalProperties": True,
}
