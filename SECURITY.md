# Security policy

## Supported versions

Security fixes are provided for the latest published release.

## Reporting

Do not open public issues for vulnerabilities. Use GitHub private vulnerability
reporting at https://github.com/cheese-sansan/VocalSieve/security/advisories/new.
Include reproduction steps, affected versions, and impact.

The HTTP API is intentionally loopback-only. It is not designed to be exposed
to a LAN or the public internet.

Source directories are a trusted local input boundary. The current pipeline does
not enforce a maximum audio file size, duration, decoded sample count, or aggregate
job size; very large or adversarial corpora can exhaust local CPU, memory, or disk.
Apply operating-system quotas and review untrusted corpora before processing them.

Self-hosted GPU runners execute only maintainer-triggered workflows. They must
never be assigned to pull-request workflows from forks and should be removed
after a release gate. The privileged workflows enforce repository-owner and
main/version-tag checks. Signing certificates are supplied only through encrypted
GitHub Secrets, exposed only to the signing step, and deleted from the runner after
signing.
