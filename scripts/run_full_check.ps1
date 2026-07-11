param(
    [switch]$SkipDocker,
    [switch]$CleanDocker,
    [switch]$DockerOnly,
    [string]$ApkgFixture = "",
    [switch]$RequireApkgFixture,
    [switch]$Perf100
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$DashboardDir = Join-Path $Root "web-dashboard"
$ComposeFile = Join-Path $Root "docker\anki-e2e\docker-compose.yml"
$DockerRunner = Join-Path $Root "scripts\run_anki_e2e_docker.ps1"

function Write-Section {
    param([string]$Message)

    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Invoke-CheckedCommand {
    param(
        [string]$Name,
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$WorkingDirectory = $Root
    )

    Write-Section $Name
    Push-Location $WorkingDirectory
    try {
        & $FilePath @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "$FilePath failed with exit code $LASTEXITCODE"
        }
    } finally {
        Pop-Location
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
        '(^|/)(e2e-artifacts|ci-fast|ci-fast-download|node_modules|__pycache__|\.pytest_cache)(/|$)',
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

Set-Location $Root
Add-BundledNodeToPath
Assert-RepositoryHygiene

$node = Find-CommandPath @("node.exe", "node")
if (-not $node) {
    throw "Could not find node. Install Node.js or use the bundled Codex runtime."
}

$pnpm = Find-CommandPath @("pnpm.cmd", "pnpm")
if (-not $pnpm) {
    throw "Could not find pnpm. Install pnpm or enable Corepack, then rerun this script."
}

if (-not $DockerOnly) {
    Invoke-CheckedCommand `
        -Name "Python tests" `
        -FilePath $node `
        -Arguments @("scripts/run_python.mjs", "-m", "pytest")

    Invoke-CheckedCommand `
        -Name "Frontend tests" `
        -FilePath $pnpm `
        -Arguments @("run", "test:frontend") `
        -WorkingDirectory $DashboardDir

    # Package validation must see freshly copied add-on assets, not only web-dashboard/dist.
    Invoke-CheckedCommand `
        -Name "Build frontend assets for add-on" `
        -FilePath $pnpm `
        -Arguments @("run", "build:addon") `
        -WorkingDirectory $DashboardDir

    Invoke-CheckedCommand `
        -Name "Build and validate package archive" `
        -FilePath $node `
        -Arguments @("scripts/run_python.mjs", "scripts/package_addon.py", "--check")

    Invoke-CheckedCommand `
        -Name "Verify package archive" `
        -FilePath $node `
        -Arguments @("scripts/run_python.mjs", "scripts/package_addon.py", "--check-only")
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
        Invoke-CheckedCommand `
            -Name "Docker E2E" `
            -FilePath "powershell" `
            -Arguments @("-ExecutionPolicy", "Bypass", "-File", $DockerRunner)
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
    }
}

Write-Host ""
Write-Host "Full check completed." -ForegroundColor Green
