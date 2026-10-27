"""Generate the Wattanapat PDF logo set from the original Wattanapat shape.

Reuses the silhouette of the supplied logo (blue rounded triangle) so the new
mark stays visibly part of the same family, then replaces the plain cross with a
PDF document that carries the cross.  Run:  python tools/make_branding.py <original_logo.png>
Outputs are written to ./assets
"""
import struct, sys, io
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

ASSETS = Path(__file__).resolve().parent.parent / "assets"
BLUE = (1, 129, 236)
BLUE_TOP = (52, 167, 255)
BLUE_BOT = (0, 104, 210)
NAVY = (9, 42, 84)
FONT_BI = "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def smooth_mask(src_png):
    a = np.array(Image.open(src_png).convert("RGBA"))[..., 3]
    m = Image.fromarray(((a > 128) * 255).astype("uint8"))
    ys, xs = np.where(np.array(m) > 0)
    return m.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))


PAD = 24  # original-pixel margin added around the silhouette before smoothing


def make_master(src_png, size=2048, small=False):
    sil = smooth_mask(src_png)
    W = size
    k = W * 0.88 / sil.width
    sw, sh = int(sil.width * k), int(sil.height * k)
    padded = Image.new("L", (sil.width + 2 * PAD, sil.height + 2 * PAD), 0)
    padded.paste(sil, (PAD, PAD))
    pw, ph = int(padded.width * k), int(padded.height * k)
    big = padded.resize((pw, ph), Image.LANCZOS).filter(ImageFilter.GaussianBlur(3.4 * k))
    big = big.point(lambda v: 255 if v > 128 else 0).filter(ImageFilter.GaussianBlur(1.6))
    ox, oy = (W - sw) // 2, (W - sh) // 2 - int(W * 0.01)
    mask = Image.new("L", (W, W), 0)
    mask.paste(big, (ox - int(PAD * k), oy - int(PAD * k)))
    grad = np.zeros((W, W, 4), dtype="uint8")
    t = np.clip((np.arange(W) - oy) / sh, 0, 1)[:, None]
    for i in range(3):
        grad[..., i] = (BLUE_TOP[i] * (1 - t) + BLUE_BOT[i] * t).astype("uint8")
    grad[..., 3] = 255
    img = Image.fromarray(grad, "RGBA")
    img.putalpha(mask)

    u = k * (sil.width / 475)

    def P(x, y):
        return ox + (x - 40) * u, oy + (y - 84) * k * (sil.height / 455)

    cx = 278
    d_l, d_r = cx - 98, cx + 98
    d_t, d_b = (150, 405) if not small else (140, 440)
    fold = 48
    layer = Image.new("RGBA", (W, W), (0, 0, 0, 0))

    sh_l = Image.new("L", (W, W), 0)
    ImageDraw.Draw(sh_l).rounded_rectangle([*P(d_l + 6, d_t + 12), *P(d_r + 6, d_b + 14)], radius=22 * u, fill=150)
    sh_l = ImageChops.multiply(sh_l.filter(ImageFilter.GaussianBlur(14 * u)), mask)
    shadow = Image.new("RGBA", (W, W), (0, 40, 110, 0))
    shadow.putalpha(sh_l)
    img = Image.alpha_composite(img, shadow)

    dd = ImageDraw.Draw(layer)
    r = 20 * u
    dd.rounded_rectangle([*P(d_l, d_t), *P(d_r, d_b)], radius=r, fill=(255, 255, 255, 255))
    cut = Image.new("L", (W, W), 0)
    ImageDraw.Draw(cut).polygon([P(d_r - fold, d_t - 2), P(d_r + 2, d_t - 2), P(d_r + 2, d_t + fold)], fill=255)
    layer.putalpha(ImageChops.subtract(layer.getchannel("A"), cut))
    dd = ImageDraw.Draw(layer)
    dd.polygon([P(d_r - fold, d_t), P(d_r - fold, d_t + fold), P(d_r, d_t + fold)], fill=(190, 224, 252, 255))

    cyc = d_t + (d_b - d_t) * (0.42 if not small else 0.5)
    arm, th = (50, 36) if not small else (62, 46)
    dd.rectangle([*P(cx - th / 2, cyc - arm), *P(cx + th / 2, cyc + arm)], fill=BLUE + (255,))
    dd.rectangle([*P(cx - arm, cyc - th / 2), *P(cx + arm, cyc + th / 2)], fill=BLUE + (255,))

    if not small:
        band = Image.new("L", (W, W), 0)
        ImageDraw.Draw(band).rectangle([*P(d_l - 10, d_b - 56), *P(d_r + 10, d_b + 10)], fill=255)
        band = ImageChops.multiply(band, layer.getchannel("A"))
        solid = Image.new("RGBA", (W, W), BLUE_BOT + (255,))
        solid.putalpha(band)
        layer = Image.alpha_composite(layer, solid)
        ImageDraw.Draw(layer).text(P(cx, d_b - 28), "PDF", font=ImageFont.truetype(FONT_B, int(30 * u)), fill="white", anchor="mm")
        f2 = ImageFont.truetype(FONT_BI, int(40 * u))
        f2 = ImageFont.truetype(FONT_BI, int(40 * u * (330 * u) / f2.getlength("WATTANAPAT")))
        ImageDraw.Draw(layer).text(P(cx, 468), "WATTANAPAT", font=f2, fill="white", anchor="mm")
    return Image.alpha_composite(img, layer)


def write_ico(path, images):
    entries, blobs, off = [], [], 6 + 16 * len(images)
    for im in images:
        b = io.BytesIO(); im.save(b, "PNG"); data = b.getvalue()
        w = im.width if im.width < 256 else 0
        entries.append(struct.pack("<BBBBHHII", w, w, 0, 0, 1, 32, len(data), off))
        blobs.append(data); off += len(data)
    Path(path).write_bytes(struct.pack("<HHH", 0, 1, len(images)) + b"".join(entries) + b"".join(blobs))


def lockup(master, white_text):
    H = 360
    icon = master.resize((H, H), Image.LANCZOS)
    f1, f2 = ImageFont.truetype(FONT_BI, 120), ImageFont.truetype(FONT_B, 46)
    W = H + 40 + int(f1.getlength("WATTANAPAT")) + 20
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    im.paste(icon, (0, 0), icon)
    d = ImageDraw.Draw(im)
    c1 = (255, 255, 255) if white_text else BLUE_BOT
    c2 = (190, 224, 252) if white_text else (90, 110, 140)
    d.text((H + 40, H // 2 - 14), "WATTANAPAT", font=f1, fill=c1, anchor="ls")
    d.text((H + 46, H // 2 + 56), "PDF  OFFLINE  TOOLKIT", font=f2, fill=c2, anchor="ls")
    return im


def installer_bmps(master):
    g = np.zeros((314, 164, 3), dtype="uint8")
    for i in range(3):
        g[..., i] = np.linspace(BLUE_TOP[i] * 0.55, NAVY[i], 314)[:, None]
    side = Image.fromarray(g, "RGB")
    ic = master.resize((140, 140), Image.LANCZOS)
    side.paste(ic, (12, 70), ic)
    d = ImageDraw.Draw(side)
    d.text((82, 235), "WATTANAPAT", font=ImageFont.truetype(FONT_BI, 15), fill="white", anchor="mm")
    d.text((82, 256), "PDF Offline Toolkit", font=ImageFont.truetype(FONT_B, 10), fill=(190, 224, 252), anchor="mm")
    side.save(ASSETS / "installer-side.bmp")
    small = Image.new("RGB", (55, 58), "white")
    ic = master.resize((52, 52), Image.LANCZOS)
    small.paste(ic, (1, 3), ic)
    small.save(ASSETS / "installer-small.bmp")


def main(src):
    ASSETS.mkdir(exist_ok=True)
    full = make_master(src, 2048)
    master = full.resize((1024, 1024), Image.LANCZOS)
    master.save(ASSETS / "logo-wattanapat-pdf.png")
    sm = make_master(src, 1024, small=True)
    ico_imgs = [(full if s >= 48 else sm).resize((s, s), Image.LANCZOS) for s in (256, 128, 64, 48, 32, 24, 16)]
    write_ico(ASSETS / "app.ico", ico_imgs)
    master.resize((256, 256), Image.LANCZOS).save(ASSETS / "logo-256.png")
    master.resize((96, 96), Image.LANCZOS).save(ASSETS / "logo-96.png")
    lockup(master, False).save(ASSETS / "logo-lockup.png")
    lockup(master, True).save(ASSETS / "logo-lockup-white.png")
    installer_bmps(master)
    print("branding written to", ASSETS)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/mnt/user-data/uploads/wattanapat-logo.png")
