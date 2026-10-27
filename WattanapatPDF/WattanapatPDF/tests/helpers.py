import io, os, random
from pathlib import Path
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, letter


def make_pdf(path, pages=3, size=A4, label="Page", with_image=False):
    c = canvas.Canvas(str(path), pagesize=size)
    for i in range(pages):
        c.setFont("Helvetica", 28)
        c.drawString(72, size[1] - 100, f"{label} {i + 1} of {pages}")
        c.setFont("Helvetica", 12)
        c.drawString(72, size[1] - 130, "The quick brown fox jumps over the lazy dog. " * 2)
        if with_image:
            rnd = random.Random(i)
            im = Image.effect_noise((1600, 1200), 64).convert("RGB")
            im = Image.blend(im, Image.new("RGB", im.size, (rnd.randint(0, 255), 120, 200)), 0.4)
            buf = io.BytesIO(); im.save(buf, "JPEG", quality=95); buf.seek(0)
            from reportlab.lib.utils import ImageReader
            c.drawImage(ImageReader(buf), 72, 200, 400, 300)
        c.showPage()
    c.save()
    return str(path)


def make_image(path, size=(800, 600), color=(200, 40, 40), fmt="JPEG"):
    Image.new("RGB", size, color).save(path, fmt)
    return str(path)
