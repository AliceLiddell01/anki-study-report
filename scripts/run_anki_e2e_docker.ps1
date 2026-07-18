param(
    [switch]$BuildOnly,
    [switch]$NoBuild,
    [string]$ArtifactsDir = "",
    [ValidateSet("buildkit", "ghcr")]
    [string]$ImageSource = "buildkit"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$BaseComposeFile = Join-Path $Root "docker\anki-e2e\docker-compose.yml"
$GhcrComposeFile = Join-Path $Root "docker\anki-e2e\docker-compose.ghcr.yml"
$LocalInputDir = Join-Path $Root "docker\anki-e2e\local-input"
$LocalApkgName = "asr-e2e-render-fixtures.apkg"
$LocalApkgPath = Join-Path $LocalInputDir $LocalApkgName

if (-not $PSBoundParameters.ContainsKey("ImageSource") -and $env:ANKI_E2E_IMAGE_SOURCE) {
    if ($env:ANKI_E2E_IMAGE_SOURCE -notin @("buildkit", "ghcr")) {
        throw "Unsupported ANKI_E2E_IMAGE_SOURCE: $env:ANKI_E2E_IMAGE_SOURCE"
    }
    $ImageSource = $env:ANKI_E2E_IMAGE_SOURCE
}

if (-not (Test-Path $BaseComposeFile)) {
    throw "Docker compose file not found: $BaseComposeFile"
}

$ComposeFiles = @($BaseComposeFile)
if ($ImageSource -eq "ghcr") {
    if (-not (Test-Path $GhcrComposeFile)) {
        throw "GHCR Docker compose override not found: $GhcrComposeFile"
    }
    $ComposeFiles += $GhcrComposeFile
}

if (-not $ArtifactsDir) {
    $ArtifactsDir = Join-Path $Root "e2e-artifacts"
}

New-Item -ItemType Directory -Force -Path $ArtifactsDir | Out-Null
New-Item -ItemType Directory -Force -Path $LocalInputDir | Out-Null
$ArtifactsDir = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath $ArtifactsDir).Path)

if ($env:ANKI_E2E_APKG_FIXTURE) {
    $sourceApkg = Resolve-Path -LiteralPath $env:ANKI_E2E_APKG_FIXTURE -ErrorAction Stop
    Copy-Item -LiteralPath $sourceApkg.Path -Destination $LocalApkgPath -Force
    $env:ANKI_E2E_APKG_FIXTURE_PATH = "/e2e/local-input/$LocalApkgName"
    Write-Host "Staged APKG fixture for Docker E2E: $($sourceApkg.Path) -> docker/anki-e2e/local-input/$LocalApkgName"
} elseif (Test-Path -LiteralPath $LocalApkgPath) {
    $env:ANKI_E2E_APKG_FIXTURE_PATH = "/e2e/local-input/$LocalApkgName"
} elseif ($env:ANKI_E2E_APKG_FIXTURE_PATH -eq "/e2e/local-input/$LocalApkgName") {
    Remove-Item Env:\ANKI_E2E_APKG_FIXTURE_PATH
}

function Invoke-DockerCompose {
    param([string[]]$Arguments)

    $composeArguments = @("compose")
    foreach ($composeFile in $ComposeFiles) {
        $composeArguments += @("-f", $composeFile)
    }
    $composeArguments += $Arguments
    & docker @composeArguments
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose failed: $($Arguments -join ' ')"
    }
}

function Restore-E2EArtifactOwnership {
    param([string]$Volume)

    if (-not $IsLinux) {
        return
    }

    $uid = (& id -u).Trim()
    if ($LASTEXITCODE -ne 0 -or $uid -notmatch '^\d+$') {
        throw "Could not resolve the host UID for E2E artifact ownership restoration."
    }
    $gid = (& id -g).Trim()
    if ($LASTEXITCODE -ne 0 -or $gid -notmatch '^\d+$') {
        throw "Could not resolve the host GID for E2E artifact ownership restoration."
    }

    Invoke-DockerCompose @(
        "run",
        "--rm",
        "--no-deps",
        "-v",
        $Volume,
        "--entrypoint",
        "/bin/chown",
        "anki-e2e",
        "-R",
        "$($uid):$($gid)",
        "/e2e/artifacts"
    )
}

function Assert-E2EArtifactManifest {
    param([string]$ArtifactsRoot)

    $manifestPath = Join-Path $ArtifactsRoot "artifact-manifest.json"
    if (-not (Test-Path -LiteralPath $manifestPath)) {
        throw "E2E artifact manifest not found: $manifestPath"
    }
    $manifestText = Get-Content -Raw -LiteralPath $manifestPath
    if ($manifestText -match '(?i)(token=|\?token)') {
        throw "E2E artifact manifest contains a token-bearing URL."
    }
    $manifest = $manifestText | ConvertFrom-Json
    if ($manifest.status -ne "success") {
        throw "E2E artifact manifest status is not success: $($manifest.status)"
    }

    $indexedPaths = @()
    foreach ($property in $manifest.runtime.PSObject.Properties) {
        if ($property.Value -is [string] -and $property.Value) {
            $indexedPaths += [string]$property.Value
        }
    }
    foreach ($property in $manifest.artifacts.PSObject.Properties) {
        foreach ($value in @($property.Value)) {
            if ($value -is [string] -and $value) {
                $indexedPaths += [string]$value
            }
        }
    }
    foreach ($entry in @($manifest.screenshots)) {
        if ($entry.path) {
            $indexedPaths += [string]$entry.path
        }
    }

    $duplicates = @($indexedPaths | Group-Object | Where-Object { $_.Count -gt 1 } | ForEach-Object Name)
    if ($duplicates.Count -gt 0) {
        throw "Manifest contains duplicate artifact paths: $($duplicates -join ', ')"
    }
    foreach ($relativePath in $indexedPaths) {
        if ([IO.Path]::IsPathRooted($relativePath) -or $relativePath -match '^[A-Za-z]:' -or $relativePath -match '(^|[\\/])\.\.([\\/]|$)') {
            throw "Manifest contains a non-relative artifact path: $relativePath"
        }
        if (-not (Test-Path -LiteralPath (Join-Path $ArtifactsRoot $relativePath) -PathType Leaf)) {
            throw "Manifest references a missing artifact: $relativePath"
        }
    }

    $screenshots = @($manifest.screenshots)
    $pageScreenshots = @($screenshots | Where-Object { $_.kind -eq "page" })
    $navigationScreenshots = @($screenshots | Where-Object { $_.kind -eq "navigation" })
    $syntheticCards = @($screenshots | Where-Object { $_.kind -eq "cards" -and $_.fixture -eq "synthetic" })
    $apkgCards = @($screenshots | Where-Object { $_.kind -eq "cards" -and $_.fixture -eq "apkg" })
    $scope = if ($manifest.execution.scope) { [string]$manifest.execution.scope } else { "full" }
    $expectedPages = @{ full = 50; global = 8; stats = 20; decks = 2; activity = 2; cards = 0; settings = 14; notifications = 4 }[$scope]
    if ($null -eq $expectedPages -or $pageScreenshots.Count -ne $expectedPages) {
        throw "Expected $expectedPages page screenshots for scope=$scope, found $($pageScreenshots.Count)."
    }
    $expectedNavigation = if ($scope -in @("full", "global")) { 2 } else { 0 }
    if ($navigationScreenshots.Count -ne $expectedNavigation) {
        throw "Expected $expectedNavigation avatar menu screenshots for scope=$scope, found $($navigationScreenshots.Count)."
    }
    $expectedCards = if ($scope -in @("full", "cards")) { 6 } else { 0 }
    if ($syntheticCards.Count -ne $expectedCards) {
        throw "Expected $expectedCards synthetic Cards screenshots for scope=$scope, found $($syntheticCards.Count)."
    }
    if ($env:ANKI_E2E_REQUIRE_APKG_FIXTURE -eq "1" -and $scope -in @("full", "cards") -and $apkgCards.Count -ne 6) {
        throw "Expected 6 APKG Cards screenshots, found $($apkgCards.Count)."
    }

    Write-Host "Verified structured E2E artifacts: pages=$($pageScreenshots.Count), navigation=$($navigationScreenshots.Count), syntheticCards=$($syntheticCards.Count), apkgCards=$($apkgCards.Count)"
}

Push-Location $Root
try {
    if ($env:ANKI_E2E_NO_BUILD -eq "1") {
        $NoBuild = $true
    }

    if ($ImageSource -eq "ghcr") {
        if (-not $NoBuild) {
            throw "GHCR image source requires -NoBuild or ANKI_E2E_NO_BUILD=1."
        }
        if ($BuildOnly) {
            throw "GHCR image source does not support -BuildOnly."
        }
        if (-not $env:ANKI_E2E_IMAGE -or $env:ANKI_E2E_IMAGE -notmatch '^ghcr\.io/[a-z0-9._/-]+@sha256:[0-9a-f]{64}$') {
            throw "GHCR image source requires an exact digest reference in ANKI_E2E_IMAGE."
        }
        if ($env:ANKI_E2E_IMAGE -match ':latest') {
            throw "GHCR image source does not allow mutable latest references."
        }
        if ($env:ANKI_E2E_PACKAGE_SOURCE -notin @("fast-ci-artifact", "release-artifact")) {
            throw "GHCR image source requires a prebuilt Fast CI or release artifact package."
        }
        if (-not $env:ANKI_E2E_PREBUILT_ADDON_PATH) {
            throw "GHCR image source requires ANKI_E2E_PREBUILT_ADDON_PATH."
        }
    }

    Invoke-DockerCompose @("config", "--quiet")

    if (-not $NoBuild) {
        Invoke-DockerCompose @("build")
    }

    if ($BuildOnly) {
        return
    }

    $volume = "$($ArtifactsDir):/e2e/artifacts"
    $runArgs = @("run", "--rm", "-v", $volume)
    foreach ($name in @(
        "ANKI_E2E_IMAGE_SOURCE",
        "ANKI_E2E_PREBUILT_ADDON_PATH",
        "ANKI_E2E_PACKAGE_SOURCE",
        "ANKI_E2E_FAST_CI_RUN_ID",
        "ANKI_E2E_FAST_CI_TESTED_SHA",
        "ANKI_E2E_FAST_CI_PACKAGE_SHA256"
    )) {
        $value = if ($name -eq "ANKI_E2E_IMAGE_SOURCE") { $ImageSource } else { [Environment]::GetEnvironmentVariable($name) }
        if ($value) {
            $runArgs += @("-e", "$name=$value")
        }
    }
    if ($env:ANKI_E2E_REAL_MEDIA_DIR) {
        $realMediaPath = Resolve-Path -LiteralPath $env:ANKI_E2E_REAL_MEDIA_DIR -ErrorAction Stop
        $runArgs += @("-v", "$($realMediaPath.Path):/e2e/real-media:ro", "-e", "ANKI_E2E_REAL_MEDIA_DIR=/e2e/real-media")
    }
    if ($env:ANKI_E2E_REQUIRE_REAL_MEDIA) {
        $runArgs += @("-e", "ANKI_E2E_REQUIRE_REAL_MEDIA=$($env:ANKI_E2E_REQUIRE_REAL_MEDIA)")
    }
    $runArgs += "anki-e2e"
    try {
        Invoke-DockerCompose $runArgs
    } finally {
        Restore-E2EArtifactOwnership -Volume $volume
    }
    Assert-E2EArtifactManifest -ArtifactsRoot $ArtifactsDir
} finally {
    Pop-Location
}
