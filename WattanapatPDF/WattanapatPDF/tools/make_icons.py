"""Draw the sidebar/tool icons (simple line art) in white and brand blue.  python tools/make_icons.py"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageChops

OUT = Path(__file__).resolve().parent.parent / "assets" / "icons"
S = 256  # drawing canvas; downsampled to 64
LW = 16


def doc(d, x, y, w, h, c, lw=LW):
    d.rounded_rectangle([x, y, x + w, y + h], radius=18, outline=c, width=lw)


def arrow(d, x1, y1, x2, y2, c, lw=LW, head=34):
    d.line([x1, y1, x2, y2], fill=c, width=lw)
    import math
    a = math.atan2(y2 - y1, x2 - x1)
    for s in (-0.5, 0.5):
        d.line([x2, y2, x2 - head * math.cos(a + s), y2 - head * math.sin(a + s)], fill=c, width=lw)


def draw(name, c):
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if name == "home":
        d.line([28, 128, 128, 40, 228, 128], fill=c, width=LW, joint="curve")
        d.line([52, 112, 52, 216, 204, 216, 204, 112], fill=c, width=LW, joint="curve")
        d.rectangle([108, 150, 148, 216], outline=c, width=LW)
    elif name == "merge":
        doc(d, 24, 28, 78, 100, c); doc(d, 24, 128, 78, 100, c)
        arrow(d, 112, 128, 160, 128, c, head=26); doc(d, 168, 70, 64, 116, c)
    elif name == "split":
        doc(d, 24, 70, 64, 116, c)
        arrow(d, 98, 128, 146, 128, c, head=26); doc(d, 154, 28, 78, 90, c); doc(d, 154, 138, 78, 90, c)
    elif name == "organize":
        for x in (32, 140):
            for y in (32, 140):
                d.rounded_rectangle([x, y, x + 84, y + 84], radius=14, outline=c, width=LW)
    elif name == "image":
        d.rounded_rectangle([24, 40, 232, 216], radius=22, outline=c, width=LW)
        d.polygon([(44, 196), (104, 120), (148, 170), (176, 138), (216, 196)], fill=c)
        d.ellipse([160, 68, 200, 108], fill=c)
    elif name == "lock":
        d.rounded_rectangle([44, 110, 212, 224], radius=22, outline=c, width=LW)
        d.arc([74, 30, 182, 150], 180, 360, fill=c, width=LW)
        d.line([74, 90, 74, 110], fill=c, width=LW); d.line([182, 90, 182, 110], fill=c, width=LW)
        d.ellipse([116, 150, 140, 174], fill=c)
    elif name == "watermark":
        outer = Image.new("L", (S, S), 0); od = ImageDraw.Draw(outer)
        od.polygon([(128, 22), (65.6, 100), (190.4, 100)], fill=255); od.ellipse([48, 70, 208, 230], fill=255)
        inner = Image.new("L", (S, S), 0); idr = ImageDraw.Draw(inner)
        idr.polygon([(128, 54), (79.4, 113.5), (176.6, 113.5)], fill=255); idr.ellipse([68, 90, 188, 210], fill=255)
        ring = ImageChops.subtract(outer, inner)
        solid = Image.new("RGBA", (S, S), c); solid.putalpha(ring)
        im = Image.alpha_composite(im, solid)
        ImageDraw.Draw(im).arc([86, 118, 150, 182], 100, 200, fill=c, width=LW - 4)
    elif name == "compress":
        arrow(d, 128, 20, 128, 100, c, head=30); arrow(d, 128, 236, 128, 156, c, head=30)
        d.line([40, 128, 216, 128], fill=c, width=LW)
        d.line([72, 100, 184, 100], fill=c, width=LW - 4); d.line([72, 156, 184, 156], fill=c, width=LW - 4)
    elif name == "convert":
        arrow(d, 36, 90, 220, 90, c); arrow(d, 220, 166, 36, 166, c)
    elif name == "preset":
        for y, k in ((60, 90), (128, 168), (196, 120)):
            d.line([30, y, 226, y], fill=c, width=LW - 4)
            d.ellipse([k - 22, y - 22, k + 22, y + 22], fill=(255, 255, 255, 0), outline=c, width=LW)
    elif name == "shield":
        d.polygon([(128, 20), (216, 56), (216, 128), (128, 236), (40, 128), (40, 56)], outline=c, width=LW)
        d.line([84, 124, 118, 160, 176, 90], fill=c, width=LW + 2, joint="curve")
    elif name == "gear":
        import math
        for k in range(8):
            a = math.radians(k * 45)
            x, y = 128 + 88 * math.cos(a), 128 + 88 * math.sin(a)
            d.ellipse([x - 20, y - 20, x + 20, y + 20], fill=c)
        d.ellipse([48, 48, 208, 208], fill=c)
        d.ellipse([92, 92, 164, 164], fill=(0, 0, 0, 0))
    return im.resize((64, 64), Image.LANCZOS)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    names = "home merge split organize image lock watermark compress convert preset shield gear".split()
    for n in names:
        for col, rgb in (("white", (255, 255, 255, 255)), ("blue", (1, 129, 236, 255))):
            # the gear / shield hole needs real transparency: draw on a big canvas then punch
            im = draw(n, rgb)
            if n == "gear":
                big = Image.new("RGBA", (S, S), (0, 0, 0, 0)); bd = ImageDraw.Draw(big)
                import math
                for k in range(8):
                    a = math.radians(k * 45)
                    x, y = 128 + 88 * math.cos(a), 128 + 88 * math.sin(a)
                    bd.ellipse([x - 20, y - 20, x + 20, y + 20], fill=rgb)
                bd.ellipse([48, 48, 208, 208], fill=rgb)
                hole = Image.new("L", (S, S), 255); ImageDraw.Draw(hole).ellipse([92, 92, 164, 164], fill=0)
                big.putalpha(Image.composite(big.getchannel("A"), Image.new("L", (S, S), 0), hole))
                im = big.resize((64, 64), Image.LANCZOS)
            im.save(OUT / f"{n}-{col}.png")
    print("icons:", len(names) * 2)


if __name__ == "__main__":
    main()
