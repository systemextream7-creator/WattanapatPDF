import multiprocessing
multiprocessing.freeze_support()   # the engine runs in a child process of the frozen exe
from wattanapat_pdf.app import main
raise SystemExit(main())
