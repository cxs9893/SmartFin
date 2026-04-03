param(
    [int]$MaxCount = 50,
    [string]$Since,
    [string]$OutputPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

$sep = [char]31
$pretty = "%H%x1f%h%x1f%an%x1f%ad%x1f%s"
$gitArgs = @("log", "--date=iso-strict")

if ($MaxCount -gt 0) {
    $gitArgs += @("-n", "$MaxCount")
}
if ($Since -and $Since.Trim() -ne "") {
    $gitArgs += "--since=$Since"
}

$gitArgs += "--pretty=format:$pretty"

$raw = & git @gitArgs
if ($LASTEXITCODE -ne 0) {
    throw "读取 Git 提交历史失败，请确认当前目录是 Git 仓库。"
}

if (-not $raw -or $raw.Trim() -eq "") {
    Write-Host "未查询到提交记录。"
    exit 0
}

$lines = $raw -split "`r?`n" | Where-Object { $_ -and $_.Trim() -ne "" }
$records = @()

foreach ($line in $lines) {
    $parts = $line -split $sep
    if ($parts.Count -lt 5) {
        continue
    }

    $records += [PSCustomObject]@{
        FullHash  = $parts[0]
        ShortHash = $parts[1]
        Author    = $parts[2]
        Date      = $parts[3]
        Subject   = $parts[4]
    }
}

Write-Host ("提交记录（共 {0} 条）：" -f $records.Count) -ForegroundColor Cyan
$i = 1
foreach ($r in $records) {
    Write-Host ("[{0}] 提交: {1}" -f $i, $r.ShortHash)
    Write-Host ("    作者: {0}" -f $r.Author)
    Write-Host ("    时间: {0}" -f $r.Date)
    Write-Host ("    备注: {0}" -f $r.Subject)
    $i++
}

if ($OutputPath -and $OutputPath.Trim() -ne "") {
    $targetPath = $OutputPath
    if (-not [System.IO.Path]::IsPathRooted($targetPath)) {
        $targetPath = Join-Path $repoRoot $targetPath
    }

    $dir = Split-Path -Parent $targetPath
    if ($dir -and -not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
    }

    $md = @("# 提交备注清单", "", ("生成时间：{0}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss")), "")
    foreach ($r in $records) {
        $md += ("## {0} - {1}" -f $r.ShortHash, $r.Subject)
        $md += ('- 完整哈希：`{0}`' -f $r.FullHash)
        $md += ("- 作者：{0}" -f $r.Author)
        $md += ("- 时间：{0}" -f $r.Date)
        $md += ""
    }

    Set-Content -Path $targetPath -Value ($md -join "`r`n") -Encoding UTF8
    Write-Host ("已写入文件：{0}" -f $targetPath) -ForegroundColor Green
}

exit 0
