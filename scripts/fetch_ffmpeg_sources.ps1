[CmdletBinding()]
param(
    [string]$Destination = "dist/sources"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$manifest = Get-Content (Join-Path $root "packaging/ffmpeg-manifest.json") | ConvertFrom-Json
$destinationPath = Join-Path $root $Destination
New-Item -ItemType Directory -Force -Path $destinationPath | Out-Null

foreach ($archive in $manifest.source_archives) {
    $name = Split-Path $archive.url -Leaf
    $target = Join-Path $destinationPath $name
    Invoke-WebRequest -Uri $archive.url -OutFile $target -UseBasicParsing
    $hash = Get-FileHash -Algorithm SHA256 -LiteralPath $target
    if ($hash.Hash -ne $archive.sha256) {
        throw "Source SHA256 mismatch for $name. Expected $($archive.sha256), got $($hash.Hash)"
    }
    $hash
}
