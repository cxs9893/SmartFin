param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-z][a-z0-9_-]*$')]
    [string]$Module
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$docsDir = Join-Path $repoRoot "docs"
$templatePath = Join-Path $docsDir "templates/iteration-template.md"
$iterationDocPath = Join-Path $docsDir "$Module-iteration.md"
$flowPath = Join-Path $docsDir "development-flow.md"

if (-not (Test-Path $templatePath)) {
    throw "未找到模板文件: $templatePath"
}

if (-not (Test-Path $flowPath)) {
    throw "未找到流程文档: $flowPath"
}

if (-not (Test-Path $iterationDocPath)) {
    $template = Get-Content -Raw $templatePath
    $rendered = $template.Replace("{{MODULE}}", $Module)
    Set-Content -Path $iterationDocPath -Value $rendered -Encoding UTF8
    Write-Host "已创建: docs/$Module-iteration.md"
} else {
    Write-Host "已存在: docs/$Module-iteration.md"
}

$startMarker = "<!-- ITERATION_DOCS_INDEX_START -->"
$endMarker = "<!-- ITERATION_DOCS_INDEX_END -->"

$flow = Get-Content -Raw $flowPath

if (-not $flow.Contains($startMarker) -or -not $flow.Contains($endMarker)) {
    $insertion = @"
## 迭代文档索引
$startMarker
$endMarker
"@
    $flow = $flow -replace "(##\s+总体流程图)", "$insertion`r`n`r`n`$1"
}

$allIterationDocs = Get-ChildItem -Path $docsDir -File -Filter "*-iteration.md" |
    Where-Object { $_.Name -ne "iteration-template.md" } |
    Sort-Object Name

$lines = @()
foreach ($doc in $allIterationDocs) {
    $name = [System.IO.Path]::GetFileNameWithoutExtension($doc.Name)
    $label = $name -replace '-iteration$',''
    $lines += "- ${label}: docs/$($doc.Name)"
}

if ($lines.Count -eq 0) {
    $lines += "- （暂无）"
}

$replacement = $startMarker + "`r`n" + ($lines -join "`r`n") + "`r`n" + $endMarker
$pattern = [regex]::Escape($startMarker) + "[\s\S]*?" + [regex]::Escape($endMarker)
$updated = [regex]::Replace($flow, $pattern, $replacement)

Set-Content -Path $flowPath -Value $updated -Encoding UTF8
Write-Host "已更新索引: docs/development-flow.md"
