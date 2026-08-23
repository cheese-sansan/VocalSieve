# Prerelease signing certificate

Windows prerelease builds are Authenticode-signed with a self-signed project
certificate. This proves that assets carrying the same signature were produced
with the release signing key, but it does not provide the identity assurance of
a publicly trusted code-signing certificate.

- Subject: `CN=VocalSieve Prerelease, O=VocalSieve`
- Thumbprint: `2B409A50008B5E9785129F8138AB594694F757BA`
- Valid until: 2028-06-21 19:20:47 UTC

The public certificate is committed as
`packaging/VocalSieve-Prerelease-CodeSigning.cer` and is included with Windows
release assets. Never commit the corresponding PFX or its password.
