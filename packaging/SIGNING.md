# Prerelease signing certificate

Windows prerelease builds are Authenticode-signed with a self-signed project
certificate. This proves that assets carrying the same signature were produced
with the release signing key, but it does not provide the identity assurance of
a publicly trusted code-signing certificate.

- Subject: `CN=VocalSieve Prerelease, O=VocalSieve`
- Thumbprint: `8E6E9C75133477634B6211D6FE31BBFE2A86067C`
- Valid until: 2028-09-25 18:33:47 UTC

This certificate replaced the previous prerelease signing identity on
2026-09-26 because its private key was no longer available. The packaging
script checks that the private key supplied through Actions Secrets matches
the public certificate before signing.

The public certificate is committed as
`packaging/VocalSieve-Prerelease-CodeSigning.cer` and is included with Windows
release assets. Never commit the corresponding PFX or its password.
