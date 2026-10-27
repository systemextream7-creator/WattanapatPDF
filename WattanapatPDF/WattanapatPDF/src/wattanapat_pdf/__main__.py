import sys
if len(sys.argv) > 1 and sys.argv[1] in ("merge", "split", "protect", "watermark", "compress", "pdf2img",
                                          "img2pdf", "pdf2docx", "docx2pdf"):
    from .cli import main
else:
    from .app import main
raise SystemExit(main())
