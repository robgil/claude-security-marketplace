# Secure Container Review SKILL

This SKILL analyzes Dockerfiles and provides recommendations for creating secure containers following best practices.

## Features

- Analyzes Dockerfiles for security best practices
- Recommends Chainguard base images where appropriate
- Checks for proper multi-stage build usage
- Verifies non-root user usage
- Identifies privilege and network access issues
- Provides actionable security recommendations

## Requirements

- Claude plugin environment
- Access to Dockerfile content for analysis

## Usage

1. Place Dockerfile in your project
2. Call the Secure Container Review SKILL
3. Review security recommendations provided
4. Apply fixes as recommended

## Security Analysis Components

1. **Base Image Check**: Verify base image quality and security updates
2. **Build Process**: Multi-stage build detection and dependency separation
3. **User Rights**: User privilege checks and non-root execution verification
4. **Security Profile**: Privilege level and process management
5. **Script Usage**: Shell script detection and recommendations
6. **Network Access**: Outbound connectivity restrictions

## Documentation

- [Security Best Practices](skills/secure-container-review/references/security_best_practices.md)
- [Chainguard Guidelines](skills/secure-container-review/references/chainguard_guidelines.md)

## Testing

The SKILL includes test cases for both insecure and secure Dockerfile examples to validate analysis accuracy.

## Version Information

- Version: 1.0.0
- Release Date: May 2026