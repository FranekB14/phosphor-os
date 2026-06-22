# PHOSPHOR-OS

> A retro CRT-terminal operating-system simulator written in Python — boot a haunted 1980s machine with a real shell, tools, games, and a few secrets.

PHOSPHOR-OS is a self-contained fake "operating system" that runs inside its own
terminal window. It has a boot sequence, a virtual filesystem, a working shell
with pipes and scripting, a built-in Python interpreter, an image-to-ASCII
converter, a pile of games and toys, six color themes, and some hidden things to
find.

---

## Running it

### Option A — the Windows app (easiest, no Python needed)

Grab the release folder (it contains `PhosphorOS.exe`, a `phosphor` folder, and a
`VERSION` file), then just **double-click `PhosphorOS.exe`**. The CRT terminal
window opens — that's it.

Keep the three items together in the same folder:

```
PhosphorOS.exe
phosphor\        <- the program code (this is what `update` replaces)
VERSION
```

The exe loads the code from the loose `phosphor\` folder, which is what lets the
built-in `update` command upgrade it later without you reinstalling anything.

### Option B — from source (any OS with Python)

Requires **Python 3.8+** (Tkinter is included with most installs; on some Linux
distros, `sudo apt install python3-tk`). From inside the project folder:

```
python phosphor_os.py             # opens the CRT terminal window (default)
python phosphor_os.py --console   # run inside your current terminal instead
python -m phosphor                # run it as a package
```

Keep `phosphor_os.py` and the `phosphor/` folder together — the launcher imports
the package. *(Optional: `pip install pillow` if you want the `img2ascii`
command.)*

## Updating

PHOSPHOR-OS can update itself. Inside the OS, run:

```
update            # download + install the latest, then restart
update --check    # only check whether a new version exists
```

It compares your version against the `VERSION` file at the repo root, downloads
the latest, backs up your current files to `.phosphor_backups/<timestamp>/`, and
asks you to restart.

## Commands

Type `help` inside the OS for the full list, or `help <command>` for details.

| Group | Commands |
|-------|----------|
| **Files** | `ls` `cd` `pwd` `tree` `mkdir` `rmdir` `touch` `write` `append` `cat` `rm` `cp` `mv` `find` `grep` `wc` `head` `tail` `sort` `nl` `edit` |
| **Tools** | `python` `img2ascii` `calc` `banner` `echo` `rev` `upper` `lower` `roll` `flip` `morse` `leet` `rot13` `bases` `asciitable` |
| **System** | `help` `clear` `theme` `sysinfo` `history` `alias` `unalias` `set` `unset` `run` `update` `scores` `setname` `whoami` `date` `time` `uptime` `ver` `save` `load` `format` `reboot` `exit` |
| **Toys** | `matrix` `hack` `cowsay` `fortune` `glitch` `8ball` `joke` `rainbow` `slot` `fire` `aquarium` `clock` |
| **Games** | `guess` `rps` `hangman` `ttt` `quiz` `wordle` |

## The shell

It behaves like a real shell, not just a command list:

- **Pipes** — `cat notes.txt | grep error | wc`
- **Redirection** — `cmd > file`, `cmd >> file` (append), `cmd < file`
- **Wildcards** — `ls *.txt`, `rm *.log`
- **Aliases** — `alias ll="ls"` (saved between sessions)
- **Variables** — `set NAME=value`, then `echo $NAME`; built-ins `$USER $VERSION $CWD $THEME $HOME`
- **Batch scripts** — `run script.txt` runs a file of commands; an `autoexec.bat`
  at the root of the virtual disk runs automatically on boot
- **A built-in editor** — `edit <file>` opens a simple line editor
- **Command history** — arrow keys, plus `history`
- **Tab completion** — for commands and file names

## Themes

Six color schemes: `phosphor` (green), `amber`, `ice`, `blood`, `plasma`, `mono`.
Switch with `theme <name>` — your choice is remembered.

```
theme amber
```

## Built-in Python

`python` drops you into a real Python interpreter, with the running OS exposed as
the variable `os_sim`. Type `exit()` to return to the shell.