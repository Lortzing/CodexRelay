[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string]$Binary,
    [Parameter(Mandatory = $true)] [ValidateSet("x86", "x86_64", "arm64")] [string]$Architecture,
    [Parameter(Mandatory = $true)] [string]$Version,
    [Parameter(Mandatory = $true)] [string]$OutputDir
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$BinaryPath = (Resolve-Path $Binary).Path
$OutputPath = [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $OutputDir))
New-Item -ItemType Directory -Path $OutputPath -Force | Out-Null

function Find-Iscc {
    $candidates = @(
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 7\ISCC.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 7\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
    )
    foreach ($candidate in $candidates) { if (Test-Path $candidate) { return $candidate } }
    throw "ISCC.exe was not found. Install Inno Setup before running this script."
}

$iscc = Find-Iscc
$setupBaseName = "CoderRelay-Setup-$Version-windows-$Architecture"
$iss = Join-Path $Root "installers\windows\CoderRelay.iss"
& $iscc @(
    "/Qp",
    "/DAppVersion=$Version",
    "/DSourceExe=$BinaryPath",
    "/DTargetArch=$Architecture",
    "/DOutputDir=$OutputPath",
    "/DOutputBaseFilename=$setupBaseName",
    $iss
)
if ($LASTEXITCODE -ne 0) { throw "Inno Setup compilation failed." }

$setupPath = Join-Path $OutputPath "$setupBaseName.exe"
if (-not (Test-Path $setupPath)) { throw "Expected installer was not produced: $setupPath" }

$portableName = "CoderRelay-Portable-$Version-windows-$Architecture"
$stage = Join-Path $env:RUNNER_TEMP $portableName
Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $stage -Force | Out-Null
Copy-Item $BinaryPath (Join-Path $stage "cdy.exe")
foreach ($name in @("README.md", "README.en.md", "LICENSE")) {
    $source = Join-Path $Root $name
    if (Test-Path $source) { Copy-Item $source (Join-Path $stage $name) }
}
@"
CoderRelay portable package

1. Move cdy.exe to a permanent directory.
2. Add that directory to your user PATH.
3. Open a new terminal and run: cdy status

For a normal installation, use the matching CoderRelay-Setup executable.
"@ | Set-Content -Path (Join-Path $stage "INSTALL.txt") -Encoding UTF8
$zipPath = Join-Path $OutputPath "$portableName.zip"
Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
Compress-Archive -Path $stage -DestinationPath $zipPath -CompressionLevel Optimal
Write-Output $setupPath
Write-Output $zipPath
