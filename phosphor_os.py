#!/usr/bin/env python3
"""PHOSPHOR-OS launcher.

The implementation lives in the phosphor/ package next to this file (or next to
the .exe in a PyInstaller build). To allow the in-OS `update` command to replace
the code even in a built .exe, this launcher prefers a loose, on-disk phosphor/
folder over any copy bundled inside the executable.
"""
import os
import sys

if getattr(sys, "frozen", False):
    _base = os.path.dirname(os.path.abspath(sys.executable))
else:
    _base = os.path.dirname(os.path.abspath(__file__))

if _base not in sys.path:
    sys.path.insert(0, _base)

# In a frozen exe the bundled package would normally shadow the loose folder,
# so when a loose phosphor/ exists beside the exe we force-load it explicitly.
_loose = os.path.join(_base, "phosphor", "__init__.py")
if getattr(sys, "frozen", False) and os.path.isfile(_loose):
    import importlib.util
    _spec = importlib.util.spec_from_file_location(
        "phosphor", _loose,
        submodule_search_locations=[os.path.join(_base, "phosphor")])
    _mod = importlib.util.module_from_spec(_spec)
    sys.modules["phosphor"] = _mod
    _spec.loader.exec_module(_mod)

from phosphor.cli import main_entry

if __name__ == "__main__":
    main_entry()
