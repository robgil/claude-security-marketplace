---
name: Secure Container Creation
description: Analyze Dockerfiles and provide recommendations for creating secure containers following best practices
version: 1.0.0
---

# Secure Container Creation SKILL

This SKILL helps create secure containers by analyzing Dockerfiles and providing recommendations for hardening container security.

## Requirements Implemented

### 1. Use Chainguard when possible
- Analyze Dockerfiles for Chainguard base images
- Recommend Chainguard alternatives for base images
- Check for latest security updates in Chainguard images

### 2. Multi-stage builds with dev tools
- Identify base images used for build vs runtime
- Recommend multi-stage approaches separating build dependencies
- Verify no development tools in production images

### 3. Non-root user usage
- Check for USER directive usage
- Verify running applications as non-root users
- Recommend alternative user creation (e.g., USER appuser:appuser)

### 4. Privileged mode requirements
- Identify whether containers run in privileged mode
- Report dangerous privileged configurations
- Recommend safe alternatives to privileged mode

### 5. Shell scripts in container builds
- Identify shell script usage in Dockerfile
- Alert when shell scripts are used in non-essential parts
- Recommend alternative approaches for script execution

### 6. Single process containers
- Verify container runs only one process
- Identify potential multi-process configurations
- Recommend process management solutions

### 7. Outbound network call restrictions
- Check for curl, wget, and similar network commands
- Identify network connectivity in container builds
- Recommend network restriction strategies

### 8. Semantic versioning
- Implement semantic versioning in SKILL output
- Provide version information in reports
- Update version with each new release

### 9. Hash-pinned base images (all runtimes)
Every `FROM` instruction must reference its base image by an immutable `@sha256:<digest>` digest, not by a floating tag. This rule applies uniformly across runtimes — language ecosystem does not change the requirement.

**Detection rules:**
- Flag any `FROM <image>:<tag>` reference that lacks `@sha256:<64 hex chars>`.
- Tags like `:latest`, `:latest-dev`, `:3`, `:3.13`, `:20`, `:1.22`, `:21-jdk`, `:1.75-slim` are all violations on their own — they are mutable upstream.
- `FROM scratch` is exempt (no image to pin).
- `FROM <alias>` referencing a prior `AS <alias>` build stage is exempt (the alias resolves to an already-pinned image earlier in the file).
- A `--platform=...` prefix does not change the rule; the image reference still must include `@sha256:...`.

**Runtime coverage — report violations identically for any of these (non-exhaustive):**
| Runtime | Common base images to check |
| --- | --- |
| Python | `python`, `cgr.dev/chainguard/python`, `python-slim` |
| Node.js | `node`, `cgr.dev/chainguard/node`, `node-alpine` |
| Go | `golang`, `cgr.dev/chainguard/go`, `cgr.dev/chainguard/static` |
| Rust | `rust`, `cgr.dev/chainguard/rust`, `rust-slim` |
| Java / JVM | `eclipse-temurin`, `openjdk`, `amazoncorretto`, `cgr.dev/chainguard/jdk`, `cgr.dev/chainguard/jre` |
| Ruby | `ruby`, `cgr.dev/chainguard/ruby` |
| .NET | `mcr.microsoft.com/dotnet/sdk`, `mcr.microsoft.com/dotnet/runtime`, `cgr.dev/chainguard/dotnet-runtime` |
| Generic / distroless | `alpine`, `debian`, `ubuntu`, `cgr.dev/chainguard/wolfi-base`, `gcr.io/distroless/*` |

**Why:** Tags are mutable; the image bytes behind `python:3.13-slim` today are not the bytes behind it next week. Digest pinning gives reproducible builds, makes supply-chain attacks visible (a different digest = a different image), and is required for meaningful SBOM and provenance attestation.

**Reporting format:** When a violation is found, output:
- The exact `FROM` line and line number.
- The current tag-only reference.
- A concrete fix: `FROM <image>@sha256:<digest>` — and instructions to obtain the digest with `docker pull <image>:<tag> && docker inspect --format='{{index .RepoDigests 0}}' <image>:<tag>` (or `crane digest <image>:<tag>` / `regctl image digest <image>:<tag>`).
- A note recommending automated pin rotation (Dependabot, Renovate) so pins don't go stale.

**Severity:** MEDIUM by default; HIGH for production / published images.

### 10. No public package registries (all runtimes)
Packages installed during `docker build` must be pulled from a known, controlled internal registry — never from a public open-source registry directly. Public registries (PyPI, npm, crates.io, Maven Central, RubyGems, NuGet.org, the public Go module proxy, default `apt`/`apk` mirrors) are routinely abused for dependency-confusion, typosquatting, account-takeover, and post-install malware. An internal proxy (Artifactory, Nexus, AWS CodeArtifact, GCP Artifact Registry, Azure Artifacts, GitHub Packages, or a Verdaccio / devpi / Athens / Sonatype mirror) provides quarantine, vetting, audit logging, and CVE blocking.

**Detection rules:**
Flag any `RUN` line that invokes a package installer **without** evidence that it has been redirected to an internal registry. Evidence of redirection can be any one of:
- An explicit flag on the command: `--index-url`, `--extra-index-url`, `--registry`, `-i`, `--repository`, `GOPROXY=...`, `--source`, `-s`.
- A Dockerfile `ENV` (or `ARG` exposed as env) set **earlier in the same stage** with one of the recognized variables below.
- A registry/config file COPY'd into the build context **before** the install step (e.g. `.npmrc`, `pip.conf`, `.cargo/config.toml`, `nuget.config`, `~/.gemrc`, `settings.xml`, `gradle.properties`).

If none of those are present, the installer is hitting the upstream public default → violation.

**Per-runtime detection map:**
| Runtime | Installer commands to flag | Acceptable redirection signals |
| --- | --- | --- |
| Python | `pip install`, `pip3 install`, `python -m pip install`, `poetry install`, `poetry add`, `uv pip install`, `uv sync`, `pipenv install`, `conda install` | `--index-url=...` / `-i ...`, `PIP_INDEX_URL`, `PIP_EXTRA_INDEX_URL`, `UV_INDEX_URL`, `POETRY_REPOSITORIES_*_URL`, COPY of `pip.conf` / `pyproject.toml` with `[[tool.poetry.source]]` |
| Node.js | `npm install`, `npm ci`, `npm i`, `yarn install`, `yarn add`, `pnpm install`, `pnpm add` | `--registry=...`, `NPM_CONFIG_REGISTRY`, `YARN_NPM_REGISTRY_SERVER`, COPY of `.npmrc` / `.yarnrc.yml` |
| Go | `go build`, `go get`, `go install`, `go mod download`, `go mod tidy` | `GOPROXY=<internal>`, `GONOSUMCHECK=off` only with internal GOSUMDB, COPY of `go.env` |
| Rust | `cargo build`, `cargo install`, `cargo fetch`, `cargo update` | COPY of `.cargo/config.toml` with `[source.crates-io] replace-with = "internal"`, `CARGO_REGISTRIES_*_INDEX` env, `--registry <name>` |
| Java / JVM | `mvn install`, `mvn package`, `mvn dependency:resolve`, `./gradlew build`, `./gradlew dependencies`, `sbt update` | COPY of `settings.xml` with `<mirrors>`, `MAVEN_OPTS` pointing at internal, `gradle.properties` with internal `repositories`, `init.gradle` mirror |
| Ruby | `gem install`, `bundle install`, `bundle update` | `--source <internal>`, `BUNDLE_MIRROR__*`, COPY of `.gemrc` / `.bundle/config` |
| .NET | `dotnet restore`, `dotnet add package`, `dotnet build`, `nuget install`, `nuget restore` | `--source <internal>`, `-s <internal>`, COPY of `nuget.config` with internal `<add key="..." value="..."/>` |
| OS packages (apt/apk/dnf/yum) | `apt-get install`, `apt install`, `apk add`, `dnf install`, `yum install`, `microdnf install`, `zypper install` | COPY of `sources.list` / `/etc/apt/sources.list.d/*.list` / `/etc/apk/repositories` / `*.repo` pointing at internal mirror **before** the install |

**Exemptions:**
- `RUN` lines that install only from a path or local file (`pip install ./vendor/wheel.whl`, `npm install ./packages/foo.tgz`, `dpkg -i ./*.deb`) — no registry contacted.
- Multi-stage builds where a prior stage produced a fully-vendored artifact and the final stage runs no installer.
- Air-gapped builds where the network is provably unavailable (BuildKit `--network=none`); flag as INFO instead of MEDIUM in that case.

**Reporting format:**
- The exact `RUN` line and line number.
- The installer detected (e.g., `pip install`, `npm ci`).
- The default public registry it will hit (`pypi.org`, `registry.npmjs.org`, `crates.io`, `proxy.golang.org`, `repo.maven.apache.org`, `rubygems.org`, `api.nuget.org`).
- Concrete fix: a redirected invocation **and** the preferred approach of baking the registry into a config file COPY'd in earlier so the command line stays clean:
  ```dockerfile
  # Preferred: ship config, keep the install command unchanged
  COPY .npmrc /root/.npmrc           # contains: registry=https://npm.internal.example.com/
  RUN npm ci

  # Alternative: flag the install directly
  RUN pip install --index-url https://pypi.internal.example.com/simple/ -r requirements.txt
  ```
- A note that the internal registry itself must be configured to mirror, scan, and quarantine upstream packages — pointing the build at an unconfigured proxy is not sufficient.

**Severity:** HIGH for production / published images (supply-chain risk is the single largest attack vector against container builds). MEDIUM for ephemeral / local test images.

## Dockerfile Analysis and Recommendations

### Analysis Components:
- **Base Image Check**: Verify base image quality, security updates, recommended chainguard alternatives
- **Build Process**: Multi-stage build detection, build-time vs runtime dependencies
- **User Rights**: User privilege checks, non-root process execution
- **Security Profile**: Privilege level, process management, network access
- **Script Usage**: Shell script detection and recommendations
- **Network Access**: Outbound connectivity restrictions

### Recommendation Engine:
- Generate detailed reports for each Dockerfile
- Prioritize security issues based on severity
- Provide actionable fix recommendations
- Include links to relevant documentation via Context7

## Testing Approach
Text-based testing using SKILL prompts
- Validation of analysis prompt accuracy
- Verification of security recommendation quality
- Test cases covering both insecure and secure examples

## Marketplace Configuration
plugin.json - Plugin manifest for Claude marketplace
marketplace.json - Marketplace entry for plugin discovery

## Documentation Integration
Use Context7 for:
- Security best practices documentation lookup
- Dockerfile best practices and standards
- Chainguard documentation
- Container security guidelines

## Version Information
- Version: 1.0.0
- Release Date: May 2026
- Compatible with Claude and Kilo platforms

## Implementation Details

### Core Components:
1. **plugin.json** - Plugin manifest with metadata
2. **SKILL.md** - Main skill definition with AI prompts
3. **references/** - Security documentation and guidelines

### Features:
- Natural language prompt-based Dockerfile analysis
- AI-powered security rule enforcement based on industry standards
- Integration with Context7 for up-to-date security guidance
- Detailed reporting with actionable recommendations
- Pure text-based solution without Python code