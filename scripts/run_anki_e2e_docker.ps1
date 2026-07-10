param(
    [switch]$BuildOnly,
    [switch]$NoBuild,
    [string]$ArtifactsDir = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ComposeFile = Join-Path $Root "docker\anki-e2e\docker-compose.yml"
$LocalInputDir = Join-Path $Root "docker\anki-e2e\local-input"
$LocalApkgName = "asr-e2e-render-fixtures.apkg"
$LocalApkgPath = Join-Path $LocalInputDir $LocalApkgName

if (-not (Test-Path $ComposeFile)) {
    throw "Docker compose file not found: $ComposeFile"
}

if (-not $ArtifactsDir) {
    $ArtifactsDir = Join-Path $Root "e2e-artifacts"
}

New-Item -ItemType Directory -Force -Path $ArtifactsDir | Out-Null
New-Item -ItemType Directory -Force -Path $LocalInputDir | Out-Null

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

    & docker compose -f $ComposeFile @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose failed: $($Arguments -join ' ')"
    }
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
    if ($pageScreenshots.Count -ne 18) {
        throw "Expected 18 page screenshots, found $($pageScreenshots.Count)."
    }
    if ($navigationScreenshots.Count -ne 2) {
        throw "Expected 2 avatar menu screenshots, found $($navigationScreenshots.Count)."
    }
    if ($syntheticCards.Count -ne 6) {
        throw "Expected 6 synthetic Cards screenshots, found $($syntheticCards.Count)."
    }
    if ($env:ANKI_E2E_REQUIRE_APKG_FIXTURE -eq "1" -and $apkgCards.Count -ne 6) {
        throw "Expected 6 APKG Cards screenshots, found $($apkgCards.Count)."
    }

    Write-Host "Verified structured E2E artifacts: pages=$($pageScreenshots.Count), navigation=$($navigationScreenshots.Count), syntheticCards=$($syntheticCards.Count), apkgCards=$($apkgCards.Count)"
}

Push-Location $Root
try {
    if (-not $NoBuild) {
        Invoke-DockerCompose @("build")
    }

    if ($BuildOnly) {
        return
    }

    $volume = "$($ArtifactsDir):/e2e/artifacts"
    $runArgs = @("run", "--rm", "-v", $volume)
    if ($env:ANKI_E2E_REAL_MEDIA_DIR) {
        $realMediaPath = Resolve-Path -LiteralPath $env:ANKI_E2E_REAL_MEDIA_DIR -ErrorAction Stop
        $runArgs += @("-v", "$($realMediaPath.Path):/e2e/real-media:ro", "-e", "ANKI_E2E_REAL_MEDIA_DIR=/e2e/real-media")
    }
    if ($env:ANKI_E2E_REQUIRE_REAL_MEDIA) {
        $runArgs += @("-e", "ANKI_E2E_REQUIRE_REAL_MEDIA=$($env:ANKI_E2E_REQUIRE_REAL_MEDIA)")
    }
    $runArgs += "anki-e2e"
    Invoke-DockerCompose $runArgs
    Assert-E2EArtifactManifest -ArtifactsRoot $ArtifactsDir
} finally {
    Pop-Location
}
