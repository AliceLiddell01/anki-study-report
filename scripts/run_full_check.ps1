param(
    [switch]$SkipDocker,
    [switch]$CleanDocker,
    [switch]$DockerOnly
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

Set-Location $Root
Add-BundledNodeToPath

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

    Invoke-CheckedCommand `
        -Name "Frontend production build" `
        -FilePath $pnpm `
        -Arguments @("run", "build") `
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

    Invoke-CheckedCommand `
        -Name "Docker E2E" `
        -FilePath "powershell" `
        -Arguments @("-ExecutionPolicy", "Bypass", "-File", $DockerRunner)
}

Write-Host ""
Write-Host "Full check completed." -ForegroundColor Green
