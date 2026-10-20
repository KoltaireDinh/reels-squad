# Live viewer for PLAN.md: redraws whenever the file changes. Not a Claude session.
# ASCII only: Windows PowerShell 5.1 misreads UTF-8 without BOM.
param([Parameter(Mandatory)][string]$File)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$host.UI.RawUI.WindowTitle = 'reels-plan'
$last = $null
while ($true) {
    $stamp = if (Test-Path -LiteralPath $File) { (Get-Item -LiteralPath $File).LastWriteTimeUtc } else { $null }
    if ($stamp -ne $last) {
        $last = $stamp
        Clear-Host
        Write-Host "=== PLAN  ($File)  refreshed $(Get-Date -Format HH:mm:ss) ===" -ForegroundColor Cyan
        if ($stamp) {
            foreach ($line in (Get-Content -LiteralPath $File -Encoding UTF8)) {
                if ($line -match '^#') { Write-Host $line -ForegroundColor Yellow }
                elseif ($line -match '^\s*[-*] ') { Write-Host $line -ForegroundColor Gray }
                else { Write-Host $line }
            }
        } else {
            Write-Host '(PLAN.md chua co)'
        }
    }
    Start-Sleep -Milliseconds 1500
}
