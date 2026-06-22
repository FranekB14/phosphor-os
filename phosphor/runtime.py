"""Process-wide mutable flags shared by every module."""
import sys

INTERACTIVE = sys.stdin.isatty()   # animations animate when True
GUI_ACTIVE = False                 # True while inside the GUI window
