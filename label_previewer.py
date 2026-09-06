"""
Label Previewer
================
Browse thousands of (image.jpeg, annotation) pairs, see the bounding boxes
drawn on the image, and move pairs you want to keep into a separate folder.

Two annotation formats are supported, auto-detected per image:
  - Pascal VOC XML   : image.jpeg + image.xml
  - YOLO txt         : image.jpeg + image.txt, with class names looked up
                        from a shared "classes.names" (or "classes.txt")
                        file in the source folder (one class name per line,
                        line number = class id used in the .txt files).

Controls
--------
  Right / D       -> next image
  Left  / A       -> previous image
  Enter / M       -> move current pair to the "keep" folder, then advance
  Backspace       -> undo the last move (moves the pair back)
  O               -> choose a different "keep" (destination) folder
  S               -> choose a different source (raw) folder
  Q / Escape      -> quit

Usage
-----
    python label_previewer.py [source_folder] [dest_folder]

If the folders are not given on the command line, you'll be asked to pick
them the first time you run the app; your choices are remembered (in
``.label_previewer_config.json`` next to this script) for next time.

Requires: Pillow (``pip install pillow``). Tkinter ships with Python.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from tkinter import Tk, Canvas, PhotoImage, filedialog, messagebox, StringVar
from tkinter import ttk

from PIL import Image, ImageTk

IMAGE_EXTS = (".jpeg", ".jpg")
CLASSES_FILENAMES = ("classes.names", "classes.txt", "obj.names")
CONFIG_PATH = Path(__file__).with_name(".label_previewer_config.json")

PALETTE = [
    "#e6194B", "#3cb44b", "#4363d8", "#f58231", "#911eb4",
    "#42d4f4", "#f032e6", "#bfef45", "#fabed4", "#469990",
    "#dcbeff", "#9A6324", "#800000", "#aaffc3", "#808000",
]


def color_for_label(label: str) -> str:
    return PALETTE[hash(label) % len(PALETTE)]


@dataclass
class Pair:
    image_path: Path
    annotation_path: Path
    fmt: str  # "xml" or "yolo"

    @property
    def stem(self) -> str:
        return self.image_path.stem


def find_classes_file(folder: Path) -> Path | None:
    for name in CLASSES_FILENAMES:
        candidate = folder / name
        if candidate.exists():
            return candidate
    return None


def load_classes(folder: Path) -> list[str]:
    classes_path = find_classes_file(folder)
    if classes_path is None:
        return []
    try:
        lines = classes_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    return [line.strip() for line in lines if line.strip()]


def find_pairs(folder: Path) -> list[Pair]:
    pairs = []
    for ext in IMAGE_EXTS:
        for img in folder.glob(f"*{ext}"):
            xml_path = img.with_suffix(".xml")
            txt_path = img.with_suffix(".txt")
            if xml_path.exists():
                pairs.append(Pair(img, xml_path, "xml"))
            elif txt_path.exists() and txt_path.name not in CLASSES_FILENAMES:
                pairs.append(Pair(img, txt_path, "yolo"))
    pairs.sort(key=lambda p: p.stem.lower())
    return pairs


def load_boxes_xml(xml_path: Path) -> list[tuple[str, int, int, int, int]]:
    """Returns list of (label, xmin, ymin, xmax, ymax). Tolerant of odd XML."""
    boxes = []
    try:
        root = ET.parse(xml_path).getroot()
    except ET.ParseError:
        return boxes
    for obj in root.findall("object"):
        name_el = obj.find("name")
        box_el = obj.find("bndbox")
        if box_el is None:
            continue
        try:
            xmin = int(float(box_el.findtext("xmin", "0")))
            ymin = int(float(box_el.findtext("ymin", "0")))
            xmax = int(float(box_el.findtext("xmax", "0")))
            ymax = int(float(box_el.findtext("ymax", "0")))
        except ValueError:
            continue
        label = name_el.text if name_el is not None and name_el.text else "?"
        boxes.append((label, xmin, ymin, xmax, ymax))
    return boxes


def load_boxes_yolo(
    txt_path: Path, classes: list[str], img_w: int, img_h: int
) -> list[tuple[str, int, int, int, int]]:
    """Returns list of (label, xmin, ymin, xmax, ymax) from a YOLO txt file.

    YOLO lines look like: ``class_id x_center y_center width height``, all
    normalized to [0, 1] relative to the image size.
    """
    boxes = []
    try:
        lines = txt_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return boxes
    for line in lines:
        parts = line.split()
        if len(parts) < 5:
            continue
        try:
            class_id = int(float(parts[0]))
            cx, cy, w, h = (float(p) for p in parts[1:5])
        except ValueError:
            continue
        xmin = int((cx - w / 2) * img_w)
        ymin = int((cy - h / 2) * img_h)
        xmax = int((cx + w / 2) * img_w)
        ymax = int((cy + h / 2) * img_h)
        label = classes[class_id] if 0 <= class_id < len(classes) else f"class {class_id}"
        boxes.append((label, xmin, ymin, xmax, ymax))
    return boxes


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_config(cfg: dict) -> None:
    try:
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    except OSError:
        pass


def set_app_icon(root: Tk) -> PhotoImage | None:
    """Sets the window/taskbar icon if icon.ico / icon.png sit next to this
    script. Returns the PhotoImage so the caller can keep a reference alive.
    """
    here = Path(__file__).parent
    try:
        ico_path = here / "icon.ico"
        if ico_path.exists():
            root.iconbitmap(default=str(ico_path))  # Windows title bar/taskbar
    except Exception:
        pass
    try:
        png_path = here / "icon.png"
        if png_path.exists():
            image = PhotoImage(file=str(png_path))
            root.iconphoto(True, image)  # cross-platform (Linux/Mac too)
            return image
    except Exception:
        pass
    return None


class App:
    def __init__(self, root: Tk, source: Path, dest: Path):
        self.root = root
        self.source = source
        self.dest = dest
        self.pairs = find_pairs(source)
        self.classes = load_classes(source)
        self.index = 0
        self.tk_image = None  # keep a reference so it isn't garbage collected
        self.last_moved: tuple[Pair, int] | None = None  # for undo

        root.title("Label Previewer")
        root.geometry("1280x820")
        root.configure(bg="#1e1e1e")
        self._icon_ref = set_app_icon(root)  # keep a reference so it isn't GC'd

        self.canvas = Canvas(root, bg="#111111", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.status_var = StringVar()
        status_bar = ttk.Label(
            root, textvariable=self.status_var, anchor="w",
            padding=(8, 4), background="#2b2b2b", foreground="white",
            font=("Segoe UI", 10),
        )
        status_bar.pack(fill="x", side="bottom")

        self.help_var = StringVar(
            value="←/→ or A/D: navigate    Enter/M: move to keep folder    "
                  "Backspace: undo last move    O: change keep folder    "
                  "S: change source folder    Q/Esc: quit"
        )
        help_bar = ttk.Label(
            root, textvariable=self.help_var, anchor="w",
            padding=(8, 2), background="#1e1e1e", foreground="#aaaaaa",
            font=("Segoe UI", 9),
        )
        help_bar.pack(fill="x", side="bottom")

        root.bind("<Right>", lambda e: self.next_image())
        root.bind("<d>", lambda e: self.next_image())
        root.bind("<D>", lambda e: self.next_image())
        root.bind("<Left>", lambda e: self.prev_image())
        root.bind("<a>", lambda e: self.prev_image())
        root.bind("<A>", lambda e: self.prev_image())
        root.bind("<Return>", lambda e: self.move_current())
        root.bind("<m>", lambda e: self.move_current())
        root.bind("<M>", lambda e: self.move_current())
        root.bind("<BackSpace>", lambda e: self.undo_move())
        root.bind("<o>", lambda e: self.choose_dest())
        root.bind("<O>", lambda e: self.choose_dest())
        root.bind("<s>", lambda e: self.choose_source())
        root.bind("<S>", lambda e: self.choose_source())
        root.bind("<q>", lambda e: root.quit())
        root.bind("<Q>", lambda e: root.quit())
        root.bind("<Escape>", lambda e: root.quit())
        root.bind("<Configure>", self._on_resize)

        self._resize_job = None
        self.render()

    # -- navigation -------------------------------------------------
    def next_image(self):
        if not self.pairs:
            return
        if self.index < len(self.pairs) - 1:
            self.index += 1
            self.render()

    def prev_image(self):
        if not self.pairs:
            return
        if self.index > 0:
            self.index -= 1
            self.render()

    def _on_resize(self, event):
        # Debounce redraw on resize to avoid flicker/lag while dragging.
        if self._resize_job is not None:
            self.root.after_cancel(self._resize_job)
        self._resize_job = self.root.after(100, self.render)

    # -- file operations ----------------------------------------------
    def move_current(self):
        if not self.pairs:
            return
        pair = self.pairs[self.index]
        self.dest.mkdir(parents=True, exist_ok=True)
        dest_img = self.dest / pair.image_path.name
        dest_ann = self.dest / pair.annotation_path.name
        if dest_img.exists() or dest_ann.exists():
            messagebox.showwarning(
                "Already exists",
                f"A file named '{pair.image_path.name}' or its annotation "
                f"already exists in the keep folder. Skipping move.",
            )
            return
        try:
            shutil.move(str(pair.image_path), str(dest_img))
            shutil.move(str(pair.annotation_path), str(dest_ann))
        except OSError as exc:
            messagebox.showerror("Move failed", str(exc))
            return

        # For YOLO datasets, make sure the kept folder has its own copy of
        # the shared classes file so the .txt annotations stay usable there.
        if pair.fmt == "yolo":
            classes_src = find_classes_file(self.source)
            if classes_src is not None:
                classes_dst = self.dest / classes_src.name
                if not classes_dst.exists():
                    try:
                        shutil.copy2(str(classes_src), str(classes_dst))
                    except OSError:
                        pass

        self.last_moved = (pair, self.index)
        del self.pairs[self.index]
        if self.index >= len(self.pairs):
            self.index = max(0, len(self.pairs) - 1)
        self.render()

    def undo_move(self):
        if self.last_moved is None:
            return
        pair, idx = self.last_moved
        dest_img = self.dest / pair.image_path.name
        dest_ann = self.dest / pair.annotation_path.name
        if not dest_img.exists() or not dest_ann.exists():
            messagebox.showwarning("Undo failed", "The moved files are no longer there.")
            self.last_moved = None
            return
        try:
            shutil.move(str(dest_img), str(pair.image_path))
            shutil.move(str(dest_ann), str(pair.annotation_path))
        except OSError as exc:
            messagebox.showerror("Undo failed", str(exc))
            return
        self.pairs.insert(min(idx, len(self.pairs)), pair)
        self.index = min(idx, len(self.pairs) - 1)
        self.last_moved = None
        self.render()

    def choose_dest(self):
        chosen = filedialog.askdirectory(title="Choose folder to move kept images to")
        if chosen:
            self.dest = Path(chosen)
            cfg = load_config()
            cfg["dest"] = str(self.dest)
            save_config(cfg)
            self.render()

    def choose_source(self):
        chosen = filedialog.askdirectory(title="Choose the folder with your labelled images")
        if not chosen:
            return
        self.source = Path(chosen)
        self.pairs = find_pairs(self.source)
        self.classes = load_classes(self.source)
        self.index = 0
        self.last_moved = None  # points at the old source's files; drop it
        cfg = load_config()
        cfg["source"] = str(self.source)
        save_config(cfg)
        self.render()

    # -- rendering ----------------------------------------------------
    def render(self):
        self.canvas.delete("all")

        if not self.pairs:
            self.canvas.create_text(
                640, 400, text="No labelled image pairs left in the source folder.",
                fill="white", font=("Segoe UI", 16),
            )
            self.status_var.set(f"Source: {self.source}    Keep folder: {self.dest}")
            return

        pair = self.pairs[self.index]
        try:
            image = Image.open(pair.image_path)
            image = image.convert("RGB")
        except Exception as exc:  # noqa: BLE001 - show any load error to the user
            self.canvas.create_text(
                640, 400, text=f"Failed to open image:\n{exc}",
                fill="#ff6666", font=("Segoe UI", 14),
            )
            self.status_var.set(f"{pair.image_path.name}  (error)")
            return

        img_w, img_h = image.size
        if pair.fmt == "xml":
            boxes = load_boxes_xml(pair.annotation_path)
        else:
            boxes = load_boxes_yolo(pair.annotation_path, self.classes, img_w, img_h)

        canvas_w = max(self.canvas.winfo_width(), 100)
        canvas_h = max(self.canvas.winfo_height() - 0, 100)
        scale = min(canvas_w / img_w, canvas_h / img_h)
        disp_w, disp_h = max(1, int(img_w * scale)), max(1, int(img_h * scale))

        resized = image.resize((disp_w, disp_h), Image.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(resized)

        off_x = (canvas_w - disp_w) // 2
        off_y = (canvas_h - disp_h) // 2
        self.canvas.create_image(off_x, off_y, anchor="nw", image=self.tk_image)

        for label, xmin, ymin, xmax, ymax in boxes:
            color = color_for_label(label)
            x1, y1 = off_x + xmin * scale, off_y + ymin * scale
            x2, y2 = off_x + xmax * scale, off_y + ymax * scale
            self.canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=2)
            text_y = y1 - 10 if y1 - 10 > off_y else y1 + 10
            self.canvas.create_text(
                x1 + 2, text_y, text=label, fill=color, anchor="w",
                font=("Segoe UI", 10, "bold"),
            )

        self.status_var.set(
            f"[{self.index + 1}/{len(self.pairs)}]  {pair.image_path.name}"
            f"    |  {len(boxes)} object(s)"
            f"    |  Keep folder: {self.dest}"
        )


def resolve_folder(cli_value: str | None, cfg_key: str, cfg: dict, prompt: str) -> Path:
    if cli_value:
        return Path(cli_value)
    if cfg.get(cfg_key):
        remembered = Path(cfg[cfg_key])
        if remembered.exists():
            return remembered
    chosen = filedialog.askdirectory(title=prompt)
    if not chosen:
        print("No folder chosen, exiting.")
        sys.exit(1)
    return Path(chosen)


def main():
    parser = argparse.ArgumentParser(
        description="Preview labelled image pairs (XML or YOLO txt annotations)."
    )
    parser.add_argument("source", nargs="?", help="Folder containing the image/annotation pairs")
    parser.add_argument("dest", nargs="?", help="Folder to move kept pairs into")
    args = parser.parse_args()

    if sys.platform == "win32":
        # Without this, Windows groups the window under pythonw.exe's own
        # taskbar identity (and its icon) instead of giving this app its
        # own taskbar entry/icon. Must be set before any window is created.
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "LabelPreviewer.App"
            )
        except Exception:
            pass

    root = Tk()
    root.withdraw()  # hide main window until folders are resolved

    cfg = load_config()
    source = resolve_folder(args.source, "source", cfg, "Choose the folder with your labelled images")
    dest = resolve_folder(args.dest, "dest", cfg, "Choose the folder to move kept images into")

    cfg["source"] = str(source)
    cfg["dest"] = str(dest)
    save_config(cfg)

    root.deiconify()
    App(root, source, dest)
    root.mainloop()


if __name__ == "__main__":
    main()
