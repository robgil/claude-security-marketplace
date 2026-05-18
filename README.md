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

## Security frameworks assessed and mapped

Plugins in this marketplace produce findings that cite specific control identifiers from established security frameworks, so downstream GRC, audit, and FedRAMP assessment teams can trace each finding back to their own catalogs without re-deriving the mapping. Each plugin's `SKILL.md` documents the exact per-rule mapping; the full reference text lives under `plugins/<plugin>/skills/<skill>/references/`.

The frameworks the marketplace's skills assess against:

| Framework | What it is | How the skills use it |
| --- | --- | --- |
| **[NIST Cybersecurity Framework 2.0](https://www.nist.gov/cyberframework)** | Outcome-oriented framework most boards and risk committees read. Released Feb 2024; introduces the new **PR.PS (Platform Security)** function. | Findings tagged with CSF subcategories — primarily under **GV.SC** (Supply Chain Risk Management), **PR.AA** (Identity / Access Control), **PR.DS** (Data Security), **PR.PS** (Platform Security), **PR.IR** (Infrastructure Resilience), **ID.AM** / **ID.RA** (Asset Management, Risk Assessment). For audiences still on CSF 1.1, PR.PS controls fall back to PR.IP-01, PR.IP-03, PR.DS-06. |
| **[NIST SP 800-190](https://csrc.nist.gov/publications/detail/sp/800-190/final)** | The container-specific NIST publication. §4 covers image risks; §5 covers orchestrator and runtime risks. | Findings cite specific sections (§4.1 image vulnerabilities, §4.4 secrets, §4.5 untrusted images, §4.6 registry security). This is the standard most container-image findings map to. |
| **[NIST SP 800-53 Rev. 5](https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final)** | The prescriptive control catalog U.S. federal auditors map to. | Findings cite specific control IDs. The two controls that drive the largest number of findings are **AC-6 (Least Privilege)** and **CM-7 (Least Functionality)** — every form of "this doesn't belong in a production container" maps to one or both. Supply-chain findings cluster in the **SR family** (SR-3, SR-4, SR-5, SR-6, SR-9, SR-10, SR-11). Cryptographic findings cite SC-8/12/13/28. Secret findings cite IA-5. |
| **[NIST SSDF (SP 800-218)](https://csrc.nist.gov/Projects/ssdf)** | Secure Software Development Framework. | Findings cite SSDF practices — primarily **PO 1.1** (define security requirements), **PW 1.2** (protect code from unauthorized access), **PW 4.1 / PW 4.4** (reuse from approved sources, well-secured software), **RV 1.1** (identify vulnerabilities). |
| **[CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)** | Industry-standard image and runtime hardening benchmark from the Center for Internet Security. | Findings cite specific benchmark sections — image checks under section 4 (e.g., 4.1 USER, 4.5 unnecessary packages, 4.6 HEALTHCHECK, 4.10 no secrets in Dockerfiles); runtime checks under section 5 (5.4 privileged, 5.12 read-only rootfs, 5.25 no new privileges). |
| **[FedRAMP Vulnerability Scanning Requirements for Containers](https://www.fedramp.gov/)** | FedRAMP-specific container scanning requirements. | Cited on supply-chain and image-source findings (Rules #10, #13) when in scope. Pairs with FedRAMP Moderate/High baselines. |
| **[FIPS 140-2 / FIPS 140-3](https://csrc.nist.gov/projects/cryptographic-module-validation-program)** | Cryptographic module validation standard. | Cited only when FIPS context is declared (config flag, `LABEL compliance.fips="required"`, repo marker, or explicit prompt). Triggers Rule #14: require a FIPS-variant base, reject explicit disabling, warn that FIPS image ≠ FIPS application configuration. |
| **[DISA STIG](https://public.cyber.mil/stigs/)** | DoD Security Technical Implementation Guides. | Container Platform STIG and Kubernetes STIG cited where applicable; relevant for DoD SRG IL4/IL5 workloads. |
| **[NSA/CISA Kubernetes Hardening Guide](https://media.defense.gov/2022/Aug/29/2003066362/-1/-1/0/CTR_KUBERNETES_HARDENING_GUIDANCE_1.2_20220829.PDF)** | Joint NSA/CISA guidance on Kubernetes hardening. | Cited on findings with runtime implications — single-purpose containers, Pod Security Standards, runtime configuration. |
| **[OWASP Docker Top 10](https://owasp.org/www-project-docker-top-10/)** | OWASP's container security top-10. | Cited where the finding aligns with a top-10 category. |
| **[SLSA](https://slsa.dev/)** | Supply-chain Levels for Software Artifacts. | Cited on supply-chain and build-hermeticity findings — Build L2 for provenance (Rule #9), Build L3 for hermetic builds (Rule #7). |

**Why both CSF 2.0 *and* 800-53 (not one or the other):** CSF is the framework most boards and risk committees read; 800-53 is the catalog auditors map to. Citing both makes findings legible to both audiences without forcing either to translate.

Each plugin's `SKILL.md` includes a per-rule `Maps to:` line listing the exact control IDs that apply, plus a "Most-cited NIST 800-53 controls" summary table near the top. Findings produced by the skill carry a `Refs:` line in the same format.

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

## References

The rules and reasoning behind the `secure-container` skill draw on the following background reading. The skill citations themselves reference NIST SP 800-190, NIST 800-53, NIST SSDF, CIS Docker Benchmark, FedRAMP container scanning guidance, and FIPS 140-2/140-3 — see [plugins/secure-container/skills/secure-container/SKILL.md](plugins/secure-container/skills/secure-container/SKILL.md) for the per-rule mapping.

- **["The Do's and Don'ts of Containers"](https://medium.com/@rem5/the-dos-and-don-ts-of-containers-0d1bd623a441)** by Rob Gil — the operational thesis behind several of the skill's rules: over-patch/under-harden, untrusted vendor and community containers, what belongs in a final image, and the case for purpose-built minimal distributions over general-purpose ones. Rules 1, 2, 5, 6, 11, 12, 13, and 14 in the skill are direct codifications of recommendations from this article.
- **[NIST SP 800-190 — Application Container Security Guide](https://csrc.nist.gov/publications/detail/sp/800-190/final)** — the foundational NIST publication on container security; the skill's findings cite specific sections (§4.1 image vulnerabilities, §4.4 secrets, §4.5 untrusted images, §4.6 registry security).
- **[NIST SSDF (SP 800-218)](https://csrc.nist.gov/Projects/ssdf)** — Secure Software Development Framework practices referenced in skill output (PO, PS, PW, RV families).
- **[CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)** — image-level checks (section 4) and runtime checks (section 5).
- **[Chainguard documentation](https://edu.chainguard.dev/)** — purpose-built minimal images and the Wolfi distribution.

## License

Apache-2.0
