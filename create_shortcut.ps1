# Creates a "Label Previewer" shortcut on your Desktop that launches the
# app windowless (via pythonw.exe) with the custom icon.
#
# Run it once:
#   powershell -ExecutionPolicy Bypass -File create_shortcut.ps1

$ErrorActionPreference = "Stop"

$appDir = $PSScriptRoot
$target = Join-Path $appDir "Label Previewer.pyw"
$icon = Join-Path $appDir "icon.ico"
$pythonw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $pythonw) {
    $pythonw = (Get-Command python.exe).Source -replace "python\.exe$", "pythonw.exe"
}

$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "Label Previewer.lnk"

# Build the shortcut at an ASCII path first: the classic WScript.Shell
# shortcut COM API can fail to save directly to a path containing non-ASCII
# characters (e.g. a OneDrive Desktop folder localized to another
# language), so we save locally then move it with a Unicode-safe API.
$tempLnk = Join-Path $appDir "Label Previewer.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($tempLnk)
$shortcut.TargetPath = $pythonw
$shortcut.Arguments = "`"$target`""
$shortcut.WorkingDirectory = $appDir
$shortcut.IconLocation = $icon
$shortcut.Description = "Preview and sort labelled image/annotation pairs"
$shortcut.Save()

Move-Item -LiteralPath $tempLnk -Destination $shortcutPath -Force
Write-Host "Created shortcut: $shortcutPath"
