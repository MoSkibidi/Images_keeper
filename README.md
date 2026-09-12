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
| `G` | Jump straight to a given image number |
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

The installers below now take care of everything themselves — Python,
Tkinter, and Pillow are all checked for and installed automatically if
they're missing, so there's no separate "install the requirements first"
step. Just download this repo (green **Code → Download ZIP** button on
GitHub, or `git clone`) and follow the steps for your OS.

### Windows

1. Double-click **`install.bat`**.
2. If it says Python isn't installed, it'll try to install it for you via
   `winget` — once that finishes, just double-click `install.bat` again.
3. A "Label Previewer" shortcut appears on your Desktop and in the Start
   Menu, with the app icon. Use that from now on.

To remove it, double-click **`uninstall.bat`**.

Prefer the command line? `powershell -ExecutionPolicy Bypass -File install.ps1`
(and `uninstall.ps1` to remove). You can also just double-click
`Label Previewer.pyw` directly from this folder without installing
anything.

### macOS

1. Double-click **`install_mac.command`**. (First time only: if macOS
   warns the file is from an unidentified developer, right-click it →
   **Open** instead, and confirm.)
2. It installs Python/Tkinter/Pillow for you (via Homebrew, if you have
   it) and builds a real **Label Previewer.app** in `~/Applications`.
3. Drag it to your Dock, or into `/Applications`, if you want it there
   instead. Re-run the `.command` file any time to rebuild it after
   pulling updates.

To remove it, double-click **`uninstall_mac.command`**.

Prefer the terminal? `bash install_mac.sh` (and `bash uninstall_mac.sh` to
remove) do the same thing.

If you don't have Homebrew and don't want it, install Python from
[python.org](https://www.python.org/downloads/macos/) instead (its
installer bundles Tkinter already), then run the installer again.

### Linux

```bash
bash install.sh
```

Detects your package manager (apt/dnf/pacman/zypper) and uses it to install
`python3-tk` and Pillow automatically (you'll be prompted for your `sudo`
password), then adds a "Label Previewer" entry to your application menu.

### Run without installing (any OS)

```bash
python3 label_previewer.py [source_folder] [dest_folder]
```

If the folders are omitted, you'll be prompted to pick them the first time.
This still needs Python 3.9+ with Pillow and Tkinter available — see
[Requirements](#requirements) above, or just run the installer for your OS,
which sets all that up for you either way.

## Files

- `label_previewer.py` — the app
- `make_icon.py` — regenerates `icon.ico` / `icon.icns` / `icon.png`
- `install.ps1` / `uninstall.ps1` — Windows installer (PowerShell)
- `install.bat` / `uninstall.bat` — double-clickable wrappers for the above
- `install_mac.sh` / `uninstall_mac.sh` — macOS installer (shell script)
- `install_mac.command` / `uninstall_mac.command` — double-clickable
  wrappers for the above
- `install.sh` — Linux installer
- `Label Previewer.pyw` — windowless entry point used by the Windows shortcuts
