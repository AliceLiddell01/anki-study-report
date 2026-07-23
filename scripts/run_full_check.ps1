param(
    [switch]$SkipDocker,
    [switch]$CleanDocker,
    [switch]$DockerOnly,
    [switch]$Perf100,
    [switch]$RequireApkgFixture,
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
} else { "" }
$TimingNode = $null

function Write-Section {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Find-CommandPath {
    param([string[]]$Names)
    foreach ($name in $Names) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) { return $command.Source }
    }
    return $null
}

function Add-BundledNodeToPath {
    if (-not $env:USERPROFILE) { return }
    $deps = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies"
    $parts = @()
    foreach ($candidate in @((Join-Path $deps "node\bin"), (Join-Path $deps "bin"))) {
        if (Test-Path $candidate) { $parts += $candidate }
    }
    if ($parts.Count -gt 0) { $env:PATH = (($parts + @($env:PATH)) -join [IO.Path]::PathSeparator) }
}

function Invoke-TimingHelper {
    param([string[]]$Arguments)
    if (-not $TimingOutputPath) { return }
    if (-not $TimingNode) { throw "Timing helper cannot run before Node.js is resolved." }
    & $TimingNode "scripts/run_python.mjs" $TimingHelper @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Fast CI timing helper failed with exit code $LASTEXITCODE" }
}

function Initialize-TimingIfNeeded {
    if (-not $TimingOutputPath) { return }
    if (-not (Test-Path -LiteralPath $TimingHelper)) { throw "Timing helper not found: $TimingHelper" }
    if (Test-Path -LiteralPath $TimingOutputPath) {
        Invoke-TimingHelper @("validate", "--output", $TimingOutputPath, "--allow-running")
        return
    }
    $repository = if ($env:GITHUB_REPOSITORY) { $env:GITHUB_REPOSITORY } else { "AliceLiddell01/anki-study-report" }
    $eventName = if ($env:GITHUB_EVENT_NAME) { $env:GITHUB_EVENT_NAME } else { "local" }
    $branch = (& git branch --show-current).Trim()
    $ref = if ($env:GITHUB_REF) { $env:GITHUB_REF } elseif ($branch) { "refs/heads/$branch" } else { "refs/heads/local" }
    $sha = if ($env:GITHUB_SHA) { $env:GITHUB_SHA } else { (& git rev-parse HEAD).Trim() }
    $runId = if ($env:GITHUB_RUN_ID) { $env:GITHUB_RUN_ID } else { "1" }
    $runAttempt = if ($env:GITHUB_RUN_ATTEMPT) { $env:GITHUB_RUN_ATTEMPT } else { "1" }
    Invoke-TimingHelper @(
        "initialize", "--output", $TimingOutputPath,
        "--repository", $repository, "--event-name", $eventName, "--ref", $ref,
        "--tested-commit-sha", $sha, "--run-id", $runId, "--run-attempt", $runAttempt
    )
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
    $started = $false
    $exitCode = 0
    $errorRecord = $null
    if ($TimingOutputPath -and $TimingPhase) {
        Invoke-TimingHelper @("start", "--output", $TimingOutputPath, "--phase-id", $TimingPhase)
        $started = $true
    }
    Push-Location $WorkingDirectory
    try {
        & $FilePath @Arguments
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) { throw "$FilePath failed with exit code $exitCode" }
    } catch {
        $errorRecord = $_
        if ($exitCode -eq 0) { $exitCode = 1 }
    } finally {
        Pop-Location
        if ($started) {
            Invoke-TimingHelper @("finish", "--output", $TimingOutputPath, "--phase-id", $TimingPhase, "--exit-code", "$exitCode")
        }
    }
    if ($errorRecord) { throw $errorRecord }
}

function Invoke-DockerCompose {
    param([string[]]$Arguments)
    Invoke-CheckedCommand -Name "Docker compose $($Arguments -join ' ')" -FilePath "docker" -Arguments (@("compose", "-f", $ComposeFile) + $Arguments)
}

function Assert-RepositoryHygiene {
    Write-Section "Repository hygiene"
    $git = Find-CommandPath @("git.exe", "git")
    if (-not $git) { throw "Could not find git. Repository hygiene checks require Git." }
    & $git diff --check
    if ($LASTEXITCODE -ne 0) { throw "git diff --check failed with exit code $LASTEXITCODE" }
    $forbiddenPatterns = @(
        '(^|/)(e2e-artifacts|release-artifacts|\.playwright-auth|ci-fast|ci-fast-download|node_modules|__pycache__|\.pytest_cache)(/|$)',
        '^web-dashboard/(dist|screenshots)/',
        '^anki_study_report/(web_dashboard|user_files)/',
        '\.(ankiaddon|zip)$'
    )
    $tracked = @(& $git ls-files)
    if ($LASTEXITCODE -ne 0) { throw "git ls-files failed with exit code $LASTEXITCODE" }
    $forbidden = @($tracked | Where-Object {
        $path = $_
        @($forbiddenPatterns | Where-Object { $path -match $_ }).Count -gt 0
    })
    if ($forbidden.Count -gt 0) { throw "Forbidden generated/runtime files are tracked:`n$($forbidden -join "`n")" }
}

Set-Location $Root
Add-BundledNodeToPath
Assert-RepositoryHygiene

if ($RequireApkgFixture) {
    Write-Host "Compatibility input RequireApkgFixture accepted; committed real-deck packages are mandatory in every Docker mode."
}

if (-not $DockerOnly) {
    $node = Find-CommandPath @("node.exe", "node")
    if (-not $node) { throw "Could not find node. Install Node.js or use the bundled Codex runtime." }
    $TimingNode = $node
    $pnpm = Find-CommandPath @("pnpm.cmd", "pnpm")
    if (-not $pnpm) { throw "Could not find pnpm. Install pnpm or enable Corepack." }
    Initialize-TimingIfNeeded

    Invoke-CheckedCommand -Name "Structured changelog generated outputs" -FilePath $node -Arguments @("scripts/run_python.mjs", "scripts/generate_changelog.py", "--check") -TimingPhase "changelog-check"
    Invoke-CheckedCommand -Name "Frontend typecheck before tests" -FilePath $pnpm -Arguments @("run", "typecheck") -WorkingDirectory $DashboardDir -TimingPhase "frontend-typecheck-tests"
    Invoke-CheckedCommand -Name "Frontend tests" -FilePath $pnpm -Arguments @("run", "test:run") -WorkingDirectory $DashboardDir -TimingPhase "frontend-vitest"
    Invoke-CheckedCommand -Name "Build frontend production bundle" -FilePath $pnpm -Arguments @("run", "build:vite") -WorkingDirectory $DashboardDir -TimingPhase "frontend-vite-build"
    Invoke-CheckedCommand -Name "Validate frontend bundle" -FilePath $pnpm -Arguments @("run", "build:check-bundle") -WorkingDirectory $DashboardDir -TimingPhase "frontend-bundle-check"
    Invoke-CheckedCommand -Name "Synchronize dashboard assets into add-on" -FilePath $pnpm -Arguments @("run", "build:copy-addon") -WorkingDirectory $DashboardDir -TimingPhase "frontend-addon-assets-copy"
    Invoke-CheckedCommand -Name "Python tests" -FilePath $node -Arguments @("scripts/run_python.mjs", "-m", "pytest") -TimingPhase "python-pytest"
    Invoke-CheckedCommand -Name "Build and validate package archive" -FilePath $node -Arguments @("scripts/run_python.mjs", "scripts/package_addon.py", "--check") -TimingPhase "package-build-check"
    Invoke-CheckedCommand -Name "Verify package archive" -FilePath $node -Arguments @("scripts/run_python.mjs", "scripts/package_addon.py", "--check-only") -TimingPhase "package-check-only"
}

if (-not $SkipDocker) {
    if (-not (Test-Path $ComposeFile)) { throw "Docker compose file not found: $ComposeFile" }
    if (-not (Test-Path $DockerRunner)) { throw "Docker E2E runner not found: $DockerRunner" }
    if ($CleanDocker) { Invoke-DockerCompose @("down", "-v") }

    $previous = @{
        ANKI_E2E_PERF100 = $env:ANKI_E2E_PERF100
        ANKI_E2E_SCOPE = $env:ANKI_E2E_SCOPE
        ANKI_E2E_SCREENSHOT_WORKERS = $env:ANKI_E2E_SCREENSHOT_WORKERS
        ANKI_E2E_RESOURCE_TELEMETRY = $env:ANKI_E2E_RESOURCE_TELEMETRY
        ANKI_E2E_VERIFY_RESTART = $env:ANKI_E2E_VERIFY_RESTART
        ANKI_E2E_NO_BUILD = $env:ANKI_E2E_NO_BUILD
        E2E_MODE = $env:E2E_MODE
    }
    if (-not $env:E2E_MODE) { $env:E2E_MODE = if ($Perf100) { "perf100" } else { "standard" } }
    $env:ANKI_E2E_SCOPE = $E2EScope
    $env:ANKI_E2E_SCREENSHOT_WORKERS = if ($ScreenshotWorkers -eq "auto") { "3" } else { $ScreenshotWorkers }
    $env:ANKI_E2E_RESOURCE_TELEMETRY = if ($DisableResourceTelemetry) { "0" } elseif ($previous.ANKI_E2E_RESOURCE_TELEMETRY) { $previous.ANKI_E2E_RESOURCE_TELEMETRY } else { "1" }
    $env:ANKI_E2E_VERIFY_RESTART = switch ($VerifyRestart) { "true" { "1" }; "false" { "0" }; default { "auto" } }
    if ($NoDockerBuild) { $env:ANKI_E2E_NO_BUILD = "1" }
    if ($Perf100) { $env:ANKI_E2E_PERF100 = "1" }

    try {
        Write-Section "Docker E2E with committed real working decks"
        & $DockerRunner
        if ($LASTEXITCODE -ne 0) { throw "$DockerRunner failed with exit code $LASTEXITCODE" }
    } finally {
        foreach ($name in $previous.Keys) {
            $value = $previous[$name]
            if ($null -eq $value) { Remove-Item "Env:$name" -ErrorAction SilentlyContinue }
            else { Set-Item "Env:$name" $value }
        }
    }
}

Write-Host ""
Write-Host "Full check completed." -ForegroundColor Green
