"""PHOSPHOR-OS -- a retro CRT-terminal OS simulator (modular package).

Generated from the monolith by refactor_phosphor.py.
"""
import os

# Enable ANSI escape sequences on Windows 10+ consoles.
if os.name == "nt":
    os.system("")

from .shell import Phosphor, main

__all__ = ["Phosphor", "main"]
