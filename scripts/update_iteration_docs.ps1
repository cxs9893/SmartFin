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
    throw "Template not found: $templatePath"
}

if (-not (Test-Path $flowPath)) {
    throw "Flow doc not found: $flowPath"
}

if (-not (Test-Path $iterationDocPath)) {
    $template = Get-Content -Raw $templatePath
    $rendered = $template.Replace("{{MODULE}}", $Module)
    Set-Content -Path $iterationDocPath -Value $rendered -Encoding UTF8
    Write-Host "Created: docs/$Module-iteration.md"
} else {
    Write-Host "Exists: docs/$Module-iteration.md"
}

$startMarker = "<!-- ITERATION_DOCS_INDEX_START -->"
$endMarker = "<!-- ITERATION_DOCS_INDEX_END -->"

$flow = Get-Content -Raw $flowPath

if (-not $flow.Contains($startMarker) -or -not $flow.Contains($endMarker)) {
    $insertion = @"
## Iteration Document Index
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
    $lines += "- (none)"
}

$replacement = $startMarker + "`r`n" + ($lines -join "`r`n") + "`r`n" + $endMarker
$pattern = [regex]::Escape($startMarker) + "[\s\S]*?" + [regex]::Escape($endMarker)
$updated = [regex]::Replace($flow, $pattern, $replacement)

Set-Content -Path $flowPath -Value $updated -Encoding UTF8
Write-Host "Updated index in docs/development-flow.md"
