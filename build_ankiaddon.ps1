param(
    [switch]$SkipInstall,
    [switch]$SkipFrontendTests,
    [switch]$SkipPythonTests
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$DashboardDir = Join-Path $Root "web-dashboard"
$AddonDir = Join-Path $Root "anki_study_report"
$Archive = Join-Path $Root "anki_study_report.ankiaddon"

function Assert-ProjectRoot {
    $requiredFiles = @(
        (Join-Path $DashboardDir "package.json"),
        (Join-Path $AddonDir "manifest.json"),
        (Join-Path $Root "scripts\package_addon.py")
    )

    $missing = @($requiredFiles | Where-Object { -not (Test-Path -LiteralPath $_ -PathType Leaf) })
    if ($missing.Count -gt 0) {
        throw @"
build_ankiaddon.ps1 must be run from the Anki Study Report project root.
Resolved root: $Root
Missing required files:
$($missing -join "`n")
"@
    }
}

function Write-Section {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Script
    )

    Write-Section $Name
    & $Script
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

function Find-PythonCommand {
    $candidates = @()

    if ($env:PYTHON) {
        $candidates += ,@($env:PYTHON)
    }

    if ($env:USERPROFILE) {
        $bundledPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
        if (Test-Path $bundledPython) {
            $candidates += ,@($bundledPython)
        }
    }

    $candidates += ,@("python")
    $candidates += ,@("python3")
    if ($IsWindows -or $env:OS -eq "Windows_NT") {
        $candidates += ,@("py", "-3")
    }

    foreach ($candidate in $candidates) {
        try {
            $extraArgs = @($candidate | Select-Object -Skip 1)
            $probe = & $candidate[0] @extraArgs --version 2>&1
            if ($LASTEXITCODE -eq 0 -and ($probe -join "`n") -match "Python") {
                return ,$candidate
            }
        } catch {
            continue
        }
    }

    throw "Could not find Python. Set PYTHON to a full Python executable path."
}

function Invoke-Python {
    param(
        [string[]]$Arguments
    )

    $command = Find-PythonCommand
    $extraArgs = @($command | Select-Object -Skip 1)
    & $command[0] @extraArgs @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed: $($Arguments -join ' ')"
    }
}

function Invoke-Pnpm {
    param(
        [string[]]$Arguments
    )

    $pnpm = Find-CommandPath @("pnpm.cmd", "pnpm")
    if (-not $pnpm) {
        throw "Could not find pnpm. Install pnpm or enable Corepack, then rerun this script."
    }

    Push-Location $DashboardDir
    try {
        & $pnpm @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "pnpm command failed: $($Arguments -join ' ')"
        }
    } finally {
        Pop-Location
    }
}

function Remove-PythonCaches {
    Get-ChildItem -Path $AddonDir -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
        Remove-Item -Recurse -Force
}

Set-Location $Root
Assert-ProjectRoot
Add-BundledNodeToPath

Invoke-Step "Check JSON files" {
    Invoke-Python -Arguments @("-m", "json.tool", (Join-Path $AddonDir "manifest.json")) | Out-Null
    Invoke-Python -Arguments @("-m", "json.tool", (Join-Path $AddonDir "config.json")) | Out-Null
}

Invoke-Step "Compile Python files" {
    $pythonFiles = Get-ChildItem -Path $AddonDir -Recurse -Filter "*.py" -File |
        Where-Object { $_.FullName -notmatch "\\__pycache__\\" } |
        Sort-Object FullName |
        ForEach-Object { $_.FullName }

    if (-not $pythonFiles) {
        throw "No Python files found under $AddonDir"
    }

    Invoke-Python -Arguments (@("-B", "-m", "py_compile") + $pythonFiles)
    Remove-PythonCaches
}

if (-not $SkipInstall) {
    Invoke-Step "Install frontend dependencies" {
        Invoke-Pnpm -Arguments @("install", "--frozen-lockfile")
    }
}

if (-not $SkipFrontendTests) {
    Invoke-Step "Run frontend tests" {
        Invoke-Pnpm -Arguments @("run", "test:frontend")
    }
}

Invoke-Step "Build frontend assets for add-on" {
    Invoke-Pnpm -Arguments @("run", "build:addon")
}

if (-not $SkipPythonTests) {
    Invoke-Step "Run Python tests" {
        Invoke-Python @("-m", "pytest")
    }
}

Invoke-Step "Build and validate anki_study_report.ankiaddon" {
    Invoke-Python -Arguments @((Join-Path $Root "scripts\package_addon.py"), "--output", $Archive, "--check")
}

Invoke-Step "Verify final archive" {
    Invoke-Python -Arguments @((Join-Path $Root "scripts\package_addon.py"), "--output", $Archive, "--check-only")
}

Write-Host ""
Write-Host "Built and verified: $Archive" -ForegroundColor Green
