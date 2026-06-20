[CmdletBinding()]
param(
    [string]$Python = ".venv/Scripts/python.exe",
    [string]$FfmpegPath = "E:/ffmpeg-master-latest-win64-gpl/ffmpeg-master-latest-win64-gpl/bin/ffmpeg.exe",
    [string]$FfmpegLicensePath = "E:/ffmpeg-master-latest-win64-gpl/ffmpeg-master-latest-win64-gpl/LICENSE.txt",
    [string]$OutputDirectory = "dist/windows",
    [switch]$RequireSignature
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$pythonPath = [System.IO.Path]::GetFullPath((Join-Path $root $Python))
$ffmpeg = [System.IO.Path]::GetFullPath($FfmpegPath)
$ffmpegLicense = [System.IO.Path]::GetFullPath($FfmpegLicensePath)
$manifestPath = Join-Path $root "packaging/ffmpeg-manifest.json"
$manifest = Get-Content $manifestPath | ConvertFrom-Json

if (-not (Test-Path -LiteralPath $pythonPath)) { throw "Python not found: $pythonPath" }
if (-not (Test-Path -LiteralPath $ffmpeg)) { throw "FFmpeg not found: $ffmpeg" }
if (-not (Test-Path -LiteralPath $ffmpegLicense)) { throw "FFmpeg license not found: $ffmpegLicense" }
$actualHash = (Get-FileHash -LiteralPath $ffmpeg -Algorithm SHA256).Hash
if ($actualHash -ne $manifest.sha256) {
    throw "FFmpeg SHA256 mismatch. Expected $($manifest.sha256), got $actualHash"
}

$outputRoot = [System.IO.Path]::GetFullPath((Join-Path $root $OutputDirectory))
$workRoot = Join-Path $root "build/pyinstaller"
foreach ($target in @($outputRoot, $workRoot)) {
    if (Test-Path -LiteralPath $target) {
        $resolved = (Resolve-Path -LiteralPath $target).Path
        if (-not $resolved.StartsWith($root) -or $resolved -eq $root) {
            throw "Unsafe cleanup target: $resolved"
        }
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
New-Item -ItemType Directory -Force -Path $outputRoot, $workRoot | Out-Null

& $pythonPath -m PyInstaller `
    (Join-Path $root "packaging/VocalSieve.spec") `
    --noconfirm --clean `
    --distpath $outputRoot `
    --workpath $workRoot
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }

$portable = Join-Path $outputRoot "VocalSieve"
$ffmpegTarget = Join-Path $portable "tools/ffmpeg"
$licenseTarget = Join-Path $portable "licenses/FFmpeg"
$projectLicenseTarget = Join-Path $portable "licenses/VocalSieve"
New-Item -ItemType Directory -Force -Path $ffmpegTarget, $licenseTarget, $projectLicenseTarget | Out-Null
Copy-Item -LiteralPath $ffmpeg -Destination (Join-Path $ffmpegTarget "ffmpeg.exe")
Copy-Item -LiteralPath $ffmpegLicense -Destination (Join-Path $licenseTarget "COPYING.GPLv3.txt")
Copy-Item -LiteralPath $manifestPath -Destination (Join-Path $licenseTarget "SOURCE.json")
& $ffmpeg -version | Set-Content (Join-Path $licenseTarget "BUILD.txt") -Encoding utf8
Copy-Item -LiteralPath (Join-Path $root "LICENSE") -Destination $projectLicenseTarget
Copy-Item -LiteralPath (Join-Path $root "THIRD_PARTY_NOTICES.md") -Destination $portable
Copy-Item -LiteralPath (Join-Path $root "docs/PYTHON_LICENSES.md") -Destination (Join-Path $projectLicenseTarget "PYTHON_LICENSES.md")
Copy-Item -LiteralPath (Join-Path $root "packaging/README-WINDOWS.txt") -Destination $portable
Copy-Item -LiteralPath (Join-Path $root "Start-VocalSieve.cmd") -Destination $portable

$executable = Join-Path $portable "VocalSieve.exe"
$pfxBase64 = $env:WINDOWS_SIGNING_PFX_B64
$pfxPassword = $env:WINDOWS_SIGNING_PFX_PASSWORD
if ($pfxBase64 -and $pfxPassword) {
    $pfxPath = Join-Path $env:TEMP "vocalsieve-signing-$PID.pfx"
    try {
        [System.IO.File]::WriteAllBytes($pfxPath, [Convert]::FromBase64String($pfxBase64))
        $signTool = Get-ChildItem "${env:ProgramFiles(x86)}/Windows Kits/10/bin" -Recurse -Filter signtool.exe -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match "\\x64\\" } | Sort-Object FullName -Descending | Select-Object -First 1
        if (-not $signTool) {
            $sdkVersion = "10.0.26100.8249"
            $sdkHash = "1628C77D21ED187C4DB998B37B18E267A7F092AE755589E21110C14260B14960"
            $sdkRoot = Join-Path $workRoot "windows-sdk-signing"
            $sdkPackage = Join-Path $sdkRoot "sdk.nupkg"
            $sdkZip = Join-Path $sdkRoot "sdk.zip"
            New-Item -ItemType Directory -Force -Path $sdkRoot | Out-Null
            Invoke-WebRequest "https://api.nuget.org/v3-flatcontainer/microsoft.windows.sdk.buildtools/$sdkVersion/microsoft.windows.sdk.buildtools.$sdkVersion.nupkg" -OutFile $sdkPackage -UseBasicParsing
            $downloadedHash = (Get-FileHash $sdkPackage -Algorithm SHA256).Hash
            if ($downloadedHash -ne $sdkHash) { throw "Windows SDK BuildTools SHA256 mismatch" }
            Copy-Item $sdkPackage $sdkZip -Force
            Expand-Archive $sdkZip -DestinationPath $sdkRoot -Force
            $signTool = Get-ChildItem $sdkRoot -Recurse -Filter signtool.exe |
                Where-Object { $_.FullName -match "\\x64\\" } | Select-Object -First 1
        }
        if (-not $signTool) { throw "signtool.exe was not found" }
        & $signTool.FullName sign /fd SHA256 /td SHA256 /tr http://timestamp.digicert.com /f $pfxPath /p $pfxPassword $executable
        if ($LASTEXITCODE -ne 0) { throw "signtool sign failed" }
        & $signTool.FullName verify /pa /all $executable
        if ($LASTEXITCODE -ne 0) { throw "signtool verification failed" }
    }
    finally {
        if (Test-Path -LiteralPath $pfxPath) { Remove-Item -LiteralPath $pfxPath -Force }
    }
}
elseif ($RequireSignature) {
    throw "Signing is required, but WINDOWS_SIGNING_PFX_B64 or WINDOWS_SIGNING_PFX_PASSWORD is missing"
}

$zip = Join-Path $outputRoot "VocalSieve-Windows-x64.zip"
Compress-Archive -Path (Join-Path $portable "*") -DestinationPath $zip -CompressionLevel Optimal
Get-FileHash -LiteralPath $zip -Algorithm SHA256 | Format-List
