# Label Previewer installer (Windows)
#
# Installs Python if it's missing (via winget), copies the app to a stable
# per-user folder, makes sure Pillow is installed, and creates Desktop +
# Start Menu shortcuts with the app icon. Safe to re-run any time (it just
# overwrites the previous install).
#
# Just double-click install.bat, or run:
#   powershell -ExecutionPolicy Bypass -File install.ps1

$ErrorActionPreference = "Continue"

$sourceDir = $PSScriptRoot
$installDir = Join-Path $env:LOCALAPPDATA "LabelPreviewer"

Write-Host "== Label Previewer installer (Windows) =="
Write-Host ""

$python = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
if (-not $python) {
    Write-Host "Python not found."
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if ($winget) {
        Write-Host "Installing Python via winget (this can take a minute)..."
        winget install -e --id Python.Python.3.12 --source winget --accept-source-agreements --accept-package-agreements
        Write-Host ""
        Write-Host "Python was just installed. Please close this window and run" -ForegroundColor Yellow
        Write-Host "install.bat (or this script) once more so Windows picks up the new PATH." -ForegroundColor Yellow
        exit 0
    } else {
        Write-Warning "winget isn't available either. Install Python 3 from https://www.python.org/downloads/ (check 'Add python.exe to PATH' during setup), then re-run this script."
        exit 1
    }
}

Write-Host "Installing Label Previewer to $installDir ..."
New-Item -ItemType Directory -Force -Path $installDir | Out-Null

foreach ($file in @("label_previewer.py", "Label Previewer.pyw", "icon.ico", "icon.png")) {
    Copy-Item -Path (Join-Path $sourceDir $file) -Destination $installDir -Force
}

# Make sure Tkinter is available (bundled by the official python.org
# installer; some minimal or Microsoft Store builds of Python omit it).
& $python -c "import tkinter" *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Tkinter isn't available for $python. If you installed Python from the Microsoft Store, reinstall it from https://www.python.org/downloads/ instead (its installer bundles Tkinter)."
}

# Make sure Pillow is available for whichever Python will run the app.
Write-Host "Checking for Pillow..."
& $python -m pip show pillow *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing Pillow..."
    & $python -m pip install --quiet pillow
    if ($LASTEXITCODE -ne 0) {
        Write-Host "That failed; retrying with --user --break-system-packages..."
        & $python -m pip install --quiet --user --break-system-packages pillow
    }
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

Write-Host ""
Write-Host "Done! Launch 'Label Previewer' from the Desktop or Start Menu." -ForegroundColor Green
