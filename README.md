# PHOSPHOR-OS

> A retro CRT-terminal operating-system simulator written in Python — boot a haunted 1980s machine with a real shell, networking, tools, games, and a few secrets.

PHOSPHOR-OS is a self-contained fake "operating system" that runs inside its own
green-on-black terminal window. It boots with a POST sequence, gives you a
working shell (pipes, redirection, scripting, history, tab-completion), a virtual
filesystem that persists between sessions, a built-in real Python interpreter, a
simulated network to explore, an image-to-ASCII converter, fullscreen
screensavers, six color themes, a pile of games and toys — and a few things
hidden in the dark.

Everything runs on the Python standard library. The only optional dependency is
Pillow, and only for one command.

---

## Contents

- [Running it](#running-it)
- [Updating](#updating)
- [Command reference](#command-reference)
- [The shell](#the-shell)
- [Users & permissions](#users--permissions)
- [The network](#the-network)
- [Screensavers](#screensavers)
- [Games & toys](#games--toys)
- [Built-in Python](#built-in-python)
- [Image to ASCII](#image-to-ascii)
- [Themes](#themes)
- [The virtual disk & your data](#the-virtual-disk--your-data)
- [Keyboard & tips](#keyboard--tips)
- [Secrets](#secrets)
- [License](#license)

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

Requires **Python 3.8+** (Tkinter ships with most installs; on some Linux distros
run `sudo apt install python3-tk`). From inside the project folder:

```
python phosphor_os.py             # opens the CRT terminal window (default)
python phosphor_os.py --console   # run inside your current terminal instead
python -m phosphor                # run it as a package
```

Keep `phosphor_os.py` and the `phosphor/` folder together — the launcher imports
the package. *(Optional: `pip install pillow` if you want the `img2ascii`
command.)*

If Tkinter is missing, PHOSPHOR-OS falls back to running inside your existing
terminal automatically.

---

## Updating

PHOSPHOR-OS can update itself from its GitHub home. Inside the OS:

```
update            # download + install the latest, then restart
update --check    # only check whether a newer version exists
update --force    # reinstall even if you're already current
```

It compares your `VERSION` against the one in the repo, downloads the latest,
backs your current files up to `.phosphor_backups/<timestamp>/`, mirrors the new
code into place, and asks you to restart. The loose `phosphor\` folder beside the
exe is what makes this possible — no rebuild needed.

---

## Command reference

There are **127 commands**. Type `help` inside the OS for the live list, or
`help <command>` for usage and aliases. Almost every command has short aliases
(shown in parentheses).

### Filesystem

| Command | What it does |
|---------|--------------|
| `ls` (dir) | List directory contents |
| `cd` | Change directory ( `..` = up, `/` = root ) |
| `pwd` | Print working directory |
| `tree` | Show the directory structure as a tree |
| `mkdir` (md) | Create a directory |
| `rmdir` | Remove an empty directory |
| `touch` (new) | Create an empty file |
| `write` | Overwrite a file with text |
| `append` | Append text to a file |
| `cat` (type) | Print file contents |
| `rm` (del) | Delete a file |
| `cp` (copy) | Copy a file |
| `mv` (move, ren) | Move / rename a file |
| `find` | Find files whose name contains text |
| `grep` | Search text in a file or piped input |
| `wc` | Count lines / words / chars (file or pipe) |
| `head` | Show the first N lines (default 10) |
| `tail` | Show the last N lines (default 10) |
| `sort` | Sort lines (file or piped input) |
| `nl` | Number lines (file or piped input) |
| `edit` (ed) | Edit a file in a simple line editor |

### Tools

| Command | What it does |
|---------|--------------|
| `python` (py) | Drop into a real Python interpreter |
| `img2ascii` (ascii, img) | Convert an image into ASCII art |
| `calc` | Evaluate a math expression |
| `banner` | Print BIG block-letter text |
| `echo` | Print text |
| `rev` | Reverse text |
| `upper` | Uppercase text |
| `lower` | Lowercase text |
| `roll` (dice) | Roll dice, e.g. `roll 2d6` |
| `flip` | Flip a coin |
| `convert` (conv, unit) | Convert units (length / weight / temperature) |
| `todo` (task, tasks) | A simple saved to-do list |
| `morse` | Encode text to Morse, or decode `. -` back |
| `leet` (1337) | Translate text into l33tspeak |
| `rot13` | ROT13 cipher (run twice to undo) |
| `cypherize` (cypher, cipher) | Multi-layer cipher: Caesar → Atbash → Vigenère → leet. Prompts for a shift number, a key, and a sentence; `cypherize -d` reverses it |
| `bases` (base) | Show a number in dec / bin / oct / hex |
| `asciitable` (chars) | Print the printable ASCII table |

### System

| Command | What it does |
|---------|--------------|
| `help` (?) | Show commands, or help for one command |
| `man` (manual) | Show the full manual page for a command |
| `clear` (cls) | Clear the screen |
| `theme` (color) | Change the color theme |
| `sysinfo` (neofetch) | Show a stylized system-info panel |
| `history` | Show command history |
| `alias` | List or define a command alias (saved) |
| `unalias` | Remove an alias |
| `set` (setenv) | List or set an environment variable (saved) |
| `unset` | Remove an environment variable |
| `run` (batch, do) | Run a file of commands (batch script) |
| `update` (upgrade) | Update PHOSPHOR-OS from GitHub |
| `pkg` (package) | The (fake) package manager |
| `secrets` (secret) | Hints that the OS is hiding something |
| `scores` | Show your best game scores |
| `setname` (rename) | Change your username (saved) |
| `whoami` | Show the current user |
| `date` | Show the current date |
| `time` | Show the current time |
| `uptime` | Show how long this session has run |
| `ps` (proc, procs) | List running processes (PID, user, CPU, mem, state) |
| `top` (htop) | Live process monitor — load, memory, and a sorted process list |
| `kill` | Terminate a process by PID (`kill -9` to force; system daemons are protected) |
| `sound` (audio) | Toggle PC-speaker sound effects (`sound on/off/test`) |
| `beep` | Emit a beep at a given frequency (`beep 440 200`) |
| `play` (tune) | Play a built-in tune (`play list` to see them) |
| `dmesg` (syslog, log) | Show the kernel / system message log (`dmesg -c` clears) |
| `cron` (crontab) | Schedule recurring jobs (`cron add <seconds> <command>`, `cron rm <id>`) |
| `at` | Run a command once after a delay (`at 30 fortune`) |
| `ver` (about) | Show OS version / about |
| `save` | Save the virtual disk to the host |
| `load` | Reload the virtual disk from the host |
| `format` | Wipe the virtual disk (asks first) |
| `reboot` | Restart the simulator |
| `exit` (shutdown, quit) | Power off and leave |

### Users & permissions

| Command | What it does |
|---------|--------------|
| `login` (signin) | Log in as a user (asks for a password) |
| `logout` (signout) | Log out and return to the login prompt |
| `su` | Switch user (root if none given) |
| `sudo` | Run a single command as root |
| `passwd` (password) | Set or change a password |
| `useradd` (adduser) | Create a new user account (admin) |
| `userdel` (deluser) | Delete a user account (admin) |
| `users` (who) | List the user accounts |
| `id` | Show your user / group ids |
| `chmod` | Change a file's permission bits (e.g. `644`) |
| `chown` | Change a file's owner |

### Network

| Command | What it does |
|---------|--------------|
| `ipconfig` (ifconfig, ip) | Show network config, including your **real** public IP |
| `myip` (whatismyip, publicip) | Show your real public IP (VPN-aware) |
| `ping` | Ping a host on the (simulated) network |
| `nslookup` (dig, resolve) | Resolve a hostname to an address |
| `scan` (netscan, nmap) | Scan the local segment for live hosts |
| `netstat` (ports) | Show active network connections |
| `route` | Show the IP routing table |
| `wget` (curl, fetch) | Download a page from a network host |
| `telnet` (connect) | Open a session to a network host |
| `browse` (web, www, surf) | Browse the in-world web — follow numbered links, `b` back, `q` quit |
| `bbs` | Dial into the Night City BBS — read boards and post messages (they persist) |
| `oracle` | Consult the oracle on the deepnet — ask it anything |
| `quest` (journal) | Track the deepnet mystery — a solvable puzzle hidden across the network |

### Toys

| Command | What it does |
|---------|--------------|
| `matrix` | Digital rain effect |
| `hack` | A totally real hacking sequence ;) |
| `cowsay` | A cow says something wise |
| `fortune` | Print a random fortune |
| `glitch` | Render text with corrupted glitches |
| `8ball` (eightball) | Ask the magic 8-ball a question |
| `joke` | Tell a (bad) programmer joke |
| `rainbow` | Print text in rainbow colors |
| `slot` (slots) | Spin the slot machine |
| `fire` | A cozy ASCII campfire |
| `aquarium` (fish) | A little ASCII fish tank |
| `clock` | Show the time as a big ASCII clock |
| `screensaver` (saver) | Launch a fullscreen screensaver |

### Games

| Command | What it does |
|---------|--------------|
| `guess` | Guess-the-number game (1–100) |
| `rps` | Rock paper scissors, best of 3 |
| `hangman` | Classic hangman word game |
| `ttt` (tictactoe) | Tic-tac-toe versus the computer |
| `quiz` (trivia) | A quick 5-question trivia quiz |
| `wordle` (phosdle) | Guess the 5-letter word in 6 tries |
| `2048` | Slide and merge tiles to reach 2048 |
| `minesweeper` (mines) | Clear the field without hitting a mine |
| `blackjack` (21) | Beat the dealer to 21 without busting |
| `snake` | Steer the snake, eat food, grow, don't crash |
| `tetris` | Stack falling tetrominoes and clear lines |
| `solitaire` (klondike) | Klondike solitaire with a full deck |

---

## The shell

It behaves like a real shell, not just a command launcher:

- **Pipes** — `cat notes.txt | grep error | wc`
- **Redirection** — `cmd > file`, `cmd >> file` (append), `cmd < file`
- **Wildcards** — `ls *.txt`, `rm *.log`
- **Aliases** — `alias ll="ls"` (saved between sessions; `unalias` to remove)
- **Environment variables** — `set NAME=value`, then `echo $NAME` or `${NAME}`;
  built-ins include `$USER`, `$VERSION`, `$CWD`, `$THEME`, `$HOME`
- **Batch scripts** — `run script.txt` runs a file of commands line by line; an
  `autoexec.bat` at the root of the virtual disk runs automatically on boot
- **A line editor** — `edit <file>` opens a simple editor for a file
- **History** — recall with the Up/Down arrows, or list it with `history`
- **Tab completion** — completes command names and file names

---

## Users & permissions

The first time you open PHOSPHOR-OS it logs you straight in as **`root`** (the
superuser, no password) — there's nothing to type. The moment you set a password
on any account, a **login screen** appears at startup instead.

```
passwd                   give your account a password (this turns on the login screen)
users                    list accounts
useradd alice            create a user (then: passwd alice)
login alice              log in as someone
logout                   return to the login screen
su root                  become root again (root's prompt ends in #)
```

`root` (and any account you mark admin) has full access to everything.

Files have an **owner** and Unix-style permission bits. `ls -l` shows them:

```
ls -l                    long listing with mode + owner
chmod 600 secret.txt     change permission bits
chown alice secret.txt   change owner (admin)
```

Some things are owned by `root` and protected — try `cat /etc/shadow` as a normal
user and you'll be denied. Prefix a command with **`sudo`** to run it as root:

```
sudo cat /etc/shadow
```

Your home directory is `~` (e.g. `/home/alice`); `cd` with no argument takes you
there. Accounts and passwords are saved between sessions.

## The network

PHOSPHOR-OS has its own little world to explore. Most of it is a **simulated**
network — a handful of mysterious hosts you can discover and poke at:

```
scan                          list the hosts that are out there
ping oracle.deepnet           ping a host (with realistic latency)
nslookup bbs.nightcity.bbs    resolve a hostname
netstat                       see "active" connections
route                         see the routing table
wget archive.retronet.org     read what a host is serving (--save <file> to keep it)
telnet the-angle.eye          open a session... if you dare
```

Two commands, though, report your **real** machine:

- `ipconfig` shows your actual LAN address, MAC, gateway, and your real public IP.
- `myip` shows just the public IP.

The public address is whatever your connection actually presents to the internet,
so if you're on a **VPN** it shows the VPN's exit IP instead of your own. These
two reach out to the internet to learn the public address (with a short timeout
and a graceful "offline" fallback); **everything else on the network works
offline.**

---

## Screensavers

`screensaver` opens a **dedicated fullscreen window** with a continuous animation.
**Press any key (or click)** to close it and drop straight back to your terminal,
exactly where you left off.

```
screensaver            launch a random one
screensaver fire       launch a specific one
screensaver list       show what's available
```

Available savers: `matrix`, `starfield`, `life` (Conway's Game of Life),
`bounce`, `fireworks`, `fire`, `plasma`, `rain`, `wave`, and `worms`. The window sizes itself to your screen and
re-fits if you resize it. (In a plain terminal with `--console`, screensavers run
inline and wake on Ctrl-C instead.)

---

## Games & toys

Nine games keep score across sessions (`scores` shows your bests): the classics
plus `2048`, `minesweeper`, `blackjack`, `snake`, `tetris`, and `solitaire`. The toys are pure atmosphere —
`matrix` rain, a `fire`, an `aquarium`, a big ASCII `clock`, `cowsay`, `fortune`,
the `slot` machine, `rainbow` text, and a fake `hack` sequence for showing off.

---

## Built-in Python

`python` drops you into a real Python interpreter running inside the OS, with the
live system exposed as the variable `os_sim`:

```
>>> os_sim.VERSION
>>> os_sim.theme_name
>>> 2 ** 16
```

Type `exit()` (or send EOF) to return to the shell. It works the same in the GUI,
in a console, and in the packaged exe.

---

## Image to ASCII

`img2ascii <path>` turns an image into ASCII art. Options:

```
img2ascii ~/pic.jpg 100 --color --save art.txt
```

- a width (columns), e.g. `100`
- `--color` for ANSI color
- `--invert` to flip light/dark
- `--save <file>` to write the result into the virtual disk

This is the one command that needs **Pillow** (`pip install pillow`).

---

## Themes

Six color schemes: `phosphor` (green), `amber`, `ice`, `blood`, `plasma`, `mono`.
Switch with `theme <name>` — your choice is remembered between sessions.

```
theme amber
```

---

## The virtual disk & your data

PHOSPHOR-OS has a virtual filesystem that lives in a JSON file on your real
machine, so anything you create persists between sessions.

- `save` writes the disk now; `load` reloads it; `format` wipes it (after asking).
- Your settings (theme, username), aliases, environment variables, to-do list,
  installed fake packages, and high scores are saved too.

On Windows these live under `%APPDATA%\PhosphorOS\`; on Linux/macOS under
`~/.local/share/phosphor-os/`. Deleting that folder resets everything to a fresh
install.

---

## Keyboard & tips

- **Up / Down** — walk through command history
- **Tab** — complete commands and file names
- **Ctrl+C / Ctrl+A / Ctrl+V** — copy / select-all / paste in the terminal window
  (right-click also opens a menu)
- The window's font scales to its size — resize it and the text re-fits
- Any key closes a running screensaver

---

## Secrets

The OS is hiding a few things. `secrets` will nudge you in the right direction.
Some commands do more than they admit, some files want to be found, and there's
something on the network that probably shouldn't be. Go looking.

---

## License

Released under the MIT License — see the `LICENSE` file.
