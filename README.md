# Label Previewer

A small desktop app for reviewing thousands of labelled `image + annotation`
pairs one at a time, and sorting the ones you want to keep into a separate
folder.

It shows each image with its bounding boxes drawn on top, so you can quickly
page through a dataset and pull out the good ones.

## Supported annotation formats

Auto-detected per image — a folder can even mix both:

- **Pascal VOC XML** — `image.jpeg` + `image.xml`
- **YOLO txt** — `image.jpeg` + `image.txt`, with class names looked up from
  a shared `classes.names` (or `classes.txt` / `obj.names`) file in the same
  folder — one class name per line, matching the class ids used in the
  `.txt` files.

## Controls

| Key | Action |
|---|---|
| `→` / `D` | Next image |
| `←` / `A` | Previous image |
| `Enter` / `M` | Move current pair to the keep folder, then advance |
| `Backspace` | Undo the last move |
| `O` | Choose a different keep (destination) folder |
| `S` | Choose a different source (raw) folder |
| `Q` / `Esc` | Quit |

Your source/destination folder choices are remembered between runs (in
`.label_previewer_config.json`, next to the script — not committed to git).

## Requirements

- Python 3.9+
- Pillow (`pip install pillow`)
- Tkinter — ships with Python on Windows/Mac; on Linux install it separately
  (e.g. `sudo apt install python3-tk`)

## Install

### Windows

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

This installs the app to `%LOCALAPPDATA%\LabelPreviewer`, makes sure Pillow
is installed, and adds "Label Previewer" shortcuts to your Desktop and Start
Menu (with the app icon). Re-run it any time to update the installed copy.

To remove it: `powershell -ExecutionPolicy Bypass -File uninstall.ps1`

You can also just double-click `Label Previewer.pyw` directly from this
folder without installing anything.

### Linux

```bash
bash install.sh
```

Checks for `python3-tk`/Pillow and adds a "Label Previewer" entry to your
application menu.

### Run without installing

```bash
python label_previewer.py [source_folder] [dest_folder]
```

If the folders are omitted, you'll be prompted to pick them the first time.

## Files

- `label_previewer.py` — the app
- `make_icon.py` — regenerates `icon.ico` / `icon.png`
- `install.ps1` / `uninstall.ps1` — Windows installer
- `install.sh` — Linux installer
- `Label Previewer.pyw` — windowless entry point used by the Windows shortcuts
