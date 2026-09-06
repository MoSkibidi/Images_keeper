# Removes what install.ps1 created: the installed copy of the app plus its
# Desktop and Start Menu shortcuts. Your original source folder (and any
# datasets) are untouched.
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File uninstall.ps1

$installDir = Join-Path $env:LOCALAPPDATA "LabelPreviewer"
$desktop = [Environment]::GetFolderPath("Desktop")
$startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"

foreach ($lnk in @((Join-Path $desktop "Label Previewer.lnk"), (Join-Path $startMenu "Label Previewer.lnk"))) {
    if (Test-Path -LiteralPath $lnk) {
        Remove-Item -LiteralPath $lnk -Force
        Write-Host "Removed $lnk"
    }
}

if (Test-Path -LiteralPath $installDir) {
    Remove-Item -LiteralPath $installDir -Recurse -Force
    Write-Host "Removed $installDir"
}

Write-Host "Uninstalled."
