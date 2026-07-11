param(
    [ValidateSet("success", "failure", "cancelled", "skipped", "unknown")]
    [string]$Result = "unknown",
    [ValidateSet("none", "test", "build", "package", "environment", "unknown")]
    [string]$FailureCategory = "unknown",
    [string]$StartedAt = "",
    [string]$OutputDirectory = "ci-fast",
    [string]$Command = ".\scripts\run_full_check.ps1 -SkipDocker"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$OutputPath = Join-Path $Root $OutputDirectory

function Get-SafeCommandVersion {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )

    try {
        $output = & $FilePath @Arguments 2>&1
        if ($LASTEXITCODE -ne 0 -or -not $output) {
            return "unavailable"
        }
        return (($output | Select-Object -First 1).ToString()).Trim()
    } catch {
        return "unavailable"
    }
}

function Get-GitValue {
    param([string[]]$Arguments)

    try {
        $value = & git @Arguments 2>$null
        if ($LASTEXITCODE -eq 0 -and $value) {
            return (($value | Select-Object -First 1).ToString()).Trim()
        }
    } catch {
    }
    return "unknown"
}

New-Item -ItemType Directory -Force -Path $OutputPath | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $OutputPath "logs") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $OutputPath "package") | Out-Null

$pythonVersion = Get-SafeCommandVersion -FilePath "python" -Arguments @("--version")
$nodeVersion = Get-SafeCommandVersion -FilePath "node" -Arguments @("--version")
$pnpmVersion = Get-SafeCommandVersion -FilePath "pnpm" -Arguments @("--version")
$commitSha = if ($env:GITHUB_SHA) { $env:GITHUB_SHA } else { Get-GitValue @("rev-parse", "HEAD") }
$ref = if ($env:GITHUB_REF) { $env:GITHUB_REF } else { Get-GitValue @("branch", "--show-current") }
$repository = if ($env:GITHUB_REPOSITORY) { $env:GITHUB_REPOSITORY } else { "AliceLiddell01/anki-study-report" }
$event = if ($env:GITHUB_EVENT_NAME) { $env:GITHUB_EVENT_NAME } else { "local" }
$workflow = if ($env:GITHUB_WORKFLOW) { $env:GITHUB_WORKFLOW } else { "Fast CI" }
$runId = if ($env:GITHUB_RUN_ID) { $env:GITHUB_RUN_ID } else { "local" }
$runAttempt = if ($env:GITHUB_RUN_ATTEMPT) { $env:GITHUB_RUN_ATTEMPT } else { "1" }
$runnerOs = if ($env:RUNNER_OS) { $env:RUNNER_OS } else { [System.Environment]::OSVersion.Platform.ToString() }
$started = if ($StartedAt) { $StartedAt } else { [DateTime]::UtcNow.ToString("o") }
$finished = [DateTime]::UtcNow.ToString("o")

$environmentLines = @(
    "repository=$repository"
    "commitSha=$commitSha"
    "ref=$ref"
    "event=$event"
    "workflow=$workflow"
    "runId=$runId"
    "runAttempt=$runAttempt"
    "runnerOs=$runnerOs"
    "pythonVersion=$pythonVersion"
    "nodeVersion=$nodeVersion"
    "pnpmVersion=$pnpmVersion"
)
$environmentLines | Set-Content -LiteralPath (Join-Path $OutputPath "environment.txt") -Encoding utf8

$artifactFiles = @(
    Get-ChildItem -LiteralPath $OutputPath -Recurse -File |
        ForEach-Object { $_.FullName.Substring($OutputPath.Length + 1).Replace("\", "/") }
)
$artifactFiles += @("ci-summary.md", "ci-summary.json")
$artifactFiles = @($artifactFiles | Sort-Object -Unique)

$summary = [ordered]@{
    schemaVersion = 1
    repository = $repository
    commitSha = $commitSha
    ref = $ref
    event = $event
    workflow = $workflow
    runId = $runId
    runAttempt = $runAttempt
    runnerOs = $runnerOs
    pythonVersion = $pythonVersion
    nodeVersion = $nodeVersion
    pnpmVersion = $pnpmVersion
    command = $Command
    result = $Result
    startedAt = $started
    finishedAt = $finished
    checks = @(
        [ordered]@{
            name = "canonical-fast-pipeline"
            command = $Command
            result = $Result
        }
    )
    artifactFiles = $artifactFiles
    failureCategory = if ($Result -eq "success") { "none" } else { $FailureCategory }
}
$summary | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $OutputPath "ci-summary.json") -Encoding utf8

$markdown = @"
# Fast CI summary

| Field | Value |
| --- | --- |
| Result | $($summary.result) |
| Failure category | $($summary.failureCategory) |
| Repository | $repository |
| Commit | ``$commitSha`` |
| Ref | ``$ref`` |
| Event | $event |
| Runner OS | $runnerOs |
| Python | $pythonVersion |
| Node.js | $nodeVersion |
| pnpm | $pnpmVersion |
| Command | ``$Command`` |
| Started (UTC) | $started |
| Finished (UTC) | $finished |

The package under ``package/`` is a non-release CI build artifact.
"@
$markdown | Set-Content -LiteralPath (Join-Path $OutputPath "ci-summary.md") -Encoding utf8

if ($env:GITHUB_STEP_SUMMARY) {
    $markdown | Add-Content -LiteralPath $env:GITHUB_STEP_SUMMARY -Encoding utf8
}
