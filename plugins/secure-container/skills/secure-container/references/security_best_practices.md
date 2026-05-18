# Security Best Practices for Container Images

## General Security Principles

### 1. Minimize Attack Surface
- Use minimal base images
- Remove unnecessary packages and dependencies
- Avoid installing unnecessary tools in production containers

### 2. Use Trusted Base Images
- Prefer official images from trusted sources
- Regularly update base images to include security patches
- Consider using Chainguard images for enhanced security

### 3. Run as Non-Root User
- Always switch to a non-root user after creating necessary directories
- Create dedicated user accounts with limited privileges
- Avoid running applications as root in production

### 4. Multi-Stage Builds
- Separate build-time dependencies from runtime dependencies
- Use build stages to compile applications and copy only necessary artifacts
- Keep production images minimal and focused

## Dockerfile Security Guidelines

### Base Image Security
- Choose images based on security reviews
- **Pin every `FROM` to an immutable `@sha256:<digest>` — tags are mutable and cannot anchor a reproducible build (see "Hash Pinning Base Images" below)**
- Regularly scan base images for vulnerabilities

### User Management
- Always create and use non-root users
- Set proper permissions for files and directories
- Avoid using root user in production containers

### Privilege Controls
- Avoid using privileged mode unless absolutely necessary
- Use capabilities instead of full privileged access
- Limit container capabilities with --cap-drop

### Process Management
- Ensure containers run a single process
- Handle process lifecycle properly
- Use proper init systems if needed

### Network Security
- Restrict outbound network access where possible
- Avoid unnecessary network connectivity in containers
- Implement proper firewall rules and network policies

## Chainguard Specific Recommendations

### Using Chainguard Images
- Prefer Chainguard images for enhanced security
- Verify image integrity and signatures
- Check for security updates regularly

### Image Optimization
- Use Chainguard's security-focused base images
- Leverage Chainguard's vulnerability scanning
- Follow Chainguard's best practices for image building

## Hash Pinning Base Images

### Why digest pinning matters
- Tags (`:latest`, `:3.13-slim`, `:20-alpine`, `:1.22`, `:21-jdk`) are **mutable**. The image content behind a tag changes when upstream republishes — silently breaking reproducibility and opening a supply-chain seam.
- A digest (`@sha256:<64 hex>`) is **immutable** — it cryptographically identifies exact image bytes. Any change in the image produces a different digest, making tampering visible.
- Digest pins are required for meaningful SBOM generation, provenance attestation (SLSA), and "what's actually running in prod" forensics.

### The rule (applies to every runtime — Python, Node, Go, Rust, Java, Ruby, .NET, etc.)
Every `FROM` instruction must reference its image by `@sha256:<digest>`. Tag-only references are violations regardless of how specific the tag looks.

```dockerfile
# ❌ Violation — mutable tag
FROM node:20-alpine
FROM golang:1.22
FROM rust:1.75-slim
FROM eclipse-temurin:21-jdk
FROM python:3.13-slim
FROM mcr.microsoft.com/dotnet/sdk:8.0

# ✅ Compliant — digest-pinned
FROM node:20-alpine@sha256:2c6c59cf4d34d4f937c0c1c8d3d0e7d2f....
FROM cgr.dev/chainguard/go@sha256:...
FROM cgr.dev/chainguard/rust@sha256:...
FROM cgr.dev/chainguard/jdk@sha256:...
FROM cgr.dev/chainguard/python@sha256:...
FROM mcr.microsoft.com/dotnet/sdk@sha256:...
```

### Exemptions
- `FROM scratch` — no image, nothing to pin.
- `FROM <alias>` referencing a prior `AS <alias>` build stage — the alias points to a stage in the same file whose own `FROM` must be pinned.

### Getting and rotating digests
```bash
# Resolve a tag to a digest:
docker pull node:20-alpine
docker inspect --format='{{index .RepoDigests 0}}' node:20-alpine

# Or without Docker:
crane digest node:20-alpine
regctl image digest node:20-alpine
```
Automate rotation with **Renovate** (`pinDigests: true`) or **Dependabot** so pins don't go stale and miss CVE patches. Pin tag + digest together (`node:20-alpine@sha256:...`) so the human-readable tag survives for review while the digest enforces immutability.

## Package Sources: Internal Registries Only

### Why public registries are unsafe at build time
Builds that fetch dependencies from public open-source registries (PyPI, npm, crates.io, Maven Central, RubyGems, NuGet.org, the public Go module proxy, default `apt`/`apk` mirrors) put the entire image at the mercy of:

- **Dependency confusion** — a public package matching the name of a private one gets installed instead.
- **Typosquatting** — `requesocks`, `python-sqlite3`, `nodemon-cli`, etc.
- **Maintainer account takeover** — a legitimate package gets a malicious version published.
- **Protestware / post-install scripts** — arbitrary code runs during install.
- **Upstream registry outage** — builds break unrelated to your code.

Internal proxies (Artifactory, Sonatype Nexus, AWS CodeArtifact, GCP Artifact Registry, Azure Artifacts, GitHub Packages, Verdaccio, devpi, Athens) provide quarantine, scanning, allow-listing, version locking, audit logs, and resilience.

### The rule
Every package-installer invocation in a Dockerfile must be redirected to a controlled internal registry. Redirection can be done via command-line flag, environment variable, or a registry config file COPY'd in earlier — but **something** must redirect it. A bare `RUN pip install -r requirements.txt` or `RUN npm ci` is a violation.

### Per-runtime examples

```dockerfile
# ❌ Violations — default public registry
RUN pip install -r requirements.txt
RUN npm ci
RUN go mod download
RUN cargo fetch
RUN mvn -B package
RUN bundle install
RUN dotnet restore
RUN apt-get update && apt-get install -y curl

# ✅ Compliant — redirected to internal registry
COPY pip.conf /etc/pip.conf
RUN pip install -r requirements.txt

COPY .npmrc /root/.npmrc
RUN npm ci

ENV GOPROXY=https://goproxy.internal.example.com,direct
RUN go mod download

COPY .cargo/config.toml /root/.cargo/config.toml
RUN cargo fetch

COPY settings.xml /root/.m2/settings.xml
RUN mvn -B package

COPY .bundle/config /root/.bundle/config
RUN bundle install

COPY nuget.config /root/.nuget/NuGet/NuGet.Config
RUN dotnet restore

COPY sources.list /etc/apt/sources.list
RUN apt-get update && apt-get install -y curl
```

### Preferred pattern: ship the config, keep the command clean
Putting the registry URL in a config file (rather than on every command line) means:
- The Dockerfile reads the same locally, in CI, and across environments.
- Switching registries is a one-file change.
- Reviewers can spot a missing config COPY at a glance.

### The internal registry must itself be configured
Pointing the build at an internal proxy that simply passes everything through to PyPI/npm is not sufficient. The proxy must:
- Mirror only known-good versions (lockfile pinning + hash verification).
- Run vulnerability scanning (Snyk, Trivy, Grype) and block on policy violations.
- Quarantine new upstream releases for human review before they reach builds.
- Log every fetch with build provenance for incident response.

## Secrets in Images

Secrets do not belong in any image layer. Layers are immutable and additive — a secret `COPY`'d in stage 1 and "deleted" in stage 2 is still recoverable.

Forbidden patterns:
- `ENV API_KEY=...`, `ENV *_TOKEN=...`, `ENV *_PASSWORD=...` with real values.
- `COPY .env`, `COPY id_rsa`, `COPY *.pem`, `COPY .aws/credentials`, `COPY *.kubeconfig`.
- Inline credentials in `RUN`: `curl -H "Authorization: Bearer ey..."`, `git clone https://user:token@github.com/...`.
- `ARG` consumed in a `RUN` whose value is baked into history.

The fix is BuildKit secret mounts:
```dockerfile
# syntax=docker/dockerfile:1.7
RUN --mount=type=secret,id=npm_token \
    NPM_TOKEN=$(cat /run/secrets/npm_token) npm ci
```
Build with `docker build --secret id=npm_token,src=$HOME/.npm-token .` — the secret is never written to a layer.

Public certificates (CA bundles, `*.crt` without a matching `*.key`) and example env files (`.env.example`, `.env.template`) are exempt.

Even production credentials should come from workload-identity systems at runtime (IRSA, Workload Identity, Managed Identity, SPIFFE/SPIRE) — not baked into images.

Maps to: NIST 800-190 §4.4 · NIST 800-53 IA-5 · SSDF PW 1.2 · CIS Docker Benchmark 4.10.

## No SSH, init systems, or PAM in production images

Production containers run a single application process. They are not VMs. They do not need an SSH server, an init system, or pluggable authentication.

Forbidden in the final stage:
- SSH server: `openssh-server`, `sshd`, `dropbear`. (SSH client is occasionally legitimate but should be reviewed.)
- Init systems: `systemd`, `sysvinit-core`, `openrc`, `runit`, `s6` (when used as full init), `supervisord`. `tini` / `dumb-init` are PID 1 signal-forwarding shims, *not* init systems, and are encouraged.
- PAM: `libpam-*`, `pam-*`, `/etc/pam.d/` (no human will authenticate to this image).

For "I need to debug a running container," use `kubectl debug` / `kubectl exec` / `docker exec` / ephemeral debug containers — not a persistent `sshd`. For genuine multi-process needs, split into multiple containers, not multiple processes in one container.

Maps to: NIST 800-190 §4.5 · CIS Docker Benchmark 4.5 · NSA/CISA Kubernetes Hardening Guide.

## Approved base image registries

The base image is the largest contributor to a container's attack surface and patch burden. It must come from a registry and distribution the organization explicitly trusts.

Reject:
- `FROM alpine` / `debian` / `ubuntu` / `centos` / `rockylinux` / `almalinux` / `fedora` (community general-purpose OS bases, designed for hardware/VMs not containers).
- `FROM python` / `node` / `golang` / `rust` / `eclipse-temurin` (DockerHub `library/*` — community-maintained, not supplier-supported).
- `FROM docker.io/...` / `FROM index.docker.io/...` (explicit DockerHub references).

Approved:
- Chainguard: `cgr.dev/chainguard/*` (purpose-built for containers, paid support available, FIPS variants).
- Google distroless: `gcr.io/distroless/*`.
- Red Hat UBI: `registry.access.redhat.com/ubi*` (when paired with a RHEL subscription).
- Microsoft (for .NET): `mcr.microsoft.com/dotnet/*`.
- Your organization's internal registry: AWS ECR, GCP Artifact Registry, Azure Container Registry, Harbor, Artifactory.
- `FROM scratch` — always allowed for statically compiled binaries.

Why purpose-built distros beat general-purpose ones (Chainguard / Wolfi OS as the example):
- No package manager in the final image (you can't `apt-get install` into a Chainguard runtime image, by design).
- No shell in the runtime variants (only `-dev` variants have one — for build stages).
- Dependency graphs designed for the container model: no `systemd`/`pam` hooks baked into the base, no OpenSSL where it isn't needed.
- Daily rebuilds with continuous CVE patching from the supplier.

This rule pairs with hash pinning — the approved base must still be referenced by `@sha256:...`.

Maps to: NIST 800-190 §4.5, §4.6 · NIST 800-53 SR-3, SR-5, SR-11 · SSDF PO 1.1, PW 4.1 · FedRAMP Vulnerability Scanning Requirements for Containers.

## FIPS when regulated context applies

Workloads subject to FIPS 140-2/140-3 (FedRAMP Moderate/High, DoD SRG IL4/IL5, parts of HIPAA, contracts that incorporate FIPS by reference) must use a base image whose cryptographic libraries are FIPS-validated. Non-FIPS bases ship OpenSSL builds whose validation does not apply.

Indicators that FIPS context applies:
- Configuration flag (`secure-container.config.yaml: requireFips: true`).
- Compliance `LABEL` on the Dockerfile (`LABEL compliance.fips="required"` or `LABEL fedramp.scope="moderate"`).
- Repo marker (`.fips-required`, `compliance.yaml`).

When FIPS context applies, require a FIPS-variant base:
- Chainguard `-fips` images: `cgr.dev/chainguard/python-fips`, `cgr.dev/chainguard/jre-fips`, `cgr.dev/chainguard/go-fips`.
- Red Hat UBI with FIPS-mode OpenSSL documented in `LABEL`.

Hygiene checks when FIPS context is active:
- Reject explicit disabling: `ENV OPENSSL_FIPS=0`, `GODEBUG=fips140=off`.
- Reject installing non-FIPS crypto libraries.
- Recommend a `LABEL` documenting FIPS mode for downstream auditors.

Using a FIPS image is necessary but not sufficient — the application must also be configured to use the FIPS-validated providers.

Maps to: FIPS 140-2 / 140-3 · FedRAMP Moderate/High baselines · NIST 800-53 SC-13 · DoD SRG IL4/IL5 · NIST 800-171 3.13.11.

## Compliance citations in every finding

Reports from this skill cite specific control identifiers on every finding. This turns advice into audit-aligned advice that GRC teams and FedRAMP assessors can trace to their own catalogs without re-deriving the mapping.

Cited frameworks:
- **NIST CSF 2.0** — outcome-oriented framework most boards and risk committees read. Primary functions in scope: GV (Govern, especially GV.SC Supply Chain), PR (Protect, especially PR.PS Platform Security — new in CSF 2.0 — and PR.AA Access Control), ID (Identify, especially ID.AM Asset Management and ID.RA Risk Assessment).
- **NIST SP 800-190** — Application Container Security Guide. The container-specific NIST publication; §4 covers image risks, §5 covers orchestrator and runtime risks.
- **NIST SP 800-53 Rev. 5** — prescriptive control catalog auditors map to. The two controls that recur most often in this skill are **AC-6 (Least Privilege)** and **CM-7 (Least Functionality)** — every form of "this doesn't belong in a production container" maps to one or both. Supply-chain findings cluster in the SR family.
- **NIST SSDF (SP 800-218)** — Secure Software Development Framework practices (PO / PS / PW / RV).
- **CIS Docker Benchmark** — image-level (section 4) and runtime-level (section 5) checks.
- **FedRAMP Vulnerability Scanning Requirements for Containers** — for in-scope workloads.
- **FIPS 140-2 / 140-3** — cryptographic mode requirements (Rule #14).
- **DISA STIG**, **NSA/CISA Kubernetes Hardening Guide**, **OWASP Docker Top 10**, **SLSA** — cited where applicable.

### Why CSF 2.0 *and* 800-53 (both, not either)

CSF is the outcome-oriented framework most boards and risk committees read; 800-53 is the prescriptive control catalog auditors map to. Citing both makes findings legible to both audiences without forcing either to translate. If a downstream audience is still on **CSF 1.1**, the PR.PS controls (new in 2.0) fall back to PR.IP-01 (baseline config), PR.IP-03 (config change control), and PR.DS-06 (integrity).

See the "Reporting format" section in SKILL.md for the required output shape and a worked example, and the "Most-cited NIST 800-53 controls in this skill" table at the top of SKILL.md for the full control-to-rule mapping.

## Verification Process

### Security Checks
- Validate base image security posture (Rules #1, #9, #13, #14)
- Check for proper user and privilege configuration (Rules #3, #4)
- Verify network access restrictions and hermetic build posture (Rules #7, #10)
- Confirm multi-stage build practices and no build tooling in final image (Rule #2)
- Confirm no secrets are baked into any layer (Rule #11)
- Confirm no SSH server, init system, or PAM stack (Rule #12)
- Confirm single-process design with exec-form entrypoint (Rules #5, #6)