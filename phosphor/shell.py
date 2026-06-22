"""The assembled Phosphor shell (CoreShell + every command-group mixin)."""

from .core import CoreShell
from .cmd_files import FilesMixin
from .cmd_tools import ToolsMixin
from .cmd_system import SystemMixin
from .toys import ToysMixin
from .games import GamesMixin
from .eggs import EggsMixin


class Phosphor(CoreShell, FilesMixin, ToolsMixin, SystemMixin, ToysMixin, GamesMixin, EggsMixin):
    pass


def main():
    while True:
        shell = Phosphor()
        shell.run()
        if not shell.reboot_requested:
            break
