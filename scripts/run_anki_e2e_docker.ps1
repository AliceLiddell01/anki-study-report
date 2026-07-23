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
$ArtifactsDir = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath $ArtifactsDir).Path)

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
        "run", "--rm", "--no-deps", "-v", $Volume,
        "--entrypoint", "/bin/chown", "anki-e2e", "-R", "$($uid):$($gid)", "/e2e/artifacts"
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

    $requiredReports = @(
        "reports/real-deck-manifest-report.json",
        "reports/real-deck-import-report.json",
        "reports/collection-inventory.json",
        "reports/anchor-resolution-report.json",
        "reports/scenario-application-report.json",
        "reports/api-smoke-first.json",
        "reports/browser-smoke-first.json"
    )
    foreach ($relativePath in $requiredReports) {
        if ($relativePath -notin $indexedPaths) {
            throw "Required real-deck proof is absent from artifact manifest: $relativePath"
        }
    }

    $realManifest = Get-Content -Raw -LiteralPath (Join-Path $ArtifactsRoot "reports/real-deck-manifest-report.json") | ConvertFrom-Json
    $import = Get-Content -Raw -LiteralPath (Join-Path $ArtifactsRoot "reports/real-deck-import-report.json") | ConvertFrom-Json
    $inventory = Get-Content -Raw -LiteralPath (Join-Path $ArtifactsRoot "reports/collection-inventory.json") | ConvertFrom-Json
    $anchors = Get-Content -Raw -LiteralPath (Join-Path $ArtifactsRoot "reports/anchor-resolution-report.json") | ConvertFrom-Json
    $scenarios = Get-Content -Raw -LiteralPath (Join-Path $ArtifactsRoot "reports/scenario-application-report.json") | ConvertFrom-Json
    $api = Get-Content -Raw -LiteralPath (Join-Path $ArtifactsRoot "reports/api-smoke-first.json") | ConvertFrom-Json
    $browser = Get-Content -Raw -LiteralPath (Join-Path $ArtifactsRoot "reports/browser-smoke-first.json") | ConvertFrom-Json

    foreach ($proof in @($realManifest, $import, $inventory, $anchors, $scenarios)) {
        if ($proof.status -ne "PASS") {
            throw "A required real-deck report did not report PASS."
        }
    }
    if ($realManifest.packageCount -ne 3 -or @($import.packages).Count -ne 3) {
        throw "Expected exactly three validated and imported real-deck packages."
    }
    if ($inventory.contentSource -ne "committed-real-apkg-only" -or $inventory.syntheticNotes -ne 0 -or $inventory.syntheticCards -ne 0 -or $inventory.syntheticMedia -ne 0) {
        throw "Collection inventory is not real-APKG-only."
    }
    if ($scenarios.contentMutation.notesCreated -ne 0 -or $scenarios.contentMutation.cardsCreated -ne 0 -or $scenarios.perf100.notesOrCardsCloned -ne 0) {
        throw "Scenario preparation created or cloned collection content."
    }
    if ($api.ok -ne $true -or $browser.ok -ne $true) {
        throw "API or browser real-deck smoke did not pass."
    }

    $screenshots = @($manifest.screenshots)
    $pageScreenshots = @($screenshots | Where-Object { $_.kind -eq "page" })
    $realDeckCards = @($screenshots | Where-Object { $_.kind -eq "cards" -and $_.fixture -eq "real-decks" })
    $syntheticCards = @($screenshots | Where-Object { $_.kind -eq "cards" -and $_.fixture -in @("synthetic", "apkg") })
    if ($pageScreenshots.Count -ne 10) {
        throw "Expected 10 real-dashboard page screenshots, found $($pageScreenshots.Count)."
    }
    if ($realDeckCards.Count -ne 6) {
        throw "Expected 6 real-deck preview screenshots, found $($realDeckCards.Count)."
    }
    if ($syntheticCards.Count -ne 0) {
        throw "Synthetic/legacy APKG screenshots remain in the artifact set."
    }

    Write-Host "Verified real-deck E2E artifacts: packages=3 anchors=$($anchors.resolvedCount) pages=$($pageScreenshots.Count) previews=$($realDeckCards.Count) synthetic=0"
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
        "ANKI_E2E_FAST_CI_PACKAGE_SHA256",
        "ANKI_E2E_PERF100",
        "E2E_MODE",
        "ANKI_E2E_SCOPE",
        "ANKI_E2E_SCREENSHOT_WORKERS",
        "ANKI_E2E_RESOURCE_TELEMETRY",
        "ANKI_E2E_VERIFY_RESTART"
    )) {
        $value = if ($name -eq "ANKI_E2E_IMAGE_SOURCE") { $ImageSource } else { [Environment]::GetEnvironmentVariable($name) }
        if ($value) {
            $runArgs += @("-e", "$name=$value")
        }
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
