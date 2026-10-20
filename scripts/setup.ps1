# One-time setup of the reels workspace: python tools, ffmpeg, Playwright + Chromium, three.js.
#   powershell -ExecutionPolicy Bypass -File setup.ps1 [-Dir E:\aff\reels]
# ASCII only: Windows PowerShell 5.1 misreads UTF-8 without BOM.
param([string]$Dir = 'E:\aff\reels')

$ErrorActionPreference = 'Stop'
$tools = Join-Path $Dir 'tools'
New-Item -ItemType Directory -Force -Path $tools, (Join-Path $tools 'bin'), (Join-Path $tools 'vendor'), (Join-Path $Dir 'channels'), (Join-Path $Dir 'secrets') | Out-Null

# Tool sources live in the skill; copy them so node resolves tools/node_modules.
foreach ($f in 'render.mjs', 'extract.py', 'ig_fetch.py', 'ig_collect.js', 'ig_watch.js') {
    Copy-Item -Force (Join-Path $PSScriptRoot $f) (Join-Path $tools $f)
}
$master = Join-Path $Dir 'MASTER_PROMPT.md'
if (-not (Test-Path -LiteralPath $master)) {
    Copy-Item (Join-Path (Split-Path -Parent $PSScriptRoot) 'templates\MASTER_PROMPT.md') $master
}

Write-Host '[setup] python packages'
python -m pip install --quiet --upgrade yt-dlp gallery-dl imageio-ffmpeg faster-whisper edge-tts
if ($LASTEXITCODE -ne 0) { throw 'pip install failed' }

Write-Host '[setup] ffmpeg'
$ffmpeg = Join-Path $tools 'bin\ffmpeg.exe'
if (-not (Test-Path -LiteralPath $ffmpeg)) {
    $src = python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"
    Copy-Item -Force $src.Trim() $ffmpeg
}

Write-Host '[setup] node: playwright + three'
Push-Location $tools
try {
    if (-not (Test-Path 'package.json')) {
        Set-Content -Encoding ASCII -Path 'package.json' -Value '{ "name": "reels-tools", "private": true, "type": "module" }'
    }
    npm install --silent --no-fund --no-audit playwright three gsap
    if ($LASTEXITCODE -ne 0) { throw 'npm install failed' }
    npx playwright install chromium
    if ($LASTEXITCODE -ne 0) { throw 'playwright install failed' }
    # Builds load libraries from tools/vendor via relative path, so renders work offline.
    Copy-Item -Force 'node_modules\three\build\three.module.js' 'vendor\three.module.js'
    Copy-Item -Force 'node_modules\three\build\three.core.js' 'vendor\three.core.js' -ErrorAction SilentlyContinue
    Copy-Item -Force 'node_modules\gsap\dist\gsap.min.js' 'vendor\gsap.min.js'
} finally {
    Pop-Location
}

Write-Host "[setup] done. ffmpeg=$ffmpeg"
