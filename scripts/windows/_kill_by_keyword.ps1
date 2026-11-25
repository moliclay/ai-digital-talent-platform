# Fallback cleanup: kill node/python processes whose command line matches a keyword.
# Called by the stop script. ASCII only -- PowerShell 5 reads .ps1 as ANSI.
param([Parameter(Mandatory=$true)][string]$Keyword)

$PathFilter = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))

$targets = Get-CimInstance Win32_Process -Filter "Name='node.exe' OR Name='python.exe'" |
    Where-Object {
        $_.CommandLine -and
        $_.CommandLine -like "*$Keyword*" -and
        $_.CommandLine.IndexOf($PathFilter, [StringComparison]::OrdinalIgnoreCase) -ge 0
    }

if (-not $targets) {
    Write-Output "  no leftover process matching $Keyword"
    exit 0
}

foreach ($p in $targets) {
    Write-Output "  killing PID=$($p.ProcessId) (match: $Keyword)"
    try {
        Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop
    } catch {
        Write-Output "  [warn] cannot kill PID=$($p.ProcessId)"
    }
}
