# Security policy

## Supported versions

Security fixes are provided for the latest published release.

## Reporting

Do not open public issues for vulnerabilities. Use GitHub private vulnerability
reporting at https://github.com/cheese-sansan/VocalSieve/security/advisories/new.
Include reproduction steps, affected versions, and impact.

The HTTP API is intentionally loopback-only. It is not designed to be exposed
to a LAN or the public internet.

Self-hosted GPU runners execute only maintainer-triggered workflows. They must
never be assigned to pull-request workflows from forks and should be removed
after a release gate. Signing certificates are supplied only through encrypted
GitHub Secrets and are deleted from the runner after signing.
