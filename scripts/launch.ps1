# Opens the PLAN viewer + 4 reels-squad child panes next to the manager pane, in the SAME terminal.
# Layout: manager left | right column: PLAN on top, then 2x2 researcher, prompt / coder, styler.
# Orca (ORCA_TERMINAL_HANDLE set): splits the manager's own pane via `orca terminal split`.
# Windows Terminal (WT_SESSION set): `wt -w 0 split-pane` in the current window. Never opens a new window.
#   powershell -ExecutionPolicy Bypass -File launch.ps1 -Manager <manager session name> [-Dir <workspace>] [-Only coder] [-DryRun]
# ASCII only: Windows PowerShell 5.1 misreads UTF-8 without BOM.
param(
    [Parameter(Mandatory)][string]$Manager,
    [string]$Dir = 'E:\aff\reels',
    [ValidateSet('plan', 'researcher', 'prompt', 'coder', 'styler')][string[]]$Only = @(),
    [string]$PermissionMode = '',
    [string]$SquadId = '',
    [switch]$DryRun
)

New-Item -ItemType Directory -Force -Path $Dir | Out-Null
$Dir = (Resolve-Path -LiteralPath $Dir).Path
$planFile = Join-Path $Dir 'PLAN.md'
if (-not (Test-Path -LiteralPath $planFile)) {
    Set-Content -LiteralPath $planFile -Encoding UTF8 -Value "# Reels Squad`n`nChua co kenh nao. Hay chat voi manager: dua link kenh Instagram."
}

# Forward slashes survive cmd, PowerShell and git-bash alike.
$scripts = $PSScriptRoot -replace '\\', '/'
$dirArg = $Dir -replace '\\', '/'

# Pixel Office (optional desktop pet): one squad id per full launch; -Only reuses the manager's latest one.
# Never blocks or breaks the launch.
try {
    $poHome = if ($env:PIXEL_OFFICE_HOME) { $env:PIXEL_OFFICE_HOME } else { 'E:\aff\pixel-office' }
    $poSquads = Join-Path $env:LOCALAPPDATA 'PixelOffice\squads'
    $replace = $Only.Count -eq 0
    if (-not $SquadId -and -not $replace -and (Test-Path -LiteralPath $poSquads)) {
        $latest = Get-ChildItem -LiteralPath $poSquads -Filter '*.json' | Sort-Object LastWriteTime -Descending |
            ForEach-Object { Get-Content -Raw -LiteralPath $_.FullName | ConvertFrom-Json } |
            Where-Object { $_.managerName -eq $Manager } | Select-Object -First 1
        if ($latest) { $SquadId = $latest.squad }
    }
    $isNew = -not $SquadId
    if ($isNew) { $SquadId = 'sq-' + (Get-Date -Format 'yyyyMMddHHmmss') }
    if (-not $DryRun -and (Test-Path -LiteralPath (Join-Path $poHome 'hook\notify.js'))) {
        if ($isNew) {
            New-Item -ItemType Directory -Force -Path $poSquads | Out-Null
            $json = @{ squad = $SquadId; managerName = $Manager; managerSession = $null; createdAt = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() } | ConvertTo-Json -Compress
            [IO.File]::WriteAllText((Join-Path $poSquads "$SquadId.json"), $json)
        }
        $notifyArgs = @("`"$poHome\hook\notify.js`"", 'squad-start', '--squad', $SquadId, '--manager', $Manager)
        if ($replace) { $notifyArgs += '--replace' }
        Start-Process -WindowStyle Hidden -FilePath 'node' -ArgumentList $notifyArgs | Out-Null
    }
} catch {
    Write-Host "Pixel Office: skipped ($($_.Exception.Message))"
}

function PaneCmd([string]$role) {
    if ($role -eq 'plan') {
        return "powershell -NoProfile -ExecutionPolicy Bypass -File `"$scripts/plan-view.ps1`" -File `"$dirArg/PLAN.md`""
    }
    $cmd = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$scripts/child.ps1`" -Role $role -Dir `"$dirArg`" -Manager $Manager"
    if ($PermissionMode) { $cmd += " -PermissionMode $PermissionMode" }
    if ($SquadId) { $cmd += " -SquadId $SquadId" }
    return $cmd
}

if ($env:ORCA_TERMINAL_HANDLE) {
    function Get-PaneHandles {
        $list = orca terminal list --json | Out-String | ConvertFrom-Json
        return @($list.result.terminals | ForEach-Object { $_.handle })
    }
    # Orca: "horizontal" = side by side, "vertical" = stacked.
    function Split([string]$from, [string]$dir, [string]$role) {
        if ($DryRun) { Write-Host "orca terminal split --terminal $from --direction $dir --command '$(PaneCmd $role)'"; return "<$role>" }
        # Orca can report "Timed out waiting for split pane handle" yet still create the pane.
        # Never blindly retry (that spawns duplicate sessions): look for the new pane first.
        $before = Get-PaneHandles
        $handle = $null
        for ($try = 1; $try -le 2 -and -not $handle; $try++) {
            $out = orca terminal split --terminal $from --direction $dir --command (PaneCmd $role) --json | Out-String | ConvertFrom-Json
            if ($out.ok) { $handle = $out.result.split.handle; break }
            Start-Sleep -Seconds 4
            $new = @(Get-PaneHandles | Where-Object { $before -notcontains $_ })
            if ($new.Count -ge 1) { $handle = $new[0] }
        }
        if (-not $handle) { Write-Host "Split for $role failed: $($out | ConvertTo-Json -Depth 5)"; exit 1 }
        orca terminal rename --terminal $handle --title "reels-$role" | Out-Null
        Write-Host "reels-$role -> $handle"
        # Spawn one by one so each Claude session starts cleanly.
        Start-Sleep -Seconds 2
        return $handle
    }
    $mgrPane = $env:ORCA_TERMINAL_HANDLE
    $panes = [ordered]@{}
    if ($Only.Count -gt 0) {
        foreach ($r in $Only) { $panes[$r] = Split $mgrPane 'vertical' $r }
    } else {
        $panes['plan'] = Split $mgrPane 'horizontal' 'plan'
        $panes['researcher'] = Split $panes['plan'] 'vertical' 'researcher'
        $panes['coder'] = Split $panes['researcher'] 'vertical' 'coder'
        $panes['prompt'] = Split $panes['researcher'] 'horizontal' 'prompt'
        $panes['styler'] = Split $panes['coder'] 'horizontal' 'styler'
    }
    if ($DryRun) { exit 0 }
    # --command is sometimes dropped when splits come in fast: retype it into any pane still at a bare shell.
    Start-Sleep -Seconds 8
    foreach ($r in $panes.Keys) {
        $seen = orca terminal read --terminal $panes[$r] | Out-String
        if ($seen -notmatch 'child\.ps1|plan-view|reels-|Reels Squad') {
            orca terminal send --terminal $panes[$r] --text (PaneCmd $r) --enter | Out-Null
            Write-Host "reels-${r}: startup command resent"
        }
    }
    Write-Host 'Reels panes launched in Orca. Run ListAgents in ~20s to confirm reels-researcher/prompt/coder/styler.'
    exit 0
}

if (-not $env:WT_SESSION) {
    Write-Host 'Not inside Orca or Windows Terminal: refusing to open a new window. Run Claude inside Orca or Windows Terminal.'
    exit 1
}

function PaneArgs([string]$role) { return "--title reels-$role -d `"$Dir`" $(PaneCmd $role)" }

if ($Only.Count -gt 0) {
    $parts = $Only | ForEach-Object { "split-pane -H $(PaneArgs $_)" }
} else {
    $parts = @(
        "split-pane -V -s 0.55 $(PaneArgs 'plan')",
        "split-pane -H -s 0.75 $(PaneArgs 'researcher')",
        "split-pane -H -s 0.5 $(PaneArgs 'coder')",
        "move-focus up",
        "split-pane -V -s 0.5 $(PaneArgs 'prompt')",
        "move-focus down",
        "split-pane -V -s 0.5 $(PaneArgs 'styler')"
    )
}
$argLine = '-w 0 ' + ($parts -join ' ; ')
if ($DryRun) { Write-Host "wt $argLine"; exit 0 }
Start-Process wt -ArgumentList $argLine
Write-Host 'Reels panes launched in the current Windows Terminal window. Run ListAgents in ~20s to confirm.'
