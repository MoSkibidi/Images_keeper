"""
Generates icon.ico (Windows), icon.icns (macOS), and icon.png (Linux, and
the cross-platform Tk window icon) for Label Previewer.
Run once: ``python make_icon.py``
"""

from PIL import Image, ImageDraw

SIZE = 256


def build_icon() -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded-square background.
    bg = (30, 96, 145, 255)      # deep blue
    draw.rounded_rectangle([8, 8, SIZE - 8, SIZE - 8], radius=48, fill=bg)

    # A "photo" card, tilted look kept simple (axis-aligned) with a
    # mountain + sun scene, like a generic picture icon.
    card = [44, 60, 188, 172]
    draw.rectangle(card, fill=(240, 244, 248, 255), outline=(20, 60, 90, 255), width=4)

    # Sun.
    draw.ellipse([150, 76, 176, 102], fill=(255, 196, 61, 255))

    # Mountains.
    draw.polygon([(56, 160), (96, 104), (128, 140), (150, 112), (178, 160)],
                 fill=(58, 133, 99, 255))
    draw.polygon([(56, 160), (96, 104), (118, 132), (100, 160)],
                 fill=(44, 108, 79, 255))

    # Bounding-box annotation overlay (the "labelling" motif), drawn
    # slightly larger than the card and offset so it reads as an
    # annotation box drawn on top of a photo.
    box = [96, 96, 220, 200]
    box_color = (255, 92, 92, 255)
    draw.rectangle(box, outline=box_color, width=6)
    handle = 10
    for x, y in [(box[0], box[1]), (box[2], box[1]), (box[0], box[3]), (box[2], box[3])]:
        draw.rectangle([x - handle // 2, y - handle // 2, x + handle // 2, y + handle // 2],
                        fill=box_color)

    return img


def main():
    icon = build_icon()
    icon.save("icon.png")
    # bitmap_format="bmp" makes Pillow store each entry as classic
    # BMP/DIB pixel data instead of PNG. Pillow's ICO default (PNG for
    # every size) isn't understood by some Windows icon-loading paths
    # (e.g. the legacy System.Drawing.Icon API), which then render
    # garbage instead of falling back gracefully - this is what was
    # causing the Desktop/taskbar icon to show wrong.
    icon.save(
        "icon.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
        bitmap_format="bmp",
    )
    # ICNS (unlike ICO) is expected to use PNG-compressed entries even for
    # small sizes on modern macOS, so Pillow's default here is fine as-is.
    icon.save("icon.icns")
    print("Wrote icon.png, icon.ico, and icon.icns")


if __name__ == "__main__":
    main()
