# TrackState CLI installer for PowerShell.
#
# Usage (save then run — Invoke-Expression cannot execute a param block):
#   irm https://github.com/__REPO_PLACEHOLDER__/releases/latest/download/install.ps1 -OutFile install.ps1
#   .\install.ps1
#
#   irm https://github.com/__REPO_PLACEHOLDER__/releases/download/v1.2.3/install.ps1 -OutFile install.ps1
#   .\install.ps1 -Version v1.2.3
#
#   .\install.ps1 -Force          # install even if trackstate.exe is already on PATH
#
# The script installs the TrackState CLI into a user-local directory and
# appends that directory to the user-level PATH when it is not already present.
# No administrator privileges are required.
param(
    [Parameter(Position = 0)]
    [string]$Version = "latest",

    [switch]$Force
)

$ErrorActionPreference = "Stop"

$Repo = "__REPO_PLACEHOLDER__"

function Write-Info {
    param([string]$Message)
    Write-Host "--> $Message" -ForegroundColor Cyan
}

function Write-ErrorAndExit {
    param([string]$Message)
    Write-Host "ERROR: $Message" -ForegroundColor Red
    exit 1
}

function Resolve-ReleaseTag {
    param([string]$RequestedVersion)

    if ($RequestedVersion -ne "latest") {
        return $RequestedVersion
    }

    try {
        $releaseJson = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/latest" -UseBasicParsing
    } catch {
        Write-ErrorAndExit "Unable to resolve the latest release from the GitHub API: $_"
    }

    if (-not $releaseJson.tag_name) {
        Write-ErrorAndExit "Unable to parse the latest release tag from the GitHub API response."
    }

    return $releaseJson.tag_name
}

function Get-PlatformSuffix {
    $os = $PSVersion.Platform
    $arch = [System.Runtime.InteropServices.RuntimeInformation]::ProcessArchitecture

    if ($IsWindows -or ($os -eq "Win32NT")) {
        if ($arch -eq [System.Runtime.InteropServices.Architecture]::X64) {
            return "windows-x64"
        }
        Write-ErrorAndExit "Unsupported architecture on Windows: $arch. Supported: X64."
    }

    Write-ErrorAndExit "Unsupported operating system: $os. This PowerShell installer supports Windows only."
}

function Invoke-Download {
    param(
        [string]$Url,
        [string]$OutFile
    )
    try {
        Invoke-WebRequest -Uri $Url -OutFile $OutFile -UseBasicParsing
    } catch {
        Write-ErrorAndExit "Download failed: $Url - $_"
    }
}

$InstallDir = Join-Path $env:LOCALAPPDATA "trackstate\bin"

function Test-ExistingTrackstateConflict {
    $existing = Get-Command "trackstate" -ErrorAction SilentlyContinue
    if (-not $existing) {
        $existing = Get-Command "trackstate.exe" -ErrorAction SilentlyContinue
    }
    $managedBin = Join-Path $InstallDir "trackstate.exe"
    if ($existing -and $existing.Source.ToLowerInvariant() -ne $managedBin.ToLowerInvariant()) {
        if ($Force) {
            Write-Info "Warning: an existing trackstate binary was found at $($existing.Source); continuing because -Force was passed."
        } else {
            Write-ErrorAndExit "A conflicting trackstate binary already exists on PATH at $($existing.Source). Use -Force to override."
        }
    }
}

Test-ExistingTrackstateConflict

$releaseTag = Resolve-ReleaseTag -RequestedVersion $Version
$platform = Get-PlatformSuffix
$archiveName = "trackstate-cli-$platform-$releaseTag.tar.gz"
$checksumName = "trackstate-$releaseTag.sha256"
$downloadBase = "https://github.com/$Repo/releases/download/$releaseTag"

Write-Info "Installing TrackState CLI $releaseTag for $platform..."

$tmpDir = Join-Path $env:TEMP ([System.Guid]::NewGuid().ToString())
New-Item -ItemType Directory -Path $tmpDir -Force | Out-Null

try {
    $archivePath = Join-Path $tmpDir $archiveName
    $checksumPath = Join-Path $tmpDir $checksumName

    Invoke-Download -Url "$downloadBase/$archiveName" -OutFile $archivePath
    Invoke-Download -Url "$downloadBase/$checksumName" -OutFile $checksumPath

    $checksumLines = Get-Content -Path $checksumPath
    $expectedHash = $checksumLines |
        Where-Object { $_ -match "^([a-fA-F0-9]{64})\s+$archiveName\s*$" } |
        ForEach-Object { $matches[1] }

    if (-not $expectedHash) {
        Write-ErrorAndExit "Unable to find checksum entry for $archiveName in $checksumName."
    }

    $actualHash = (Get-FileHash -Path $archivePath -Algorithm SHA256).Hash.ToLower()
    if ($expectedHash.ToLower() -ne $actualHash) {
        Write-ErrorAndExit "Checksum mismatch for $archiveName. Expected: $expectedHash, got: $actualHash."
    }

    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    tar -xzf $archivePath -C $tmpDir

    $extractedBin = Join-Path $tmpDir "trackstate.exe"
    if (-not (Test-Path $extractedBin)) {
        Write-ErrorAndExit "Expected executable 'trackstate.exe' was not found in the downloaded archive."
    }

    $targetBin = Join-Path $InstallDir "trackstate.exe"
    Copy-Item -Path $extractedBin -Destination $targetBin -Force

    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $pathEntries = $userPath -split ";" | Where-Object { $_ -ne "" }
    if ($pathEntries -notcontains $InstallDir) {
        [Environment]::SetEnvironmentVariable(
            "Path",
            "$InstallDir;$userPath",
            "User"
        )
        Write-Info "Added $InstallDir to your user PATH."
        Write-Info "Open a new PowerShell window to use the 'trackstate' command."
    } else {
        Write-Info "$InstallDir is already on your user PATH."
    }

    Write-Info "TrackState CLI $releaseTag installed to $targetBin"
    & $targetBin --version 2>$null | Out-Null
} finally {
    Remove-Item -Path $tmpDir -Recurse -Force -ErrorAction SilentlyContinue
}
