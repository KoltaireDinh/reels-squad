# Starts one reels-squad child pane: a named Claude session primed with its role brief.
# Default permission: bypass everything (bypassPermissions), regardless of settings.json defaultMode.
# ASCII only: Windows PowerShell 5.1 misreads UTF-8 without BOM.
param(
    [Parameter(Mandatory)][ValidateSet('researcher', 'prompt', 'coder', 'styler')][string]$Role,
    [Parameter(Mandatory)][string]$Dir,
    [Parameter(Mandatory)][string]$Manager,
    [string]$PermissionMode = '',
    [string]$SquadId = ''
)

# Pixel Office: the hook reads these to know which house and which character this session is.
if ($SquadId) { $env:PIXEL_OFFICE_SQUAD = $SquadId; $env:PIXEL_OFFICE_ROLE = $Role }

$roleFile = Join-Path (Split-Path -Parent $PSScriptRoot) "roles\$Role.md"

Set-Location -LiteralPath $Dir
$host.UI.RawUI.WindowTitle = "reels-$Role"

# Manager name goes in the prompt so the child can SendMessage back without guessing.
$prompt = "Read the role brief at $roleFile and take on that role for this whole session. Workspace: $Dir. The manager session name is: $Manager"
# Explicit --permission-mode: a "defaultMode" in settings.json otherwise wins over --dangerously-skip-permissions,
# and a mode mismatch with the manager makes every SendMessage wait for manual approval.
$mode = if ($PermissionMode) { $PermissionMode } else { 'bypassPermissions' }
$perm = @('--permission-mode', $mode)
if ($mode -eq 'bypassPermissions') { $perm += '--dangerously-skip-permissions' }

& claude -n "reels-$Role" @perm $prompt
