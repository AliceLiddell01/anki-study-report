param(
    [switch]$BuildOnly,
    [switch]$NoBuild,
    [string]$ArtifactsDir = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ComposeFile = Join-Path $Root "docker\anki-e2e\docker-compose.yml"

if (-not (Test-Path $ComposeFile)) {
    throw "Docker compose file not found: $ComposeFile"
}

if (-not $ArtifactsDir) {
    $ArtifactsDir = Join-Path $Root "e2e-artifacts"
}

New-Item -ItemType Directory -Force -Path $ArtifactsDir | Out-Null

function Invoke-DockerCompose {
    param([string[]]$Arguments)

    & docker compose -f $ComposeFile @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose failed: $($Arguments -join ' ')"
    }
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
    Invoke-DockerCompose @("run", "--rm", "-v", $volume, "anki-e2e")
} finally {
    Pop-Location
}
