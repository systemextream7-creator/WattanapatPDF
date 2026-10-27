"""Command line access to the same offline engine (handy for batch jobs)."""
from __future__ import annotations
import argparse, json, sys, tempfile
from .engine import ops
from .engine.ops import EngineError


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="wattanapat-pdf", description="Offline PDF toolkit")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("merge"); p.add_argument("out"); p.add_argument("files", nargs="+")
    p = sub.add_parser("split"); p.add_argument("src"); p.add_argument("out_dir"); p.add_argument("--ranges", default="")
    p.add_argument("--each", action="store_true")
    p = sub.add_parser("protect"); p.add_argument("src"); p.add_argument("out")
    p.add_argument("--user", default=""); p.add_argument("--owner", default="")
    p.add_argument("--no-print", action="store_true"); p.add_argument("--no-modify", action="store_true")
    p.add_argument("--no-copy", action="store_true")
    p = sub.add_parser("watermark"); p.add_argument("src"); p.add_argument("out"); p.add_argument("text")
    p.add_argument("--position", type=int, default=4); p.add_argument("--opacity", type=float, default=0.25)
    p.add_argument("--size", type=int, default=56); p.add_argument("--rotation", type=float, default=45)
    p.add_argument("--color", default="#808080")
    p = sub.add_parser("compress"); p.add_argument("src"); p.add_argument("out")
    p.add_argument("--level", choices=["quality", "email", "smallest"], default="email")
    p = sub.add_parser("pdf2img"); p.add_argument("src"); p.add_argument("out_dir")
    p.add_argument("--fmt", default="png"); p.add_argument("--dpi", type=int, default=150)
    p = sub.add_parser("img2pdf"); p.add_argument("out"); p.add_argument("images", nargs="+")
    p.add_argument("--fit", action="store_true")
    p = sub.add_parser("pdf2docx"); p.add_argument("src"); p.add_argument("out")
    p = sub.add_parser("docx2pdf"); p.add_argument("src"); p.add_argument("out")
    a = ap.parse_args(argv)
    ops.set_work_dir(tempfile.mkdtemp(prefix="wp-cli-"))
    try:
        if a.cmd == "merge": r = ops.merge([{"path": f} for f in a.files], a.out)
        elif a.cmd == "split": r = ops.split(a.src, a.out_dir, "each" if a.each else "ranges", a.ranges)
        elif a.cmd == "protect": r = ops.protect(a.src, a.out, a.user, a.owner, not a.no_print, not a.no_modify, not a.no_copy)
        elif a.cmd == "watermark":
            r = ops.watermark(a.src, a.out, {"kind": "text", "text": a.text, "position": a.position, "opacity": a.opacity,
                                             "font_size": a.size, "rotation": a.rotation, "color": a.color})
        elif a.cmd == "compress": r = ops.compress(a.src, a.out, a.level)
        elif a.cmd == "pdf2img": r = ops.pdf_to_images(a.src, a.out_dir, a.fmt, a.dpi)
        elif a.cmd == "img2pdf": r = ops.images_to_pdf(a.images, a.out, "fit" if a.fit else "A4")
        elif a.cmd == "pdf2docx": r = ops.pdf_to_docx(a.src, a.out)
        else: r = ops.docx_to_pdf(a.src, a.out)
    except EngineError as e:
        print("ERROR:", e, file=sys.stderr)
        return 1
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
