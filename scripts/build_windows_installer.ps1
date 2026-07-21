[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Binary,

    [Parameter(Mandatory = $true)]
    [ValidateSet("x86", "x86_64", "arm64")]
    [string]$Architecture,

    [Parameter(Mandatory = $true)]
    [string]$Version,

    [Parameter(Mandatory = $true)]
    [string]$OutputDir
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$BinaryPath = (Resolve-Path $Binary).Path
$OutputPath = [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $OutputDir))
New-Item -ItemType Directory -Path $OutputPath -Force | Out-Null

function Find-SignTool {
    $sdkRoot = Join-Path ${env:ProgramFiles(x86)} "Windows Kits\10\bin"
    if (-not (Test-Path $sdkRoot)) {
        throw "Windows SDK SignTool was not found under $sdkRoot"
    }

    $osArch = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString().ToLowerInvariant()
    $preferred = if ($osArch -eq "arm64") { "arm64" } else { "x64" }
    $all = Get-ChildItem -Path $sdkRoot -Filter signtool.exe -Recurse -File
    $candidate = $all |
        Where-Object { $_.Directory.Name -eq $preferred } |
        Sort-Object FullName |
        Select-Object -Last 1
    if (-not $candidate) {
        $candidate = $all | Sort-Object FullName | Select-Object -Last 1
    }
    if (-not $candidate) {
        throw "Windows SDK SignTool was not found."
    }
    return $candidate.FullName
}

function Find-Iscc {
    $candidates = @(
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 7\ISCC.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 7\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }
    throw "ISCC.exe was not found. Install Inno Setup before running this script."
}

function Import-SigningCertificate {
    param(
        [Parameter(Mandatory = $true)] [string]$Base64,
        [Parameter(Mandatory = $true)] [string]$Password
    )

    $pfxPath = Join-Path $env:RUNNER_TEMP "codex-relay-signing.pfx"
    [System.IO.File]::WriteAllBytes($pfxPath, [Convert]::FromBase64String($Base64))
    $securePassword = ConvertTo-SecureString -String $Password -AsPlainText -Force
    $imported = Import-PfxCertificate `
        -FilePath $pfxPath `
        -CertStoreLocation "Cert:\CurrentUser\My" `
        -Password $securePassword
    Remove-Item $pfxPath -Force

    $certificate = $imported | Where-Object { $_.HasPrivateKey } | Select-Object -First 1
    if (-not $certificate) {
        throw "The imported PFX does not contain a private key."
    }
    return $certificate
}

$certificateBase64 = $env:WINDOWS_CERTIFICATE_PFX_BASE64
$certificatePassword = $env:WINDOWS_CERTIFICATE_PASSWORD
$signingConfigured = -not [string]::IsNullOrWhiteSpace($certificateBase64) -or `
                     -not [string]::IsNullOrWhiteSpace($certificatePassword)
if ($signingConfigured -and (
    [string]::IsNullOrWhiteSpace($certificateBase64) -or
    [string]::IsNullOrWhiteSpace($certificatePassword)
)) {
    throw "Both WINDOWS_CERTIFICATE_PFX_BASE64 and WINDOWS_CERTIFICATE_PASSWORD are required for signing."
}

$iscc = Find-Iscc
$certificate = $null
$signTool = $null
$signWrapper = $null
$suffix = "-unsigned"

try {
    if ($signingConfigured) {
        $signTool = Find-SignTool
        $certificate = Import-SigningCertificate -Base64 $certificateBase64 -Password $certificatePassword
        $suffix = ""

        & $signTool sign `
            /sha1 $certificate.Thumbprint `
            /fd SHA256 `
            /td SHA256 `
            /tr "https://timestamp.digicert.com" `
            /d "CodexRelay" `
            $BinaryPath
        if ($LASTEXITCODE -ne 0) {
            throw "SignTool failed to sign cxr.exe."
        }
        & $signTool verify /pa /v $BinaryPath
        if ($LASTEXITCODE -ne 0) {
            throw "SignTool verification failed for cxr.exe."
        }

        $signWrapper = Join-Path $env:RUNNER_TEMP "codex-relay-sign.cmd"
        @"
@echo off
"$signTool" sign /sha1 $($certificate.Thumbprint) /fd SHA256 /td SHA256 /tr https://timestamp.digicert.com /d "CodexRelay" %*
"@ | Set-Content -Path $signWrapper -Encoding Ascii
    }

    $setupBaseName = "CodexRelay-Setup-$Version-windows-$Architecture$suffix"
    $iss = Join-Path $Root "installers\windows\CodexRelay.iss"
    $arguments = @(
        "/Qp",
        "/DAppVersion=$Version",
        "/DSourceExe=$BinaryPath",
        "/DTargetArch=$Architecture",
        "/DOutputDir=$OutputPath",
        "/DOutputBaseFilename=$setupBaseName"
    )
    if ($signingConfigured) {
        $arguments += "/DEnableSigning=1"
        $arguments += "/Scxr=cmd.exe /d /c `"$signWrapper`" `$f"
    }
    $arguments += $iss

    & $iscc @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup compilation failed."
    }

    $setupPath = Join-Path $OutputPath "$setupBaseName.exe"
    if (-not (Test-Path $setupPath)) {
        throw "Expected installer was not produced: $setupPath"
    }
    if ($signingConfigured) {
        & $signTool verify /pa /v $setupPath
        if ($LASTEXITCODE -ne 0) {
            throw "SignTool verification failed for the installer."
        }
    }

    $portableName = "CodexRelay-Portable-$Version-windows-$Architecture$suffix"
    $stage = Join-Path $env:RUNNER_TEMP $portableName
    Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Path $stage -Force | Out-Null
    Copy-Item $BinaryPath (Join-Path $stage "cxr.exe")
    foreach ($name in @("README.md", "README.en.md", "LICENSE")) {
        $source = Join-Path $Root $name
        if (Test-Path $source) {
            Copy-Item $source (Join-Path $stage $name)
        }
    }
    @"
CodexRelay portable package

1. Move cxr.exe to a permanent directory.
2. Add that directory to your user PATH.
3. Open a new terminal and run: cxr status

For a normal installation, use the matching CodexRelay-Setup executable.
"@ | Set-Content -Path (Join-Path $stage "INSTALL.txt") -Encoding UTF8

    $zipPath = Join-Path $OutputPath "$portableName.zip"
    Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
    Compress-Archive -Path $stage -DestinationPath $zipPath -CompressionLevel Optimal

    Write-Output $setupPath
    Write-Output $zipPath
}
finally {
    if ($certificate) {
        Remove-Item "Cert:\CurrentUser\My\$($certificate.Thumbprint)" -Force -ErrorAction SilentlyContinue
    }
    if ($signWrapper) {
        Remove-Item $signWrapper -Force -ErrorAction SilentlyContinue
    }
}
