"""Construction smoke test for the UI code using a permissive fake of PySide6.

This only catches mistakes in OUR code (typos, missing attributes, wrong hook names).
It cannot verify real Qt behaviour - run the app on Windows for that.
Skipped automatically when real PySide6 is installed (then test_ui_real is meaningful instead).
"""
import importlib.util, os, sys, tempfile, types, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
REAL = importlib.util.find_spec("PySide6") is not None


class _Meta(type):
    def __getattr__(cls, n):
        if n.startswith("__"):
            raise AttributeError(n)
        return _Any()


class _Any(metaclass=_Meta):
    def __init__(self, *a, **k): pass
    def __call__(self, *a, **k): return _Any()
    def __getattr__(self, n):
        if n.startswith("__"):
            raise AttributeError(n)
        return _Any()
    def __iter__(self): return iter(())
    def __index__(self): return 0
    def __int__(self): return 0
    def __bool__(self): return False
    def __len__(self): return 0
    def __add__(self, o): return _Any()
    __radd__ = __sub__ = __mul__ = __rmul__ = __or__ = __and__ = __truediv__ = __floordiv__ = __add__
    def __eq__(self, o): return False
    def __lt__(self, o): return False
    __gt__ = __le__ = __ge__ = __lt__
    def __hash__(self): return id(self)


def _install_fake():
    cache = {}

    def mod(name):
        m = types.ModuleType(name)
        def getattr_(n):
            if n.startswith("__"):
                raise AttributeError(n)
            if n not in cache:
                cache[n] = type(n, (_Any,), {})
            return cache[n]
        m.__getattr__ = getattr_
        return m
    pkg = mod("PySide6")
    for sub in ("QtCore", "QtGui", "QtWidgets"):
        m = mod("PySide6." + sub)
        setattr(pkg, sub, m)
        sys.modules["PySide6." + sub] = m
    sys.modules["PySide6"] = pkg


@unittest.skipIf(REAL, "real PySide6 present")
class TestUiConstruction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _install_fake()
        cls.td = tempfile.TemporaryDirectory()
        os.environ["WATTANAPAT_DATA_DIR"] = cls.td.name + "/data"
        os.environ["WATTANAPAT_LOCAL_DIR"] = cls.td.name + "/local"

    def test_all_pages_construct_and_presets_roundtrip(self):
        from wattanapat_pdf.settings import Settings
        from wattanapat_pdf.sandbox import Sandbox
        from wattanapat_pdf.engine.service import DirectClient
        from wattanapat_pdf.ui.context import AppContext
        from wattanapat_pdf.ui.main_window import MainWindow, TOOL_CLASSES
        sb = Sandbox(Path(self.td.name) / "sb"); sb.start()
        ctx = AppContext(Settings(Path(self.td.name) / "s.json"), sb, DirectClient(str(sb.session)))
        win = MainWindow(ctx)
        self.assertEqual(set(ctx.pages), {c.key for c in TOOL_CLASSES})
        for i in range(4):
            ctx.apply_preset(i)
        for page in ctx.pages.values():
            part = page.preset_part()
            self.assertTrue(part is None or isinstance(part, dict))
        sb.close()

    def test_every_tool_page_implements_hooks(self):
        from wattanapat_pdf.ui import pages_tools as pt
        for cls in (pt.MergePage, pt.SplitPage, pt.OrganizePage, pt.ImagesPage, pt.ProtectPage,
                    pt.WatermarkPage, pt.CompressPage, pt.ConvertPage):
            for hook in ("build_workspace", "plan", "accept_paths", "clear_all"):
                self.assertTrue(callable(getattr(cls, hook)), (cls, hook))


if __name__ == "__main__":
    unittest.main(verbosity=2)
