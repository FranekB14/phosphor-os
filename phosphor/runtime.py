"""Process-wide mutable flags shared by every module."""
import sys

try:
    INTERACTIVE = bool(sys.stdin) and sys.stdin.isatty()  # animate when True
except Exception:
    INTERACTIVE = False                # windowed .exe has no stdin
GUI_ACTIVE = False                 # True while inside the GUI window
