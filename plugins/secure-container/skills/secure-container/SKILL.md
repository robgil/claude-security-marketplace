---
name: Secure Container Creation
description: Analyze Dockerfiles and provide recommendations for creating secure containers following best practices
version: 1.0.0
---

# Secure Container Creation SKILL

This SKILL helps create secure containers by analyzing Dockerfiles and providing recommendations for hardening container security.

## Compliance frameworks this skill maps to

Every finding the skill reports is tagged with one or more control identifiers from the frameworks below. The full per-rule mapping appears in each rule's `Maps to:` line; the full citation source list and reporting format live in the "Reporting format" section further down. This summary exists so a reader knows up-front which catalogs the skill speaks.

- **NIST CSF 2.0** — primarily GV.SC (Supply Chain Risk Management), PR.AA (Access Control), PR.DS (Data Security), PR.PS (Platform Security — new in 2.0), PR.IR (Infrastructure Resilience), ID.AM/ID.RA (Asset Management / Risk Assessment).
- **NIST SP 800-190** — Application Container Security Guide (the container-specific NIST publication).
- **NIST SP 800-53 Rev. 5** — see the most-cited controls table below.
- **NIST SSDF (SP 800-218)** — PO / PS / PW / RV practices.
- **CIS Docker Benchmark** — sections 4 (Container Images) and 5 (Container Runtime).
- **FedRAMP** — Vulnerability Scanning Requirements for Containers (when in scope).
- **FIPS 140-2 / 140-3** — for cryptographic mode (Rule #14).
- **DISA STIG**, **NSA/CISA Kubernetes Hardening Guide**, **OWASP Docker Top 10**, **SLSA** — cited where applicable.

### Most-cited NIST 800-53 controls in this skill

The two controls that drive the largest number of findings are **AC-6 (Least Privilege)** and **CM-7 (Least Functionality)** — every form of "this doesn't belong in a production container" maps to one or both. The full table:

| Control | Family | What it means here | Rules |
| --- | --- | --- | --- |
| **AC-6 — Least Privilege** | Access Control | Non-root execution, no interactive admin path, restricted credential holders. | #3, #4, #6, #11, #12 |
| **CM-7 — Least Functionality** | Configuration Management | Only what the application needs. No build tools, no shells, no daemons, no diagnostic utilities, no extra package sources in the final image. | #2, #5, #6, #7, #10, #12, #13, #14 |
| CM-2 — Baseline Configuration | Configuration Management | The image's exact bytes are the baseline; digest pinning makes that concrete. | #9 |
| CM-6 — Configuration Settings | Configuration Management | Entrypoint form, FIPS mode, USER directive are configuration properties. | #3, #5, #6, #14 |
| CM-8 — System Component Inventory | Configuration Management | Knowing what's in the image at the byte level (paired with #9). | #9 |
| CM-11 — User-Installed Software | Configuration Management | Controlling what packages can be installed at build time. | #10, #13 |
| AC-17 — Remote Access | Access Control | Removed at the image level (no SSH server). | #12 |
| IA-5 — Authenticator Management | Identification & Authentication | Credentials must not live in image layers. | #11 |
| SC-7 — Boundary Protection | System & Communications Protection | Hermetic builds, no arbitrary outbound fetches at build time. | #7 |
| SC-8 — Transmission Confidentiality | System & Communications Protection | FIPS-validated crypto for TLS. | #14 |
| SC-12 — Cryptographic Key Establishment | System & Communications Protection | Secrets and key material handling. | #11, #14 |
| SC-13 — Cryptographic Protection | System & Communications Protection | FIPS mode for cryptographic operations. | #14 |
| SC-18 — Mobile Code | System & Communications Protection | `curl \| sh` patterns are mobile code execution. | #7 |
| SC-28 — Protection of Information at Rest | System & Communications Protection | Secrets in image layers are unprotected at rest. | #11, #14 |
| SR-3 — Supply Chain Controls and Processes | Supply Chain Risk | Trusted base images, trusted package registries. | #1, #7, #9, #10, #13 |
| SR-4 — Provenance | Supply Chain Risk | Knowing where an image came from (digest + signed registry). | #9, #13 |
| SR-5 — Acquisition Strategies, Tools, Methods | Supply Chain Risk | Approved sources for images and packages. | #10, #13 |
| SR-6 — Supplier Assessments and Reviews | Supply Chain Risk | The supplier behind the base image / package registry has been vetted. | #10, #13 |
| SR-9 — Tamper Resistance and Detection | Supply Chain Risk | Digest mismatch reveals tampering. | #9 |
| SR-10 — Inspection of Systems or Components | Supply Chain Risk | Scanning + manifest inspection of pinned images. | #9 |
| SR-11 — Component Authenticity | Supply Chain Risk | Digest + signature prove authenticity. | #1, #9, #10, #13 |
| SA-15 — Development Process, Standards, Tools | System & Services Acquisition | Build-time secret handling and tooling. | #11 |

A finding may cite additional controls in its `Refs:` line — this table covers the ones that recur.

## Requirements Implemented

### 1. Use Chainguard (or equivalent purpose-built minimal base) when possible
- Analyze Dockerfiles for Chainguard base images.
- Recommend Chainguard alternatives for base images that are general-purpose or community-distributed.
- Distroless (`gcr.io/distroless/*`) and `FROM scratch` (for statically compiled binaries) are acceptable peers — see Rule #13 for the approved-registries allow-list.
- Check for latest security updates in Chainguard images.
- Maps to: **CSF 2.0 GV.SC-04, GV.SC-05, ID.RA-09, PR.PS-01, PR.PS-05** · **NIST 800-190 §4.5** (Use of untrusted images) · **NIST 800-53 SR-3, SR-11** · **SSDF PW 4.1**.

### 2. Multi-stage builds — no build tooling in the final image
- Identify base images used for build vs runtime; require a multi-stage build when any build tooling is installed.
- Recommend multi-stage approaches that separate build-time dependencies from the runtime image.
- The **final stage** must contain only: the language runtime, application binaries, application static assets, and the entrypoint. Nothing else.
- Flag the presence of any of the following in the final stage (installed via `apt`/`apk`/`dnf`/`pip`/`npm`/`gem`/`cargo`/`go install`, or copied in):
  - **Compilers / build systems:** `gcc`, `g++`, `clang`, `make`, `cmake`, `autoconf`, `automake`, `libtool`, `pkg-config`, `meson`, `ninja`, `bazel`, `sbt`, `maven`, `gradle`, `cargo` (the build subcommand, not just the binary), `go build` toolchain, `rustc`.
  - **Debuggers / profilers / tracers:** `gdb`, `lldb`, `strace`, `ltrace`, `perf`, `valgrind`, `tcpdump`.
  - **Header / development packages:** `*-dev`, `*-devel`, `build-essential`, `linux-headers-*`, `kernel-devel`.
  - **Package managers at runtime:** `pip` / `pip3` (when no install step needs them), `npm` / `yarn` / `pnpm` (in a runtime image), `cargo` / `rustup`, `gem`, `bundle`, `mvn`, `gradle`, `apt-get` / `apk` / `dnf` themselves remaining in the final stage when no further installs occur.
  - **Source code or `.git/` directories** copied into the final stage (these belong in the builder stage only).
- For statically-compiled languages (Go, Rust, sometimes Java native-image), prefer `FROM scratch`, `gcr.io/distroless/static`, or `cgr.dev/chainguard/static` as the final stage — no userland at all.
- Maps to: **CSF 2.0 PR.PS-01, PR.PS-05, PR.PS-06** · **NIST 800-190 §4.1, §4.5** · **CIS Docker Benchmark 4.5** · **NIST 800-53 CM-7** (Least Functionality) · **SSDF PW 4.4**.

### 3. Non-root user usage
- Check for explicit `USER` directive usage with a UID > 0 in the final stage.
- Flag the absence of `USER` — relying on a base image's default `nonroot` is fragile (a base-image change can silently regress to root).
- Verify the application is invoked as a non-root user; recommend `USER appuser:appuser` or `USER 65532:65532` (the conventional `nonroot` UID).
- Flag explicit `USER root` or `USER 0` in the final stage (acceptable in the *builder* stage when necessary for installation).
- Maps to: **CSF 2.0 PR.AA-05** (Access permissions and authorizations defined / least privilege) · **CIS Docker Benchmark 4.1** (Create a user for the container) · **NIST 800-190 §4.5** · **NIST 800-53 AC-6** (Least Privilege) · **SSDF PW 4.1**.

### 4. Privileged mode and capabilities
- Privileged mode is a runtime flag (`docker run --privileged`) — flag any documentation, `docker-compose.yml`, or Kubernetes manifest in the repo that sets it.
- In the Dockerfile, flag `LABEL` declarations that signal privileged intent (`LABEL com.example.privileged="true"`).
- Recommend dropping all capabilities and adding back only what's needed: `--cap-drop=ALL --cap-add=NET_BIND_SERVICE` (or equivalent).
- Recommend `--read-only` rootfs with explicit `tmpfs` for `/tmp` and any required writable paths.
- Recommend `--security-opt=no-new-privileges:true`.
- Recommend a seccomp profile (the Docker default is a meaningful improvement over none).
- Maps to: **CSF 2.0 PR.AA-05, PR.PS-01, PR.IR-01** (least privilege, configuration management, infrastructure protection) · **CIS Docker Benchmark 5.4, 5.12, 5.25** (privileged, read-only rootfs, restrict additional privileges) · **NIST 800-190 §5.3** (Container risks) · **NIST 800-53 AC-6, CM-7** (Least Privilege, Least Functionality) · **NSA/CISA Kubernetes Hardening Guide** §Pod Security.

### 5. Shell scripts and shell-form entrypoints
Two related problems: (a) shell *scripts* shipped into the image as the entrypoint, and (b) shell-*form* `ENTRYPOINT` / `CMD` instructions that implicitly spawn `/bin/sh -c`.

**(a) Shell scripts as entrypoints**
- Flag any `ENTRYPOINT` / `CMD` that points at a `.sh` file copied into the image (`ENTRYPOINT ["/entrypoint.sh"]`, `CMD ["./run.sh"]`, etc.).
- Flag any `COPY *.sh` or `ADD *.sh` paired with execution at container start.
- Recommend invoking the language runtime directly (`ENTRYPOINT ["python", "-m", "myapp"]`, `ENTRYPOINT ["node", "server.js"]`, `ENTRYPOINT ["./myapp"]` for a static binary). Shell scripts pull in a shell and its dependencies, bloat the image, and create signal-handling problems at PID 1.

**(b) Shell-form vs exec-form**
- Flag `ENTRYPOINT some_command arg1 arg2` (shell form — string, no JSON array).
- Flag `CMD some_command arg1 arg2` (shell form).
- Require exec form: `ENTRYPOINT ["some_command", "arg1", "arg2"]`.

Why exec form matters:
- Shell form runs as `/bin/sh -c "some_command arg1 arg2"`, which requires `/bin/sh` to exist in the image (fights Rule #2's minimal-image goal — `FROM scratch` and most distroless images don't have a shell).
- The shell becomes PID 1, intercepts signals (`SIGTERM`, `SIGINT`), and typically does not forward them to the child. Container takes 10s to die instead of exiting cleanly on `docker stop`.
- Exec form makes the application PID 1 directly, with proper signal handling.

Exemption: If a wrapper is genuinely required (init-style supervision, signal proxying), use `tini` or `dumb-init` as PID 1 rather than a bash script — `ENTRYPOINT ["/sbin/tini", "--", "myapp"]`.

- Maps to: **CSF 2.0 PR.PS-01, PR.PS-05** (configuration management, prevent unauthorized software) · **NIST 800-190 §4.1, §4.5** · **NIST 800-53 CM-7** (Least Functionality — no shell required in runtime image), **CM-6** (Configuration Settings — entrypoint form is a configuration property) · **CIS Docker Benchmark 4.6** (use HEALTHCHECK) · **OCI Runtime spec** signal-handling expectations.

### 6. Single process containers
- Verify the container runs only one application process (one logical responsibility per container).
- Identify multi-process configurations: `supervisord` as the entrypoint, `&` backgrounded processes in a shell-form entrypoint, init systems (see Rule #12), wrapper scripts that fork multiple long-running daemons.
- For genuine "init shim" needs (signal forwarding, zombie reaping), recommend `tini` or `dumb-init` as PID 1 — these are not multi-process supervisors.
- For multi-process needs, recommend splitting into multiple containers (sidecars in Kubernetes, separate services in compose) rather than co-locating processes.
- Maps to: **CSF 2.0 PR.PS-01, PR.PS-05** (configuration management, prevent unauthorized software) · **NIST 800-53 CM-7** (Least Functionality — one process per container), **AC-6** (Least Privilege — fewer processes = smaller authorization surface), **CM-6** (Configuration Settings) · **CIS Docker Benchmark 4.6** (HEALTHCHECK) · **NIST 800-190 §4.5, §5.3** · **NSA/CISA Kubernetes Hardening Guide** (single-purpose containers).

### 7. Outbound network calls and hermetic builds
- Flag `RUN curl ... | sh`, `RUN wget ... -O - | bash`, `RUN curl ... | python` — these are arbitrary remote code execution at build time and bypass every scanner.
- Flag `RUN curl`/`RUN wget` fetching arbitrary tarballs/binaries from non-allow-listed URLs (anything outside the org's package mirror — see Rule #10).
- Recommend BuildKit's `--network=none` for stages that should be hermetic (no internet, packages must come from explicit COPY or earlier-stage outputs). This is a SLSA Build L3 requirement.
- Flag runtime images that ship `curl`, `wget`, `nc`, `nmap`, `dig`, `ssh-client` when no application code calls them — these expand the post-exploitation toolkit available to an attacker who lands inside the container.
- Maps to: **CSF 2.0 GV.SC-05, GV.SC-09, PR.IR-01, PR.PS-06** (supply chain controls, network protection, secure dev practices) · **NIST 800-190 §4.5** · **NIST 800-53 SC-7** (Boundary Protection), **CM-7** (Least Functionality — no diagnostic / fetch tools in runtime image), **SR-3** (Supply Chain Controls — applied to mid-build fetches), **SC-18** (Mobile Code — `curl | sh` is mobile code execution) · **SSDF PW 4.4** (Reuse Existing, Well-Secured Software) · **SLSA Build L3** (Hermetic, Reproducible Builds) · **CIS Docker Benchmark 4.5**.

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

- Maps to: **CSF 2.0 ID.AM-02, ID.RA-09, GV.SC-05, GV.SC-06, PR.PS-01** (software inventory, authenticity/integrity, supplier requirements, due diligence, configuration management) · **NIST 800-190 §4.1, §4.5** · **NIST 800-53 CM-2** (Baseline Configuration), **CM-8** (System Component Inventory), **SR-3** (Supply Chain Controls), **SR-4** (Provenance), **SR-9** (Tamper Resistance and Detection), **SR-10** (Inspection of Systems or Components), **SR-11** (Component Authenticity) · **SSDF PW 4.1, RV 1.1** · **SLSA Build L2** (Provenance) · **CIS Docker Benchmark 4.2**.

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

- Maps to: **CSF 2.0 GV.SC-04, GV.SC-05, GV.SC-07, GV.SC-09, ID.RA-10, PR.PS-06, PR.IR-01** (known suppliers, supplier requirements, third-party risk, supply chain integration, critical supplier assessment, secure dev practices, infrastructure protection) · **NIST 800-190 §4.5, §4.6** · **NIST 800-53 SR-3** (Supply Chain Controls and Processes), **SR-5** (Acquisition Strategies, Tools, and Methods), **SR-6** (Supplier Assessments and Reviews), **SR-11** (Component Authenticity), **CM-7** (Least Functionality — only authorized package sources), **CM-11** (User-Installed Software) · **SSDF PO 1.1, PW 4.1, PW 4.4** · **FedRAMP Vulnerability Scanning Requirements for Containers**.
Secrets (API keys, tokens, passwords, private keys, kubeconfigs, cloud credentials, signing keys) must never be present in any image layer. Layers are immutable and additive — a secret `COPY`'d in stage 1 and "deleted" in stage 2 of a single-stage build is still recoverable from the earlier layer; only a fresh stage that never received the secret is clean.

**Detection rules — flag any of the following:**
- `ENV` lines whose value matches a secret pattern:
  - Name matches `*_KEY`, `*_SECRET`, `*_TOKEN`, `*_PASSWORD`, `*_PASSWD`, `*_PWD`, `*_CREDENTIALS`, `*_API_KEY`, `*_PRIVATE_KEY`.
  - Value matches AWS access key ID format (`AKIA[0-9A-Z]{16}`), AWS secret access key shape (40 base64 chars), GitHub PAT (`ghp_`, `gho_`, `ghs_`, `github_pat_`), Slack tokens (`xox[baprs]-`), JWT shape (`eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\..*`), Stripe keys (`sk_live_`, `pk_live_`), Google API key shape (`AIza[0-9A-Za-z\-_]{35}`), generic 32+ char hex / base64 high-entropy strings.
- `ARG` declarations used to *bake* a secret value into the final image (`ARG GITHUB_TOKEN` followed by `RUN ... $GITHUB_TOKEN ...` in the same stage without BuildKit secret mount — the value persists in build history).
- `COPY` / `ADD` of credential files:
  - `.env`, `.env.*` (except `.env.example`, `.env.template`).
  - Private keys: `id_rsa`, `id_ed25519`, `id_ecdsa`, `*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.jks`.
  - Cloud credentials: `.aws/credentials`, `.aws/config`, `gcp-*.json` (service-account JSON shape), `azure-credentials*`, `*.kubeconfig`, `kubeconfig`.
  - Cert authorities with private material: `*-key.pem`, `private/*.pem`.
- `RUN` lines containing inline credentials:
  - `curl -H "Authorization: Bearer ey..."`, `curl -u user:password`.
  - `git clone https://<user>:<token>@github.com/...`.
  - `wget --header="X-API-Key: ..."`.
  - `echo "<token>" | docker login --password-stdin` followed by leftover env.
- `LABEL` values containing secret-shaped strings.

**The fix — BuildKit secret mounts:**
```dockerfile
# syntax=docker/dockerfile:1.7
FROM cgr.dev/chainguard/python@sha256:...
RUN --mount=type=secret,id=pip_token \
    pip install --extra-index-url https://$(cat /run/secrets/pip_token)@pypi.internal.example.com/simple/ -r requirements.txt
```
Build with: `docker build --secret id=pip_token,src=$HOME/.pip-token .` — the secret is mounted only for that `RUN` and never written to any layer.

**Exemptions:**
- Public certificates (`ca-certificates`, public root CA bundles, `*.crt` without matching `*.key`) — these are *meant* to be public.
- Example / template env files (`.env.example`, `.env.template`, `*.env.sample`) — pattern-match the suffix.
- Test fixtures inside `tests/` directories explicitly marked as fake — but still warn (INFO level) since they create habits.

**Runtime guidance (recommendation, not a Dockerfile violation):** Even production credentials should come from workload-identity systems at runtime (IRSA on AWS, Workload Identity on GCP, Managed Identity on Azure, SPIFFE/SPIRE for hybrid) — not baked, not mounted from disk, not in env vars set by an orchestrator.

- Maps to: **CSF 2.0 PR.AA-01, PR.DS-01, PR.DS-10, PR.PS-01** (credential management, data-at-rest confidentiality, data-in-use confidentiality, configuration management) · **NIST 800-190 §4.4** (Embedded clear text secrets) · **NIST 800-53 IA-5** (Authenticator Management), **AC-6** (Least Privilege — restricts who/what holds credentials), **SC-12** (Cryptographic Key Establishment), **SC-28** (Protection of Information at Rest), **SA-15** (Development Process, Standards, and Tools) · **SSDF PW 1.2** (Protect all forms of code from unauthorized access and tampering) · **CIS Docker Benchmark 4.10** (Do not store secrets in Dockerfiles).

**Severity:** HIGH (any production-shaped secret); MEDIUM (test fixtures, low-value tokens).

### 12. No SSH server, init system, or PAM stack in the final image
Production containers run a single application process. They are not VMs. They do not need remote shell access, an init system, or pluggable authentication. Each of these adds a meaningful attack surface and a non-zero footprint, contradicts Rule #6 (single process), and indicates the image is being treated as a long-lived host instead of an immutable artifact.

**Detection rules — flag any of the following in the final stage:**
- **SSH server / daemon:**
  - Package installs: `openssh-server`, `openssh-sftp-server`, `dropbear`, `ssh-server`.
  - Binaries present: `/usr/sbin/sshd`, `/usr/bin/dropbear`.
  - Config files copied: `/etc/ssh/sshd_config`, `/etc/dropbear/`.
  - `EXPOSE 22` paired with anything that runs `sshd`.
- **Init systems / process supervisors that imply multi-process intent:**
  - `systemd`, `systemd-*` packages, `/usr/lib/systemd`, `/usr/bin/systemctl` present.
  - `sysvinit-core`, `openrc`, `runit`, `s6` (when used as a full init, not as a `tini`-style PID 1).
  - `supervisord` / `supervisor` (the package, not just supervisord-style logging in an app).
- **PAM stack:**
  - Packages: `libpam-*`, `pam-*`, `libpam0g`, `libpam-modules`.
  - Files: `/etc/pam.d/`, `/etc/pam.conf`.
  - Linking against `libpam.so` (when no human will ever authenticate to this image).

**Permitted with justification (warn but don't block):**
- **SSH *client*** (`openssh-client`, `/usr/bin/ssh`) — occasionally legitimate for outbound scp/sftp to fetch artifacts. Warn (INFO) and recommend reviewing whether the call belongs in CI/CD instead.
- **`tini` / `dumb-init`** as PID 1 — explicitly *not* an init system in the multi-process sense; this is a signal-forwarding shim and is encouraged by Rule #5.

**The fix:**
- Remove the package from the install line, or move it to the builder stage if used at build time only.
- For "I need to debug a running container" — use `kubectl debug` / `kubectl exec` / `docker exec`, ephemeral debug containers, or sidecar debug containers, not a persistent `sshd`.
- For multi-process needs — split into multiple containers (separate pods/services), not multiple processes in one container.

- Maps to: **CSF 2.0 PR.AA-05, PR.PS-05, PR.IR-01** (least-privilege access permissions, prevent unauthorized software, infrastructure protection from unauthorized logical access) · **NIST 800-190 §4.5** (Use of untrusted images / minimization) · **NIST 800-53 CM-7** (Least Functionality — these components are not required for the container's mission), **AC-6** (Least Privilege — no interactive admin path), **AC-17** (Remote Access — removed at the image level), **CM-7(1)** (Periodic review and removal of unnecessary functions) · **CIS Docker Benchmark 4.5** (Do not install unnecessary packages) · **NSA/CISA Kubernetes Hardening Guide** (single-purpose containers).

**Severity:** HIGH (SSH server, systemd in production); MEDIUM (PAM, supervisord); INFO (SSH client).

### 13. Base images must come from approved registries (no DockerHub, no community distros)
The base image is the largest single contributor to a container's attack surface and patch burden. It must come from a registry and distribution that the organization explicitly trusts and has procurement/support for. DockerHub `library/*` images, arbitrary community pushes, and general-purpose OS bases designed for hardware/VMs all fail this test.

**Detection rules — flag any `FROM` matching the following:**
- **No registry prefix** (defaults to `docker.io/library/...`):
  - `FROM alpine`, `FROM debian`, `FROM ubuntu`, `FROM centos`, `FROM rockylinux`, `FROM almalinux`, `FROM fedora`, `FROM amazonlinux`, `FROM python`, `FROM node`, `FROM golang`, `FROM rust`, `FROM eclipse-temurin`, `FROM ruby`, etc. — all DockerHub.
- **Explicit DockerHub references:**
  - `FROM docker.io/...`, `FROM index.docker.io/...`, `FROM registry.hub.docker.com/...`.
- **Community / general-purpose OS bases regardless of registry:**
  - `alpine`, `debian`, `ubuntu`, `centos`, `rockylinux`, `almalinux`, `fedora`, `amazonlinux`, `opensuse/leap` — these are designed for hardware/VMs and inherit dependency graphs (OpenSSL in the base, PAM, systemd hooks) that bloat container images and aren't purpose-built for the container model.

**Approved registries (allow-list — adjust per organization):**
- Chainguard: `cgr.dev/chainguard/*`, `cgr.dev/chainguard-private/*`.
- Google distroless: `gcr.io/distroless/*`.
- Red Hat Universal Base Images: `registry.access.redhat.com/ubi*`, `registry.redhat.io/ubi*`.
- Microsoft (when justified for .NET): `mcr.microsoft.com/dotnet/*`.
- The organization's own internal registry (configurable): `<your-registry>.example.com/*`, `<account>.dkr.ecr.<region>.amazonaws.com/*`, `<region>-docker.pkg.dev/<project>/*`, `<acr-name>.azurecr.io/*`.
- `FROM scratch` — always allowed (no base).

**Recommended replacement matrix:**
| Common public base | Approved replacement |
| --- | --- |
| `python:*` (DockerHub) | `cgr.dev/chainguard/python` |
| `node:*` | `cgr.dev/chainguard/node` or `gcr.io/distroless/nodejs*` |
| `golang:*` → final stage | `FROM scratch` (for static binaries) or `cgr.dev/chainguard/static` |
| `rust:*` → final stage | `FROM scratch` or `cgr.dev/chainguard/static` |
| `eclipse-temurin:*-jre` | `cgr.dev/chainguard/jre` or `gcr.io/distroless/java*` |
| `ruby:*` | `cgr.dev/chainguard/ruby` |
| `alpine` | `cgr.dev/chainguard/wolfi-base` (purpose-built peer to Alpine) |
| `debian` / `ubuntu` | `registry.access.redhat.com/ubi9-minimal` or `cgr.dev/chainguard/wolfi-base` |

**Reporting format:**
- The exact `FROM` line and line number.
- Why the current base is rejected (DockerHub / community distro / unsupported).
- The recommended approved replacement from the matrix above.
- A note that this rule pairs with Rule #9 (digest pinning) — the approved replacement must still be pinned by `@sha256:...`.

**Configuration:** The approved-registry allow-list and per-runtime replacement matrix should be configurable per organization (e.g., `secure-container.config.yaml`). The defaults reflect a "no commercial-vendor commitment" stance; orgs with RHEL subscriptions can promote `registry.access.redhat.com/*` higher, etc.

- Maps to: **CSF 2.0 GV.SC-04, GV.SC-05, GV.SC-06, GV.SC-07, ID.RA-09, ID.RA-10, PR.PS-05** (known/prioritized suppliers, supplier requirements, due diligence, third-party risk, authenticity, supplier risk, prevent unauthorized software) · **NIST 800-190 §4.5, §4.6** (Use of untrusted images, Registry security) · **NIST 800-53 SR-3** (Supply Chain Controls and Processes), **SR-4** (Provenance), **SR-5** (Acquisition Strategies), **SR-6** (Supplier Assessments), **SR-11** (Component Authenticity), **CM-7** (Least Functionality — limit to approved sources), **CM-11** (User-Installed Software — applied to base images) · **SSDF PO 1.1, PW 4.1** (define security requirements, reuse from approved sources) · **FedRAMP Vulnerability Scanning Requirements for Containers**.

**Severity:** HIGH for production / regulated images; MEDIUM for internal tooling.

### 14. FIPS-compliant base when regulated context is declared
Workloads subject to FIPS 140-2/140-3 requirements (FedRAMP, DoD, parts of HIPAA, parts of PCI in regulated geographies, contracts that incorporate FIPS by reference) must use a base image whose cryptographic libraries are FIPS-validated. Non-FIPS bases ship OpenSSL builds whose validation does not apply, which silently breaks compliance.

**Detection rules (conditional):**
Active only when the user or configuration declares a FIPS-required context. Signals that activate the check:
- A repository-level config flag (`secure-container.config.yaml: requireFips: true`).
- A Dockerfile `LABEL` declaring compliance scope:
  - `LABEL compliance.fips="required"` or `LABEL org.opencontainers.image.compliance="fips-140-3"`.
  - `LABEL fedramp.scope="moderate"` / `"high"` (FedRAMP implies FIPS).
- A repo-level marker file (`.fips-required`, or `compliance.yaml` with `fips: required`).
- The user explicitly asks for FIPS-mode analysis in the prompt.

When active, **require** the base image to be a FIPS variant. Detection:
- Image tag or name must include `-fips`, `-fips140`, `fips-`, or be on the FIPS allow-list:
  - Chainguard: `cgr.dev/chainguard/*-fips` (e.g., `cgr.dev/chainguard/python-fips`, `cgr.dev/chainguard/jre-fips`, `cgr.dev/chainguard/go-fips`).
  - Red Hat UBI: `registry.access.redhat.com/ubi9/ubi-minimal` *with* the `MODE=fips` boot configuration documented in `LABEL`, plus FIPS-validated OpenSSL.
  - Microsoft: `mcr.microsoft.com/dotnet/*` variants documented as FIPS-mode.
- Flag any `FROM` that's clearly non-FIPS (`*:latest`, `*:slim`, `*-dev` without `-fips`) when FIPS context is active.

Additional FIPS hygiene checks when active:
- Flag explicit disabling of FIPS mode: `ENV OPENSSL_FIPS=0`, `RUN ... --disable-fips`, golang `GODEBUG=fips140=off`.
- Flag any installation of non-FIPS crypto libraries (`libsodium` without FIPS build, custom `openssl` builds from source without `enable-fips`).
- Recommend documenting FIPS mode activation in a `LABEL` so downstream auditors can confirm without rebuilding.

**Reporting format:**
- The active FIPS-context signal that triggered the check (so the user sees why it fired).
- The non-FIPS base detected.
- The recommended FIPS variant from the allow-list.
- A reminder that using a FIPS image is necessary but not sufficient — the application must also be configured to use the FIPS-validated providers (e.g., Go's `GOFIPS=1`, OpenSSL FIPS provider loaded).

**Severity when active:** HIGH (FIPS is a binary compliance state — non-compliant images fail audits). INFO when context not declared.

- Maps to: **CSF 2.0 PR.DS-01, PR.DS-02, PR.PS-01** (confidentiality and integrity of data at rest and in transit; configuration management of cryptographic mode) · **FIPS 140-2 / FIPS 140-3** · **FedRAMP Moderate/High baselines** · **NIST 800-53 SC-13** (Cryptographic Protection), **SC-8** (Transmission Confidentiality and Integrity), **SC-12** (Cryptographic Key Establishment and Management), **SC-28** (Protection of Information at Rest), **CM-6** (Configuration Settings — FIPS mode is a configuration property), **CM-7** (Least Functionality — restrict to FIPS-validated cryptographic providers) · **DoD SRG IL4/IL5** · **NIST 800-171 3.13.11**.

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
- Prioritize security issues based on severity (HIGH / MEDIUM / LOW / INFO)
- Provide actionable fix recommendations
- Include links to relevant documentation via Context7

### Reporting format — every finding must cite compliance control IDs
For each violation, the report must include a `Refs:` line that names the specific control identifiers the finding maps to. This turns the output from "advice" into "audit-aligned advice" that downstream auditors, GRC teams, and FedRAMP/SSDF assessors can trace back to their own control catalogs.

**Required citation sources (cite all that apply):**
- **NIST CSF 2.0** — Cybersecurity Framework functions and subcategories: GV.SC (Supply Chain Risk Management), ID.AM (Asset Management), ID.RA (Risk Assessment), PR.AA (Identity / Authentication / Access Control), PR.DS (Data Security), PR.PS (Platform Security — new in CSF 2.0), PR.IR (Technology Infrastructure Resilience), DE.CM (Continuous Monitoring).
- **NIST SP 800-190** — Application Container Security Guide (§4.1 image vulnerabilities, §4.4 secrets, §4.5 untrusted images, §4.6 registry security, §5 orchestrator/runtime).
- **NIST SP 800-53 Rev. 5** — control families: SR (Supply Chain), SC (System and Communications Protection), CM (Configuration Management), IA (Identification and Authentication), RA (Risk Assessment), AC (Access Control).
- **NIST SSDF (SP 800-218)** — PO (Prepare the Organization), PS (Protect the Software), PW (Produce Well-Secured Software), RV (Respond to Vulnerabilities).
- **CIS Docker Benchmark** — section 4 (Container Images) and section 5 (Container Runtime).
- **DISA STIG** — Container Platform STIG, Kubernetes STIG (when applicable).
- **FedRAMP** — Vulnerability Scanning Requirements for Containers (when in scope).
- **NSA/CISA Kubernetes Hardening Guide** — when the finding has runtime implications.
- **OWASP Docker Top 10** — when applicable.
- **FIPS 140-2 / 140-3** — for cryptographic findings under Rule #14.

**On NIST CSF 2.0 specifically:** CSF is the outcome-oriented framework most boards and risk committees read; 800-53 is the prescriptive control catalog auditors map to. Citing both makes findings legible to both audiences. The CSF 2.0 PR.PS (Platform Security) function is new in the 2.0 release (Feb 2024) and is where most container-image controls land; older mappings to CSF 1.1 used PR.IP and PR.DS — if a downstream audience is still on CSF 1.1, fall back to PR.IP-01 (baseline config), PR.IP-03 (config change control), PR.DS-06 (integrity).

**Required output shape for each finding:**
```
[SEVERITY] <Short rule name>
  Location:  <file>:<line>  (or <stage>/<line>)
  Detected:  <the exact text or pattern that matched>
  Why:       <one-line rationale>
  Fix:       <concrete remediation — code snippet preferred>
  Refs:      <NIST 800-190 §X.Y> | <NIST 800-53 control IDs> | <SSDF practice IDs> | <CIS Benchmark section> | <other>
```

**Example:**
```
[HIGH] Public package registry used (PyPI default)
  Location:  Dockerfile:6
  Detected:  RUN pip install --no-cache-dir -r requirements.txt
  Why:       pip with no --index-url and no pip.conf COPY'd in — resolves to pypi.org.
             Public registries are routinely abused for dependency confusion and typosquatting.
  Fix:       COPY pip.conf /etc/pip.conf   # contains: index-url = https://pypi.internal.example.com/simple/
             RUN pip install --no-cache-dir -r requirements.txt
  Refs:      NIST CSF 2.0 GV.SC-05, GV.SC-07, PR.PS-06  |  NIST 800-190 §4.5  |
             NIST 800-53 SR-3, SR-5, SR-11  |  SSDF PW 4.1, PO 1.1  |
             FedRAMP Container Scanning Reqs §3
```

**Roll-up at the top of every report:**
- Total counts by severity (HIGH / MEDIUM / LOW / INFO).
- Total counts by **CSF 2.0 function** (GV / ID / PR / DE / RS / RC) — gives boards and risk committees an at-a-glance read.
- Total counts by **800-53 control family** (so an auditor can see "5 findings touch SR controls, 3 touch SC, 2 touch IA").
- A short executive summary: "this image is / is not consistent with FedRAMP Moderate baseline / NIST 800-190 / DoD SRG IL4 expectations" — only when enough signal exists to make that claim, otherwise omit.

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