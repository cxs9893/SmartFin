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
    $errors += "缺少 docs/development-flow.md"
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
        $errors += "检测到 src/finqa/$module/ 有改动，但缺少对应文档改动: $docRel"
    }

    if ($flowContent -and -not $flowContent.Contains($docRelNorm)) {
        $errors += "docs/development-flow.md 缺少模块链接: $docRel"
    }
}

if ($errors.Count -gt 0) {
    Write-Host "迭代文档校验失败：" -ForegroundColor Red
    foreach ($e in $errors) {
        Write-Host " - $e" -ForegroundColor Red
    }
    exit 1
}

Write-Host "迭代文档校验通过。" -ForegroundColor Green
exit 0
