[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("cards", "full")]
    [string]$Scope,

    [Parameter(Mandatory = $true)]
    [ValidatePattern("^[0-9a-f]{64}$")]
    [string]$ExpectedPackageSha256,

    [Parameter(Mandatory = $true)]
    [ValidatePattern("^[0-9a-f]{40}$")]
    [string]$OwnerReviewSha,

    [Parameter(Mandatory = $true)]
    [ValidatePattern("^[0-9a-f]{40}$")]
    [string]$WorkflowSourceSha,

    [Parameter(Mandatory = $true)]
    [string]$PackageArtifactId,

    [Parameter(Mandatory = $true)]
    [string]$PackageArtifactDigest,

    [Parameter(Mandatory = $true)]
    [ValidatePattern("^[0-9a-f]{64}$")]
    [string]$PackageManifestSha256,

    [Parameter(Mandatory = $true)]
    [int]$PackageEntryCount,

    [Parameter(Mandatory = $true)]
    [long]$SourceRunId,

    [Parameter(Mandatory = $true)]
    [string]$RefName
)

$ErrorActionPreference = "Stop"
$rawDirectory = "r7-e2e-raw-$Scope"
$outputDirectory = "r7-e2e-$Scope"
$packageInput = "r7-input/anki_study_report.ankiaddon"
$metadataInput = "r7-input/r7-package-metadata.json"
$stagedPackage = "docker/anki-e2e/local-input/anki_study_report.ankiaddon"
$testedPackage = "e2e-artifacts/package/anki_study_report.ankiaddon"

Remove-Item e2e-artifacts, $rawDirectory, $outputDirectory -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $rawDirectory | Out-Null
$logPath = Join-Path $rawDirectory "e2e-run.log"
$startedAt = [DateTime]::UtcNow.ToString("o")
$exitCode = 0

$env:ANKI_E2E_SCOPE = $Scope
$env:ANKI_E2E_SCREENSHOT_WORKERS = "3"
$env:ANKI_E2E_RESOURCE_TELEMETRY = "1"
$env:ANKI_E2E_VERIFY_RESTART = "1"
$env:ANKI_E2E_NO_BUILD = "1"
$env:ANKI_E2E_CACHE_BACKEND = "ghcr-digest"
$env:ANKI_E2E_PREBUILT_ADDON_PATH = "/e2e/local-input/anki_study_report.ankiaddon"
$env:ANKI_VERSION = "26.05"

try {
    if (-not (Test-Path -LiteralPath $packageInput -PathType Leaf)) {
        throw "Downloaded exact package is missing."
    }
    if (-not (Test-Path -LiteralPath $metadataInput -PathType Leaf)) {
        throw "Downloaded R7 package metadata is missing."
    }

    $metadata = Get-Content -LiteralPath $metadataInput -Raw | ConvertFrom-Json
    $packageSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $packageInput).Hash.ToLowerInvariant()
    if ($packageSha -ne $ExpectedPackageSha256) {
        throw "Downloaded package SHA-256 mismatch: $packageSha"
    }
    if ([string]$metadata.testedCommitSha -ne $OwnerReviewSha) {
        throw "Downloaded package tested SHA mismatch."
    }
    if ([string]$metadata.sourceHeadSha -ne $OwnerReviewSha) {
        throw "Downloaded package source head mismatch."
    }
    if ([string]$metadata.packageSha256 -ne $packageSha) {
        throw "Downloaded package metadata SHA mismatch."
    }
    if ([long]$metadata.packageSizeBytes -ne (Get-Item -LiteralPath $packageInput).Length) {
        throw "Downloaded package metadata size mismatch."
    }

    New-Item -ItemType Directory -Force (Split-Path -Parent $stagedPackage) | Out-Null
    Copy-Item -LiteralPath $packageInput -Destination $stagedPackage -Force

    & .\scripts\run_full_check.ps1 `
        -DockerOnly `
        -E2EScope $Scope `
        -ScreenshotWorkers 3 `
        -NoDockerBuild *>&1 | Tee-Object -FilePath $logPath
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        throw "Canonical $Scope real-Anki E2E failed with exit code $exitCode."
    }
}
catch {
    if ($exitCode -eq 0) {
        $exitCode = 1
    }
    $_ | Out-String | Add-Content -LiteralPath $logPath
}
finally {
    try {
        if (-not (Test-Path -LiteralPath $testedPackage -PathType Leaf)) {
            throw "E2E package evidence is missing."
        }
        $testedSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $testedPackage).Hash.ToLowerInvariant()
        if ($testedSha -ne $ExpectedPackageSha256) {
            throw "The package tested by real Anki differs from the exact R7 package: $testedSha"
        }

        New-Item -ItemType Directory -Force e2e-artifacts/reports | Out-Null
        [ordered]@{
            schemaVersion = 1
            scope = $Scope
            ownerReviewSha = $OwnerReviewSha
            e2eCheckoutSha = (git rev-parse HEAD).Trim().ToLowerInvariant()
            e2ePackageSha256 = $testedSha
            packageArtifactId = $PackageArtifactId
            packageArtifactDigest = $PackageArtifactDigest
            packageManifestSha256 = $PackageManifestSha256
            packageEntryCount = $PackageEntryCount
        } | ConvertTo-Json | Set-Content e2e-artifacts/reports/r7-package-provenance.json -Encoding utf8NoBOM

        [ordered]@{
            schemaVersion = 1
            imageSource = "ghcr"
            imageReference = $env:ANKI_E2E_IMAGE
            imageDigest = $env:ANKI_E2E_IMAGE_DIGEST
            imagePlatform = $env:ANKI_E2E_IMAGE_PLATFORM
            imagePreparationDurationMs = [long]$env:ANKI_E2E_IMAGE_PREPARATION_DURATION_MS
            imageSizeBytes = [long]$env:ANKI_E2E_IMAGE_SIZE_BYTES
            environmentContractSha256 = $env:ANKI_E2E_ENVIRONMENT_CONTRACT_SHA256
            environmentPublicationRunId = [long]$env:ANKI_E2E_ENVIRONMENT_PUBLICATION_RUN_ID
            environmentReuseVerificationRunId = [long]$env:ANKI_E2E_ENVIRONMENT_REUSE_VERIFICATION_RUN_ID
            cacheState = "ghcr-digest"
            workflowSourceSha = $WorkflowSourceSha
            e2eCheckoutSha = $OwnerReviewSha
            packageSource = "fast-ci-artifact"
            sourceFastCiRunId = $SourceRunId
            sourceFastCiTestedSha = $OwnerReviewSha
            sourcePackageSha256 = $testedSha
        } | ConvertTo-Json | Set-Content e2e-artifacts/reports/environment-image-provenance.json -Encoding utf8NoBOM
    }
    catch {
        $exitCode = 1
        $_ | Out-String | Add-Content -LiteralPath $logPath
    }

    try {
        if (-not (Test-Path -LiteralPath e2e-artifacts -PathType Container)) {
            throw "Canonical E2E artifacts are missing."
        }
        python scripts/prepare_ci_e2e_artifacts.py `
            --source e2e-artifacts `
            --output $outputDirectory `
            --raw-logs $rawDirectory `
            --mode standard `
            --scope $Scope `
            --screenshot-workers 3 `
            --build-duration-ms 0 `
            --image-size-bytes $env:ANKI_E2E_IMAGE_SIZE_BYTES `
            --cache-state ghcr-digest `
            --e2e-exit-code $exitCode `
            --started-at $startedAt `
            --commit-sha $OwnerReviewSha `
            --ref $RefName `
            --package-source fast-ci-artifact `
            --source-fast-ci-run-id $SourceRunId `
            --source-fast-ci-tested-sha $OwnerReviewSha `
            --source-package-sha256 $ExpectedPackageSha256 `
            --e2e-checkout-sha $OwnerReviewSha
        if ($LASTEXITCODE -ne 0) {
            throw "Redacted evidence preparation failed."
        }

        $resolvedRoot = (Resolve-Path -LiteralPath $outputDirectory).Path
        $images = @(
            Get-ChildItem -LiteralPath $outputDirectory -Recurse -File |
                Where-Object { $_.Extension.ToLowerInvariant() -in @(".png", ".jpg", ".jpeg", ".webp") } |
                Sort-Object FullName |
                ForEach-Object {
                    [ordered]@{
                        path = [IO.Path]::GetRelativePath($resolvedRoot, $_.FullName).Replace("\", "/")
                        size = $_.Length
                    }
                }
        )
        if ($images.Count -eq 0) {
            throw "No screenshots were found in redacted $Scope evidence."
        }
        $jsonReports = @(
            Get-ChildItem -LiteralPath $outputDirectory -Recurse -File -Filter *.json |
                Sort-Object FullName |
                ForEach-Object { [IO.Path]::GetRelativePath($resolvedRoot, $_.FullName).Replace("\", "/") }
        )
        [ordered]@{
            schemaVersion = 1
            scope = $Scope
            count = $images.Count
            files = $images
            jsonReports = $jsonReports
        } | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $outputDirectory "r7-screenshot-inventory.json") -Encoding utf8NoBOM
        Set-Content -LiteralPath "r7-$Scope-screenshot-count.txt" -Value $images.Count -Encoding ascii
    }
    catch {
        $exitCode = 1
        $_ | Out-String | Add-Content -LiteralPath $logPath
    }

    if ($env:ANKI_E2E_IMAGE) {
        docker compose `
            -f docker/anki-e2e/docker-compose.yml `
            -f docker/anki-e2e/docker-compose.ghcr.yml `
            down -v --remove-orphans | Out-Null
    }
}

if ($exitCode -ne 0) {
    throw "$Scope real-Anki E2E or evidence preparation failed."
}
