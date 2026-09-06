# Label Previewer installer (Windows)
#
# Copies the app to a stable per-user folder, makes sure Pillow is
# installed, and creates Desktop + Start Menu shortcuts with the app icon.
# Safe to re-run any time (it just overwrites the previous install).
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File install.ps1

$ErrorActionPreference = "Stop"

$sourceDir = $PSScriptRoot
$installDir = Join-Path $env:LOCALAPPDATA "LabelPreviewer"

Write-Host "Installing Label Previewer to $installDir ..."
New-Item -ItemType Directory -Force -Path $installDir | Out-Null

foreach ($file in @("label_previewer.py", "Label Previewer.pyw", "icon.ico", "icon.png")) {
    Copy-Item -Path (Join-Path $sourceDir $file) -Destination $installDir -Force
}

# Make sure Pillow is available for whichever Python will run the app.
$python = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
if ($python) {
    Write-Host "Checking for Pillow..."
    & $python -m pip show pillow *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Installing Pillow..."
        & $python -m pip install --quiet pillow
    }
} else {
    Write-Warning "Python was not found on PATH. Install Python 3 (with tkinter) before running the app."
}

$pythonw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $pythonw -and $python) {
    $pythonw = $python -replace "python\.exe$", "pythonw.exe"
}

function New-AppShortcut([string]$folder, [string]$name) {
    # Build at an ASCII-safe temp path first, then move it in: the legacy
    # WScript.Shell shortcut COM API can fail to Save() directly to a path
    # containing non-ASCII characters (e.g. a localized OneDrive Desktop
    # folder name), but a plain file move handles Unicode paths fine.
    $tempLnk = Join-Path $env:TEMP $name
    $finalLnk = Join-Path $folder $name

    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($tempLnk)
    $shortcut.TargetPath = $pythonw
    $shortcut.Arguments = "`"$installDir\Label Previewer.pyw`""
    $shortcut.WorkingDirectory = $installDir
    $shortcut.IconLocation = Join-Path $installDir "icon.ico"
    $shortcut.Description = "Preview and sort labelled image/annotation pairs"
    $shortcut.Save()

    New-Item -ItemType Directory -Force -Path $folder | Out-Null
    Move-Item -LiteralPath $tempLnk -Destination $finalLnk -Force
    Write-Host "Created shortcut: $finalLnk"
}

if ($pythonw) {
    $desktop = [Environment]::GetFolderPath("Desktop")
    $startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
    New-AppShortcut -folder $desktop -name "Label Previewer.lnk"
    New-AppShortcut -folder $startMenu -name "Label Previewer.lnk"
} else {
    Write-Warning "pythonw.exe not found - skipping shortcut creation."
}

Write-Host "Done. Launch it from the Desktop or Start Menu."
