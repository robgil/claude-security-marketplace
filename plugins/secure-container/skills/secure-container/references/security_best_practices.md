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

## Verification Process

### Security Checks
- Validate base image security posture
- Check for proper user and privilege configuration
- Verify network access restrictions
- Confirm multi-stage build practices