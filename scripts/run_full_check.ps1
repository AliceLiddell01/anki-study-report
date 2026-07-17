param(
    [switch]$SkipDocker,
    [switch]$CleanDocker,
    [switch]$DockerOnly,
    [string]$ApkgFixture = "",
    [switch]$RequireApkgFixture,
    [switch]$Perf100,
    [ValidateSet("full", "global", "stats", "decks", "activity", "cards", "settings", "notifications")]
    [string]$E2EScope = "full",
    [ValidateSet("auto", "1", "2", "3", "4")]
    [string]$ScreenshotWorkers = "auto",
    [ValidateSet("auto", "true", "false")]
    [string]$VerifyRestart = "auto",
    [switch]$DisableResourceTelemetry,
    [switch]$NoDockerBuild,
    [string]$TimingOutput = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$DashboardDir = Join-Path $Root "web-dashboard"
$ComposeFile = Join-Path $Root "docker\anki-e2e\docker-compose.yml"
$DockerRunner = Join-Path $Root "scripts\run_anki_e2e_docker.ps1"
$TimingHelper = Join-Path $Root "scripts\ci_fast_timing.py"
$TimingOutputPath = if ($TimingOutput) {
    if ([IO.Path]::IsPathRooted($TimingOutput)) { $TimingOutput } else { Join-Path $Root $TimingOutput }
} else {
    ""
}
$TimingNode = $null

function Write-Section {
    param([string]$Message)

    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Invoke-TimingHelper {
    param([string[]]$Arguments)

    if (-not $TimingOutputPath) {
        return
    }
    if (-not $TimingNode) {
        throw "Timing helper cannot run before Node.js is resolved."
    }

    & $TimingNode "scripts/run_python.mjs" $TimingHelper @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Fast CI timing helper failed with exit code $LASTEXITCODE"
    }
}

function Invoke-CheckedCommand {
    param(
        [string]$Name,
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$WorkingDirectory = $Root,
        [string]$TimingPhase = ""
    )

    Write-Section $Name
    $phaseStarted = $false
    $commandError = $null
    $exitCode = 0

    if ($TimingOutputPath -and $TimingPhase) {
        Invoke-TimingHelper -Arguments @("start", "--output", $TimingOutputPath, "--phase-id", $TimingPhase)
        $phaseStarted = $true
    }

    Push-Location $WorkingDirectory
    try {
        & $FilePath @Arguments
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) {
            throw "$FilePath failed with exit code $exitCode"
        }
    } catch {
        $commandError = $_
        if ($exitCode -eq 0) {
            $exitCode = 1
        }
    } finally {
        Pop-Location
        if ($phaseStarted) {
            try {
                Invoke-TimingHelper -Arguments @(
                    "finish", "--output", $TimingOutputPath,
                    "--phase-id", $TimingPhase,
                    "--exit-code", "$exitCode"
                )
            } catch {
                if ($commandError) {
                    Write-Warning "Timing finalization failed after the canonical command failure: $($_.Exception.Message)"
                } else {
                    throw
                }
            }
        }
    }

    if ($commandError) {
        throw $commandError
    }
}

function Find-CommandPath {
    param([string[]]$Names)

    foreach ($name in $Names) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) {
            return $command.Source
        }
    }

    return $null
}

function Add-BundledNodeToPath {
    if (-not $env:USERPROFILE) {
        return
    }

    $deps = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies"
    $nodeBin = Join-Path $deps "node\bin"
    $sharedBin = Join-Path $deps "bin"
    $pathParts = @()

    if (Test-Path (Join-Path $nodeBin "node.exe")) {
        $pathParts += $nodeBin
    }
    if (Test-Path $sharedBin) {
        $pathParts += $sharedBin
    }

    if ($pathParts.Count -gt 0) {
        $env:PATH = (($pathParts + @($env:PATH)) -join [IO.Path]::PathSeparator)
    }
}

function Invoke-DockerCompose {
    param([string[]]$Arguments)

    Invoke-CheckedCommand `
        -Name "Docker compose $($Arguments -join ' ')" `
        -FilePath "docker" `
        -Arguments (@("compose", "-f", $ComposeFile) + $Arguments)
}

function Invoke-CheckedPowerShellScript {
    param(
        [string]$Name,
        [string]$ScriptPath,
        [string[]]$Arguments
    )

    Write-Section $Name
    & $ScriptPath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$ScriptPath failed with exit code $LASTEXITCODE"
    }
}

function Assert-RepositoryHygiene {
    Write-Section "Repository hygiene"

    $git = Find-CommandPath @("git.exe", "git")
    if (-not $git) {
        throw "Could not find git. Repository hygiene checks require Git."
    }

    & $git diff --check
    if ($LASTEXITCODE -ne 0) {
        throw "git diff --check failed with exit code $LASTEXITCODE"
    }

    $forbiddenPatterns = @(
        '(^|/)(e2e-artifacts|release-artifacts|\.playwright-auth|ci-fast|ci-fast-download|node_modules|__pycache__|\.pytest_cache)(/|$)',
        '^web-dashboard/(dist|screenshots)/',
        '^anki_study_report/(web_dashboard|user_files)/',
        '\.(ankiaddon|zip)$'
    )
    $trackedFiles = @(& $git ls-files)
    if ($LASTEXITCODE -ne 0) {
        throw "git ls-files failed with exit code $LASTEXITCODE"
    }

    $forbiddenTrackedFiles = @(
        $trackedFiles | Where-Object {
            $path = $_
            $forbiddenPatterns | Where-Object { $path -match $_ }
        }
    )
    if ($forbiddenTrackedFiles.Count -gt 0) {
        throw "Forbidden generated/runtime files are tracked:`n$($forbiddenTrackedFiles -join "`n")"
    }
}

function Initialize-TimingIfNeeded {
    if (-not $TimingOutputPath) {
        return
    }
    if (-not (Test-Path -LiteralPath $TimingHelper)) {
        throw "Timing helper not found: $TimingHelper"
    }
    if (Test-Path -LiteralPath $TimingOutputPath) {
        Invoke-TimingHelper -Arguments @("validate", "--output", $TimingOutputPath, "--allow-running")
        return
    }

    $repository = if ($env:GITHUB_REPOSITORY) { $env:GITHUB_REPOSITORY } else { "AliceLiddell01/anki-study-report" }
    $eventName = if ($env:GITHUB_EVENT_NAME) { $env:GITHUB_EVENT_NAME } else { "local" }
    $ref = if ($env:GITHUB_REF) { $env:GITHUB_REF } else {
        $branch = (& git branch --show-current).Trim()
        if ($branch) { "refs/heads/$branch" } else { "refs/heads/local" }
    }
    $sha = if ($env:GITHUB_SHA) { $env:GITHUB_SHA } else { (& git rev-parse HEAD).Trim() }
    $runId = if ($env:GITHUB_RUN_ID) { $env:GITHUB_RUN_ID } else { "1" }
    $runAttempt = if ($env:GITHUB_RUN_ATTEMPT) { $env:GITHUB_RUN_ATTEMPT } else { "1" }

    Invoke-TimingHelper -Arguments @(
        "initialize", "--output", $TimingOutputPath,
        "--repository", $repository,
        "--event-name", $eventName,
        "--ref", $ref,
        "--tested-commit-sha", $sha,
        "--run-id", $runId,
        "--run-attempt", $runAttempt
    )
}

Set-Location $Root
Add-BundledNodeToPath
Assert-RepositoryHygiene

if (-not $DockerOnly) {
    $node = Find-CommandPath @("node.exe", "node")
    if (-not $node) {
        throw "Could not find node. Install Node.js or use the bundled Codex runtime."
    }
    $TimingNode = $node

    $pnpm = Find-CommandPath @("pnpm.cmd", "pnpm")
    if (-not $pnpm) {
        throw "Could not find pnpm. Install pnpm or enable Corepack, then rerun this script."
    }

    Initialize-TimingIfNeeded

    Invoke-CheckedCommand `
        -Name "Structured changelog generated outputs" `
        -FilePath $node `
        -Arguments @("scripts/run_python.mjs", "scripts/generate_changelog.py", "--check") `
        -TimingPhase "changelog-check"

    Invoke-CheckedCommand `
        -Name "Frontend typecheck before tests" `
        -FilePath $pnpm `
        -Arguments @("run", "typecheck") `
        -WorkingDirectory $DashboardDir `
        -TimingPhase "frontend-typecheck-tests"

    Invoke-CheckedCommand `
        -Name "Frontend tests" `
        -FilePath $pnpm `
        -Arguments @("run", "test:run") `
        -WorkingDirectory $DashboardDir `
        -TimingPhase "frontend-vitest"

    # Package validation must see freshly copied add-on assets, not only web-dashboard/dist.
    Invoke-CheckedCommand `
        -Name "Build frontend production bundle" `
        -FilePath $pnpm `
        -Arguments @("run", "build:vite") `
        -WorkingDirectory $DashboardDir `
        -TimingPhase "frontend-vite-build"

    Invoke-CheckedCommand `
        -Name "Validate frontend bundle" `
        -FilePath $pnpm `
        -Arguments @("run", "build:check-bundle") `
        -WorkingDirectory $DashboardDir `
        -TimingPhase "frontend-bundle-check"

    Invoke-CheckedCommand `
        -Name "Synchronize dashboard assets into add-on" `
        -FilePath $pnpm `
        -Arguments @("run", "build:copy-addon") `
        -WorkingDirectory $DashboardDir `
        -TimingPhase "frontend-addon-assets-copy"

    Invoke-CheckedCommand `
        -Name "Python tests" `
        -FilePath $node `
        -Arguments @("scripts/run_python.mjs", "-m", "pytest") `
        -TimingPhase "python-pytest"

    Invoke-CheckedCommand `
        -Name "Build and validate package archive" `
        -FilePath $node `
        -Arguments @("scripts/run_python.mjs", "scripts/package_addon.py", "--check") `
        -TimingPhase "package-build-check"

    Invoke-CheckedCommand `
        -Name "Verify package archive" `
        -FilePath $node `
        -Arguments @("scripts/run_python.mjs", "scripts/package_addon.py", "--check-only") `
        -TimingPhase "package-check-only"
}

if (-not $SkipDocker) {
    if (-not (Test-Path $ComposeFile)) {
        throw "Docker compose file not found: $ComposeFile"
    }
    if (-not (Test-Path $DockerRunner)) {
        throw "Docker E2E runner not found: $DockerRunner"
    }

    if ($CleanDocker) {
        Invoke-DockerCompose @("down", "-v")
    }

    $previousApkgFixture = $env:ANKI_E2E_APKG_FIXTURE
    $previousRequireApkgFixture = $env:ANKI_E2E_REQUIRE_APKG_FIXTURE
    $previousPerf100 = $env:ANKI_E2E_PERF100
    $previousScope = $env:ANKI_E2E_SCOPE
    $previousWorkers = $env:ANKI_E2E_SCREENSHOT_WORKERS
    $previousTelemetry = $env:ANKI_E2E_RESOURCE_TELEMETRY
    $previousRestart = $env:ANKI_E2E_VERIFY_RESTART
    $previousNoBuild = $env:ANKI_E2E_NO_BUILD
    $previousMode = $env:E2E_MODE
    if (-not $env:E2E_MODE) {
        $env:E2E_MODE = if ($Perf100) { "perf100" } elseif ($RequireApkgFixture) { "strict-apkg" } else { "standard" }
    }
    $env:ANKI_E2E_SCOPE = $E2EScope
    $env:ANKI_E2E_SCREENSHOT_WORKERS = if ($ScreenshotWorkers -eq "auto") { "3" } else { $ScreenshotWorkers }
    $env:ANKI_E2E_RESOURCE_TELEMETRY = if ($DisableResourceTelemetry) {
        "0"
    } elseif ($previousTelemetry) {
        $previousTelemetry
    } else {
        "1"
    }
    $env:ANKI_E2E_VERIFY_RESTART = if ($PSBoundParameters.ContainsKey("VerifyRestart")) {
        switch ($VerifyRestart) { "true" { "1" }; "false" { "0" }; default { "auto" } }
    } elseif ($previousRestart) {
        $previousRestart
    } else {
        "auto"
    }
    if ($NoDockerBuild) { $env:ANKI_E2E_NO_BUILD = "1" }
    if ($ApkgFixture) {
        $env:ANKI_E2E_APKG_FIXTURE = $ApkgFixture
    }
    if ($RequireApkgFixture) {
        $env:ANKI_E2E_REQUIRE_APKG_FIXTURE = "1"
    }
    if ($Perf100) {
        $env:ANKI_E2E_PERF100 = "1"
    }

    try {
        Invoke-CheckedPowerShellScript `
            -Name "Docker E2E" `
            -ScriptPath $DockerRunner `
            -Arguments @()
    } finally {
        if ($null -eq $previousApkgFixture) {
            Remove-Item Env:\ANKI_E2E_APKG_FIXTURE -ErrorAction SilentlyContinue
        } else {
            $env:ANKI_E2E_APKG_FIXTURE = $previousApkgFixture
        }
        if ($null -eq $previousRequireApkgFixture) {
            Remove-Item Env:\ANKI_E2E_REQUIRE_APKG_FIXTURE -ErrorAction SilentlyContinue
        } else {
            $env:ANKI_E2E_REQUIRE_APKG_FIXTURE = $previousRequireApkgFixture
        }
        if ($null -eq $previousPerf100) {
            Remove-Item Env:\ANKI_E2E_PERF100 -ErrorAction SilentlyContinue
        } else {
            $env:ANKI_E2E_PERF100 = $previousPerf100
        }
        foreach ($item in @(
            @{ Name = "ANKI_E2E_SCOPE"; Value = $previousScope },
            @{ Name = "ANKI_E2E_SCREENSHOT_WORKERS"; Value = $previousWorkers },
            @{ Name = "ANKI_E2E_RESOURCE_TELEMETRY"; Value = $previousTelemetry },
            @{ Name = "ANKI_E2E_VERIFY_RESTART"; Value = $previousRestart },
            @{ Name = "ANKI_E2E_NO_BUILD"; Value = $previousNoBuild },
            @{ Name = "E2E_MODE"; Value = $previousMode }
        )) {
            if ($null -eq $item.Value) { Remove-Item "Env:$($item.Name)" -ErrorAction SilentlyContinue }
            else { Set-Item "Env:$($item.Name)" $item.Value }
        }
    }
}

Write-Host ""
Write-Host "Full check completed." -ForegroundColor Green
