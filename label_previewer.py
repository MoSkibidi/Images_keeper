"""
Label Previewer
================
Browse thousands of (image, annotation) pairs, see the bounding boxes
drawn on the image, and move pairs you want to keep into a separate folder.
Images can be .jpeg/.jpg/.png/.bmp.

Two annotation formats are supported, auto-detected per image:
  - Pascal VOC XML   : image.ext + image.xml
  - YOLO txt         : image.ext + image.txt, with class names looked up
                        from a shared "classes.names" (or "classes.txt")
                        file in the source folder (one class name per line,
                        line number = class id used in the .txt files).

Controls
--------
  Right / D             -> next image
  Left  / A             -> previous image
  G                     -> jump straight to a given image number
  Enter / M             -> move current pair to the "keep" folder, then advance
  Backspace             -> undo the last move (moves the pair back)
  O                     -> choose a different "keep" (destination) folder
  S                     -> choose a different source (raw) folder
  Q / Escape            -> quit

  Drag a box corner     -> resize that box (saved to the annotation file
                            as soon as you release the mouse)
  Drag inside a box      -> move that box
  Right-click a box     -> relabel it, picking from the labels already
                            used elsewhere in the dataset, or delete it
  Delete / X            -> delete the box currently under the cursor

Usage
-----
    python label_previewer.py [source_folder] [dest_folder]

If the folders are not given on the command line, you'll be asked to pick
them the first time you run the app; your choices are remembered (in
``.label_previewer_config.json`` next to this script) for next time.

Requires: Pillow (``pip install pillow``). Tkinter ships with Python.

Note on editing: resizing/moving/relabeling a box rewrites its annotation
file immediately. For YOLO ``.txt`` files this rewrites the whole file
(all boxes, recomputed). For XML files this rewrites just the touched
``<object>``, but since it's done via ``xml.etree.ElementTree`` the file's
original formatting/whitespace/comments are not preserved byte-for-byte
(the box data itself is unaffected).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from tkinter import Tk, Canvas, Menu, PhotoImage, filedialog, messagebox, simpledialog, StringVar
from tkinter import ttk

from PIL import Image, ImageTk

IMAGE_EXTS = (".jpeg", ".jpg", ".png", ".bmp")
CLASSES_FILENAMES = ("classes.names", "classes.txt", "obj.names")
CONFIG_PATH = Path(__file__).with_name(".label_previewer_config.json")

# Box-editing tuning (canvas pixels, independent of image resolution/zoom).
HANDLE_SIZE = 5   # half-width of the little corner-handle squares
HIT_RADIUS = 8    # how close a click needs to be to a corner to grab it

CORNER_CURSORS = {
    "tl": "top_left_corner", "tr": "top_right_corner",
    "bl": "bottom_left_corner", "br": "bottom_right_corner",
}

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


@dataclass
class Box:
    """One bounding box, editable in place and traceable back to its
    annotation file so an edit can be saved immediately."""
    label: str
    xmin: int
    ymin: int
    xmax: int
    ymax: int
    xml_obj: ET.Element | None = None  # xml fmt: the <object> element to update
    class_id: int | None = None        # yolo fmt: the class id to keep on save


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


def collect_xml_labels(pairs: list[Pair]) -> list[str]:
    """Scans every XML annotation once and returns the sorted set of
    distinct label names found, for the relabel menu."""
    labels: set[str] = set()
    for pair in pairs:
        if pair.fmt != "xml":
            continue
        try:
            root = ET.parse(pair.annotation_path).getroot()
        except ET.ParseError:
            continue
        for obj in root.findall("object"):
            name_el = obj.find("name")
            if name_el is not None and name_el.text:
                labels.add(name_el.text.strip())
    return sorted(labels)


def load_boxes_xml(xml_path: Path) -> tuple[ET.ElementTree | None, list[Box]]:
    """Returns (tree, boxes). Tolerant of odd XML; tree is None on parse
    failure. Each Box keeps a reference to its <object> element so an
    edit can be written straight back into ``tree`` and saved."""
    boxes: list[Box] = []
    try:
        tree = ET.parse(xml_path)
    except ET.ParseError:
        return None, boxes
    for obj in tree.getroot().findall("object"):
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
        boxes.append(Box(label, xmin, ymin, xmax, ymax, xml_obj=obj))
    return tree, boxes


def load_boxes_yolo(
    txt_path: Path, classes: list[str], img_w: int, img_h: int
) -> list[Box]:
    """Returns boxes decoded from a YOLO txt file (``class_id x_center
    y_center width height``, all normalized to [0, 1])."""
    boxes: list[Box] = []
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
        boxes.append(Box(label, xmin, ymin, xmax, ymax, class_id=class_id))
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
        self.xml_labels = collect_xml_labels(self.pairs)
        self.index = 0
        self.tk_image = None  # keep a reference so it isn't garbage collected
        self.last_moved: tuple[Pair, int] | None = None  # for undo

        # Current-image render state, kept around so mouse handlers can
        # hit-test/convert coordinates without recomputing everything.
        self.current_pair: Pair | None = None
        self.current_boxes: list[Box] = []
        self.current_tree: ET.ElementTree | None = None
        self.img_w = self.img_h = 1
        self.off_x = self.off_y = 0.0
        self.scale = 1.0

        # Box drag state.
        self.drag_mode: str | None = None   # None | "resize" | "move"
        self.drag_box_idx: int | None = None
        self.drag_corner: str | None = None
        self.drag_offset = (0.0, 0.0)
        self.hover_box_idx: int | None = None  # box under the cursor, for the Delete key

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
            value="←/→ or A/D: navigate    G: go to image #    "
                  "Enter/M: move to keep folder    "
                  "Backspace: undo last move    O: change keep folder    "
                  "S: change source folder    Q/Esc: quit    |    "
                  "Drag a corner: resize box    Drag inside: move box    "
                  "Right-click: relabel/delete box    Delete/X: delete hovered box"
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
        root.bind("<Delete>", lambda e: self.delete_hovered_box())
        root.bind("<x>", lambda e: self.delete_hovered_box())
        root.bind("<X>", lambda e: self.delete_hovered_box())
        root.bind("<g>", lambda e: self.go_to_index())
        root.bind("<G>", lambda e: self.go_to_index())
        root.bind("<Configure>", self._on_resize)

        # Box editing: drag corners/edges to resize, drag inside to move,
        # right-click to relabel. Bind both Button-2 and Button-3 for the
        # right-click menu since Tk maps the secondary click to different
        # button numbers across platforms/mice/trackpads.
        self.canvas.bind("<ButtonPress-1>", self.on_box_press)
        self.canvas.bind("<B1-Motion>", self.on_box_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_box_release)
        self.canvas.bind("<Motion>", self.on_box_hover)
        self.canvas.bind("<Button-2>", self.on_box_right_click)
        self.canvas.bind("<Button-3>", self.on_box_right_click)
        self.canvas.bind("<Control-Button-1>", self.on_box_right_click)

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

    def go_to_index(self):
        if not self.pairs:
            return
        n = simpledialog.askinteger(
            "Go to image",
            f"Image number (1-{len(self.pairs)}):",
            parent=self.root,
            minvalue=1,
            maxvalue=len(self.pairs),
            initialvalue=self.index + 1,
        )
        if n is None:
            return
        self.index = n - 1
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
        self.xml_labels = collect_xml_labels(self.pairs)
        self.index = 0
        self.last_moved = None  # points at the old source's files; drop it
        cfg = load_config()
        cfg["source"] = str(self.source)
        save_config(cfg)
        self.render()

    # -- box editing ----------------------------------------------------
    def _canvas_to_image(self, cx: float, cy: float) -> tuple[float, float]:
        x = (cx - self.off_x) / self.scale
        y = (cy - self.off_y) / self.scale
        return max(0.0, min(x, self.img_w)), max(0.0, min(y, self.img_h))

    def _box_screen_rect(self, box: Box) -> tuple[float, float, float, float]:
        x1 = self.off_x + box.xmin * self.scale
        y1 = self.off_y + box.ymin * self.scale
        x2 = self.off_x + box.xmax * self.scale
        y2 = self.off_y + box.ymax * self.scale
        return x1, y1, x2, y2

    def _corner_hit(self, cx: float, cy: float) -> tuple[int, str] | None:
        # Iterate topmost (last-drawn) box first so overlapping boxes favor
        # whichever one is visually on top.
        for i in reversed(range(len(self.current_boxes))):
            x1, y1, x2, y2 = self._box_screen_rect(self.current_boxes[i])
            for corner, (hx, hy) in (
                ("tl", (x1, y1)), ("tr", (x2, y1)),
                ("bl", (x1, y2)), ("br", (x2, y2)),
            ):
                if abs(cx - hx) <= HIT_RADIUS and abs(cy - hy) <= HIT_RADIUS:
                    return i, corner
        return None

    def _box_hit(self, cx: float, cy: float) -> int | None:
        for i in reversed(range(len(self.current_boxes))):
            x1, y1, x2, y2 = self._box_screen_rect(self.current_boxes[i])
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                return i
        return None

    def on_box_press(self, event):
        if not self.current_boxes:
            return
        hit = self._corner_hit(event.x, event.y)
        if hit is not None:
            self.drag_mode = "resize"
            self.drag_box_idx, self.drag_corner = hit
            return
        idx = self._box_hit(event.x, event.y)
        if idx is not None:
            box = self.current_boxes[idx]
            img_x, img_y = self._canvas_to_image(event.x, event.y)
            self.drag_mode = "move"
            self.drag_box_idx = idx
            self.drag_offset = (img_x - box.xmin, img_y - box.ymin)

    def on_box_drag(self, event):
        if self.drag_mode is None or self.drag_box_idx is None:
            return
        box = self.current_boxes[self.drag_box_idx]
        img_x, img_y = self._canvas_to_image(event.x, event.y)
        if self.drag_mode == "resize":
            if self.drag_corner in ("tl", "bl"):
                box.xmin = int(min(img_x, box.xmax - 1))
            else:
                box.xmax = int(max(img_x, box.xmin + 1))
            if self.drag_corner in ("tl", "tr"):
                box.ymin = int(min(img_y, box.ymax - 1))
            else:
                box.ymax = int(max(img_y, box.ymin + 1))
        else:  # move
            width, height = box.xmax - box.xmin, box.ymax - box.ymin
            new_xmin = max(0.0, min(img_x - self.drag_offset[0], self.img_w - width))
            new_ymin = max(0.0, min(img_y - self.drag_offset[1], self.img_h - height))
            box.xmin, box.ymin = int(new_xmin), int(new_ymin)
            box.xmax, box.ymax = box.xmin + width, box.ymin + height
        self._draw_boxes()

    def on_box_release(self, event):
        if self.drag_mode is not None:
            self.save_current_boxes()
        self.drag_mode = None
        self.drag_box_idx = None
        self.drag_corner = None

    def on_box_hover(self, event):
        if self.drag_mode is not None:
            return
        if not self.current_boxes:
            self.hover_box_idx = None
            return
        cursor = ""  # default arrow
        hit = self._corner_hit(event.x, event.y)
        box_idx = self._box_hit(event.x, event.y)
        if hit is not None:
            cursor = CORNER_CURSORS.get(hit[1], "")
            self.hover_box_idx = hit[0]
        elif box_idx is not None:
            cursor = "fleur"
            self.hover_box_idx = box_idx
        else:
            self.hover_box_idx = None
        try:
            self.canvas.config(cursor=cursor)
        except Exception:
            pass

    def on_box_right_click(self, event):
        if not self.current_boxes or self.current_pair is None:
            return
        idx = self._box_hit(event.x, event.y)
        if idx is None:
            return
        if self.current_pair.fmt == "yolo":
            # Only labels with a known class id can actually be encoded.
            options = [c for c in self.classes if c]
        else:
            options = sorted(set(self.classes) | set(self.xml_labels))
        if not options:
            return
        current_label = self.current_boxes[idx].label
        menu = Menu(self.root, tearoff=0)
        menu.add_command(label="🗑 Delete box", command=lambda i=idx: self.delete_box(i))
        menu.add_separator()
        for name in options:
            mark = "✓ " if name == current_label else "    "
            menu.add_command(
                label=f"{mark}{name}",
                command=lambda n=name, i=idx: self.relabel_box(i, n),
            )
        menu.tk_popup(event.x_root, event.y_root)

    def relabel_box(self, idx: int, new_label: str):
        if idx >= len(self.current_boxes):
            return
        box = self.current_boxes[idx]
        box.label = new_label
        if self.current_pair and self.current_pair.fmt == "yolo" and new_label in self.classes:
            box.class_id = self.classes.index(new_label)
        self._draw_boxes()
        self.save_current_boxes()

    def delete_hovered_box(self):
        if self.hover_box_idx is not None:
            self.delete_box(self.hover_box_idx)

    def delete_box(self, idx: int):
        if idx >= len(self.current_boxes):
            return
        pair = self.current_pair
        box = self.current_boxes[idx]
        if pair and pair.fmt == "xml" and self.current_tree is not None and box.xml_obj is not None:
            root_el = self.current_tree.getroot()
            try:
                root_el.remove(box.xml_obj)
            except ValueError:
                pass  # already not a direct child; nothing more we can do
        del self.current_boxes[idx]
        self.hover_box_idx = None
        self._draw_boxes()
        self.save_current_boxes()
        if pair:
            self.status_var.set(
                f"[{self.index + 1}/{len(self.pairs)}]  {pair.image_path.name}"
                f"    |  {len(self.current_boxes)} object(s)"
                f"    |  Keep folder: {self.dest}"
            )

    def save_current_boxes(self):
        """Writes self.current_boxes back to the current pair's annotation
        file. Called immediately after any resize/move/relabel."""
        pair = self.current_pair
        if pair is None:
            return
        if pair.fmt == "xml":
            if self.current_tree is None:
                return
            for box in self.current_boxes:
                if box.xml_obj is None:
                    continue
                bndbox = box.xml_obj.find("bndbox")
                if bndbox is not None:
                    for tag, value in (
                        ("xmin", box.xmin), ("ymin", box.ymin),
                        ("xmax", box.xmax), ("ymax", box.ymax),
                    ):
                        el = bndbox.find(tag)
                        if el is not None:
                            el.text = str(int(round(value)))
                name_el = box.xml_obj.find("name")
                if name_el is not None:
                    name_el.text = box.label
            try:
                self.current_tree.write(pair.annotation_path, encoding="utf-8")
            except OSError as exc:
                messagebox.showerror("Save failed", str(exc))
        else:  # yolo: rewrite the whole file from the current boxes
            lines = []
            for box in self.current_boxes:
                class_id = box.class_id if box.class_id is not None else 0
                cx = (box.xmin + box.xmax) / 2 / self.img_w
                cy = (box.ymin + box.ymax) / 2 / self.img_h
                w = (box.xmax - box.xmin) / self.img_w
                h = (box.ymax - box.ymin) / self.img_h
                lines.append(f"{class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
            try:
                text = "\n".join(lines) + ("\n" if lines else "")
                pair.annotation_path.write_text(text, encoding="utf-8")
            except OSError as exc:
                messagebox.showerror("Save failed", str(exc))

    # -- rendering ----------------------------------------------------
    def _draw_boxes(self):
        self.canvas.delete("boxlayer")
        for box in self.current_boxes:
            color = color_for_label(box.label)
            x1, y1, x2, y2 = self._box_screen_rect(box)
            self.canvas.create_rectangle(
                x1, y1, x2, y2, outline=color, width=2, tags=("boxlayer",)
            )
            text_y = y1 - 10 if y1 - 10 > self.off_y else y1 + 10
            self.canvas.create_text(
                x1 + 2, text_y, text=box.label, fill=color, anchor="w",
                font=("Segoe UI", 10, "bold"), tags=("boxlayer",),
            )
            for hx, hy in ((x1, y1), (x2, y1), (x1, y2), (x2, y2)):
                self.canvas.create_rectangle(
                    hx - HANDLE_SIZE, hy - HANDLE_SIZE,
                    hx + HANDLE_SIZE, hy + HANDLE_SIZE,
                    outline=color, fill=color, tags=("boxlayer",),
                )

    def render(self):
        self.canvas.delete("all")
        self.drag_mode = None
        self.drag_box_idx = None
        self.drag_corner = None

        if not self.pairs:
            self.current_pair = None
            self.current_boxes = []
            self.current_tree = None
            self.canvas.create_text(
                640, 400, text="No labelled image pairs left in the source folder.",
                fill="white", font=("Segoe UI", 16),
            )
            self.status_var.set(f"Source: {self.source}    Keep folder: {self.dest}")
            return

        pair = self.pairs[self.index]
        self.current_pair = pair
        try:
            image = Image.open(pair.image_path)
            image = image.convert("RGB")
        except Exception as exc:  # noqa: BLE001 - show any load error to the user
            self.current_boxes = []
            self.current_tree = None
            self.canvas.create_text(
                640, 400, text=f"Failed to open image:\n{exc}",
                fill="#ff6666", font=("Segoe UI", 14),
            )
            self.status_var.set(f"{pair.image_path.name}  (error)")
            return

        img_w, img_h = image.size
        self.img_w, self.img_h = img_w, img_h
        if pair.fmt == "xml":
            self.current_tree, self.current_boxes = load_boxes_xml(pair.annotation_path)
        else:
            self.current_tree = None
            self.current_boxes = load_boxes_yolo(pair.annotation_path, self.classes, img_w, img_h)

        canvas_w = max(self.canvas.winfo_width(), 100)
        canvas_h = max(self.canvas.winfo_height() - 0, 100)
        scale = min(canvas_w / img_w, canvas_h / img_h)
        disp_w, disp_h = max(1, int(img_w * scale)), max(1, int(img_h * scale))

        resized = image.resize((disp_w, disp_h), Image.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(resized)

        self.off_x = (canvas_w - disp_w) // 2
        self.off_y = (canvas_h - disp_h) // 2
        self.scale = scale
        self.canvas.create_image(self.off_x, self.off_y, anchor="nw", image=self.tk_image, tags=("image",))

        self._draw_boxes()

        self.status_var.set(
            f"[{self.index + 1}/{len(self.pairs)}]  {pair.image_path.name}"
            f"    |  {len(self.current_boxes)} object(s)"
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
