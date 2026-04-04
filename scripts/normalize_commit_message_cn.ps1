param(
    [Parameter(Mandatory = $true)]
    [string]$CommitMsgFile
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function U {
    param([int[]]$Codes)
    return (-join ($Codes | ForEach-Object { [char]$_ }))
}

$CN_ADD = U @(0x65B0,0x589E)
$CN_CREATE = U @(0x521B,0x5EFA)
$CN_UPDATE = U @(0x66F4,0x65B0)
$CN_FIX = U @(0x4FEE,0x590D)
$CN_DELETE = U @(0x5220,0x9664)
$CN_RENAME = U @(0x91CD,0x547D,0x540D)
$CN_REFACTOR = U @(0x91CD,0x6784)
$CN_OPTIMIZE = U @(0x4F18,0x5316)
$CN_TEST = U @(0x6D4B,0x8BD5)
$CN_DOC = U @(0x6587,0x6863)
$CN_SCRIPT = U @(0x811A,0x672C)
$CN_HOOK = U @(0x94A9,0x5B50)
$CN_CACHE = U @(0x7F13,0x5B58)
$CN_IGNORE = U @(0x5FFD,0x7565)
$CN_MERGE = U @(0x5408,0x5E76)
$CN_SUPP = U @(0x8865,0x5145,0x8BF4,0x660E)
$CN_NOT_FOUND = U @(0x672A,0x627E,0x5230,0x63D0,0x4EA4,0x5907,0x6CE8,0x6587,0x4EF6)
$CN_DONE = U @(0x5DF2,0x81EA,0x52A8,0x4E2D,0x6587,0x5316,0x63D0,0x4EA4,0x5907,0x6CE8)

if (-not (Test-Path $CommitMsgFile)) {
    throw "${CN_NOT_FOUND}: $CommitMsgFile"
}

function Test-ContainsChinese {
    param([string]$Text)
    if (-not $Text) { return $false }
    return [regex]::IsMatch($Text, '[\u4e00-\u9fff]')
}

function Convert-DescToChinese {
    param([string]$Desc)

    $result = $Desc
    $rules = @(
        @{ Pattern = '(?i)\badd(ed|s|ing)?\b'; Replace = $CN_ADD },
        @{ Pattern = '(?i)\bcreate(d|s|ing)?\b'; Replace = $CN_CREATE },
        @{ Pattern = '(?i)\bupdate(d|s|ing)?\b'; Replace = $CN_UPDATE },
        @{ Pattern = '(?i)\bfix(ed|es|ing)?\b'; Replace = $CN_FIX },
        @{ Pattern = '(?i)\bremove(d|s|ing)?\b'; Replace = $CN_DELETE },
        @{ Pattern = '(?i)\bdelete(d|s|ing)?\b'; Replace = $CN_DELETE },
        @{ Pattern = '(?i)\brename(d|s|ing)?\b'; Replace = $CN_RENAME },
        @{ Pattern = '(?i)\brefactor(ed|s|ing)?\b'; Replace = $CN_REFACTOR },
        @{ Pattern = '(?i)\boptimi[sz](e|ed|es|ing|ation)?\b'; Replace = $CN_OPTIMIZE },
        @{ Pattern = '(?i)\btest(s|ed|ing)?\b'; Replace = $CN_TEST },
        @{ Pattern = '(?i)\bdoc(s|ument|uments)?\b'; Replace = $CN_DOC },
        @{ Pattern = '(?i)\breadme\b'; Replace = 'README' },
        @{ Pattern = '(?i)\bscript(s)?\b'; Replace = $CN_SCRIPT },
        @{ Pattern = '(?i)\bhook(s)?\b'; Replace = $CN_HOOK },
        @{ Pattern = '(?i)\bcache\b'; Replace = $CN_CACHE },
        @{ Pattern = '(?i)\bignore(d|s|ing)?\b'; Replace = $CN_IGNORE },
        @{ Pattern = '(?i)\bmerge(d|s|ing)?\b'; Replace = $CN_MERGE }
    )

    foreach ($rule in $rules) {
        $result = [regex]::Replace($result, $rule.Pattern, $rule.Replace)
    }

    $result = $result -replace '[_\-]+', ' '
    $result = $result -replace '\s+', ' '
    return $result.Trim()
}

$raw = Get-Content -Raw $CommitMsgFile
$lines = $raw -split "`r?`n", -1

$subjectIndex = -1
for ($i = 0; $i -lt $lines.Count; $i++) {
    $line = $lines[$i]
    if ($line -and $line.Trim() -ne '' -and -not $line.TrimStart().StartsWith('#')) {
        $subjectIndex = $i
        break
    }
}

if ($subjectIndex -lt 0) {
    exit 0
}

$subject = $lines[$subjectIndex].Trim()
if ($subject -match '^(Merge|Revert)\b') {
    exit 0
}

$newSubject = $subject
if ($subject -match '^(?<prefix>[A-Za-z]+(\([^)]+\))?!?):\s*(?<desc>.+)$') {
    $prefix = $Matches['prefix']
    $desc = $Matches['desc']
    if (-not (Test-ContainsChinese $desc)) {
        $descCn = Convert-DescToChinese $desc
        if (-not (Test-ContainsChinese $descCn)) {
            $descCn = "$CN_SUPP $descCn"
        }
        $newSubject = "${prefix}: $descCn"
    }
} elseif (-not (Test-ContainsChinese $subject)) {
    $subjectCn = Convert-DescToChinese $subject
    if (-not (Test-ContainsChinese $subjectCn)) {
        $subjectCn = "$CN_SUPP $subjectCn"
    }
    $newSubject = $subjectCn
}

if ($newSubject -ne $subject) {
    $lines[$subjectIndex] = $newSubject
    Set-Content -Path $CommitMsgFile -Value ($lines -join "`r`n") -Encoding UTF8
    Write-Host ("${CN_DONE}: $newSubject")
}

exit 0
