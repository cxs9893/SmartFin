Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

function Get-ChangedPaths {
    $tracked = @()
    $untracked = @()

    $trackedRaw = git diff --name-only HEAD
    if ($trackedRaw) {
        $tracked = $trackedRaw -split "`r?`n" | Where-Object { $_ -and $_.Trim() -ne "" }
    }

    $untrackedRaw = git ls-files --others --exclude-standard
    if ($untrackedRaw) {
        $untracked = $untrackedRaw -split "`r?`n" | Where-Object { $_ -and $_.Trim() -ne "" }
    }

    return @($tracked + $untracked | Sort-Object -Unique)
}

$changedPaths = Get-ChangedPaths
$modulePattern = '^src/finqa/([^/\\]+)/'
$touchedModules = New-Object System.Collections.Generic.HashSet[string]

foreach ($path in $changedPaths) {
    $normalized = $path -replace '\\','/'
    $m = [regex]::Match($normalized, $modulePattern)
    if ($m.Success) {
        [void]$touchedModules.Add($m.Groups[1].Value)
    }
}

$errors = @()
$flowPath = Join-Path $repoRoot "docs/development-flow.md"
$flowContent = ""
if (Test-Path $flowPath) {
    $flowContent = Get-Content -Raw $flowPath
} else {
    $errors += "Missing docs/development-flow.md"
}

foreach ($module in $touchedModules) {
    $docRel = "docs/$module-iteration.md"
    $docRelNorm = $docRel -replace '\\','/'

    $docChanged = $false
    foreach ($p in $changedPaths) {
        if (($p -replace '\\','/') -eq $docRelNorm) {
            $docChanged = $true
            break
        }
    }

    if (-not $docChanged) {
        $errors += "Detected src/finqa/$module/ changes but missing docs change: $docRel"
    }

    if ($flowContent -and -not $flowContent.Contains($docRelNorm)) {
        $errors += "Missing module link in docs/development-flow.md: $docRel"
    }
}

if ($errors.Count -gt 0) {
    Write-Host "Iteration docs validation failed:" -ForegroundColor Red
    foreach ($e in $errors) {
        Write-Host " - $e" -ForegroundColor Red
    }
    exit 1
}

Write-Host "Iteration docs validation passed." -ForegroundColor Green
exit 0
