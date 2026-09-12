# Label Previewer

A small desktop app for reviewing thousands of labelled `image + annotation`
pairs one at a time, and sorting the ones you want to keep into a separate
folder.

It shows each image with its bounding boxes drawn on top, so you can quickly
page through a dataset and pull out the good ones.

## Supported annotation formats

Images can be `.jpeg`, `.jpg`, `.png`, or `.bmp`. Annotation format is
auto-detected per image — a folder can even mix both:

- **Pascal VOC XML** — `image.ext` + `image.xml`
- **YOLO txt** — `image.ext` + `image.txt`, with class names looked up from
  a shared `classes.names` (or `classes.txt` / `obj.names`) file in the same
  folder — one class name per line, matching the class ids used in the
  `.txt` files.

## Controls

| Key / Mouse | Action |
|---|---|
| `→` / `D` | Next image |
| `←` / `A` | Previous image |
| `Enter` / `M` | Move current pair to the keep folder, then advance |
| `Backspace` | Undo the last move |
| `O` | Choose a different keep (destination) folder |
| `S` | Choose a different source (raw) folder |
| `Q` / `Esc` | Quit |
| Drag a box corner | Resize that box |
| Drag inside a box | Move that box |
| Right-click a box | Relabel it (from labels already used in the dataset) or delete it |
| `Delete` / `X` | Delete the box currently under the cursor |

Your source/destination folder choices are remembered between runs (in
`.label_previewer_config.json`, next to the script — not committed to git).

## Editing boxes

Each box is drawn with small square handles at its 4 corners:

- **Drag a corner** to resize the box.
- **Drag anywhere else inside the box** to move it (it's clamped so it can't
  be dragged outside the image).
- **Right-click a box** for a menu with **Delete box**, plus every label
  already used elsewhere in the dataset (all `<name>` values seen across
  your `.xml` files, plus your `classes.names` list) — pick a label to
  relabel it.
- **`Delete` or `X`** deletes the box currently under the mouse cursor,
  without needing to right-click.

Edits are saved to the annotation file the moment you release the drag or
pick a label, no separate save step needed:

- **YOLO `.txt`** files are rewritten in full, with every box's coordinates
  recomputed and normalized.
- **Pascal VOC XML** files have just the touched `<object>`'s `<bndbox>` /
  `<name>` updated in place, via Python's `xml.etree.ElementTree`. The box
  data is correct, but note this doesn't preserve the original file's exact
  formatting/whitespace/comments byte-for-byte.

## Requirements

- Python 3.9+
- Pillow (the installers below install it for you if it's missing;
  otherwise `pip install pillow` / `pip3 install pillow`)
- Tkinter — bundled with the official python.org installer on
  Windows/macOS. On Linux, or on macOS if you installed Python via
  Homebrew, it needs installing separately (see below).

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

### macOS

```bash
bash install_mac.sh
```

Checks that `python3` has Tkinter, installs Pillow for the current user if
needed, and builds a real double-clickable **Label Previewer.app** in
`~/Applications` (no admin/sudo needed) with the custom icon. Drag it to
your Dock, or into `/Applications`, if you want it there instead. Re-run
the script any time to rebuild it after pulling updates.

To remove it: `bash uninstall_mac.sh`

If `python3` or Tkinter is missing, the script tells you exactly what to
run — typically:

```bash
brew install python python-tk
```

(Get Homebrew from [brew.sh](https://brew.sh) if you don't have it. The
official installer from [python.org](https://www.python.org/downloads/macos/)
bundles Tkinter too, if you'd rather not use Homebrew.)

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
- `make_icon.py` — regenerates `icon.ico` / `icon.icns` / `icon.png`
- `install.ps1` / `uninstall.ps1` — Windows installer
- `install_mac.sh` / `uninstall_mac.sh` — macOS installer
- `install.sh` — Linux installer
- `Label Previewer.pyw` — windowless entry point used by the Windows shortcuts
