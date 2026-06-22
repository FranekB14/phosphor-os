"""The Tkinter terminal window and the floating easter-egg eye windows."""

import os
import sys
import re
import io
import json
import time
import random
import shlex
import shutil
import fnmatch
import zipfile
import tempfile
import datetime
import textwrap
import platform
import subprocess
import urllib.request
import urllib.error

from . import runtime
from .constants import *
from .helpers import *
from .shell import Phosphor, main


def launch_gui():
    """Run PHOSPHOR-OS inside a terminal-styled GUI window."""
    import tkinter as tk
    import tkinter.font as tkfont
    import threading
    import queue
    import re

    runtime.INTERACTIVE = True          # the GUI always animates
    runtime.GUI_ACTIVE = True
    EOF = object()

    FONT = ("Consolas", 13) if os.name == "nt" else ("DejaVu Sans Mono", 12)
    ANSI = re.compile(r'\x1b\][^\x07]*\x07|\x1b\[[0-9;]*[A-Za-z]|\r')

    class Emu:
        """Minimal ANSI terminal emulator on top of a tk.Text widget."""
        def __init__(self, text):
            self.text = text
            self.cur_tag = "fg_default"
            self._tags = set()

        def _color_tag(self, r, g, b):
            name = f"c{r}_{g}_{b}"
            if name not in self._tags:
                self.text.tag_configure(name, foreground=f"#{r:02x}{g:02x}{b:02x}")
                self._tags.add(name)
            return name

        def _sgr(self, params):
            codes = params.split(";") if params else ["0"]
            if codes[:2] == ["38", "2"] and len(codes) >= 5:
                try:
                    self.cur_tag = self._color_tag(int(codes[2]), int(codes[3]), int(codes[4]))
                    return
                except ValueError:
                    pass
            if not params or "0" in codes:
                self.cur_tag = "fg_default"

        def _control(self, tok):
            if tok == "\r":
                self.text.delete("end-1c linestart", "end-1c")
                return
            if tok.startswith("\x1b]"):
                return                                  # OSC (title) -> ignore
            letter, params = tok[-1], tok[2:-1]
            if letter == "m":
                self._sgr(params)
            elif letter == "J":
                self.text.delete("1.0", "end")          # clear screen
            elif letter == "A":                          # cursor up N -> redraw zone
                n = int(params) if params.isdigit() else 1
                last = int(self.text.index("end-1c").split(".")[0])
                start = max(1, last - n)
                self.text.delete(f"{start}.0", "end-1c")
            # H (home), K, B/C/D etc. are no-ops in this append model

        def feed(self, s):
            try:
                pos = 0
                for m in ANSI.finditer(s):
                    if m.start() > pos:
                        self.text.insert("end-1c", s[pos:m.start()], self.cur_tag)
                    self._control(m.group())
                    pos = m.end()
                if pos < len(s):
                    self.text.insert("end-1c", s[pos:], self.cur_tag)
            except Exception:
                pass
            # bound memory: keep last ~3000 lines
            try:
                total = int(self.text.index("end-1c").split(".")[0])
                if total > 3000:
                    self.text.delete("1.0", f"{total - 3000}.0")
            except Exception:
                pass
            self.text.see("end")

    class VScroll(tk.Canvas):
        """A self-drawn vertical scrollbar so colors are honored on every OS
        (the native tk.Scrollbar ignores dark colors on Windows)."""
        TROUGH = "#161616"          # dark gray channel
        THUMB = "#555555"           # dark-gray grip
        THUMB_HOVER = "#6e6e6e"

        def __init__(self, parent, target):
            super().__init__(parent, width=13, highlightthickness=0, bd=0,
                             bg=self.TROUGH, takefocus=0)
            self.target = target
            self.first, self.last = 0.0, 1.0
            self.thumb = self.create_rectangle(0, 0, 0, 0, fill=self.THUMB, outline="")
            self.bind("<Configure>", lambda e: self._redraw())
            self.bind("<Button-1>", self._on_press)
            self.bind("<B1-Motion>", self._on_drag)
            self.tag_bind(self.thumb, "<Enter>", lambda e: self.itemconfig(self.thumb, fill=self.THUMB_HOVER))
            self.tag_bind(self.thumb, "<Leave>", lambda e: self.itemconfig(self.thumb, fill=self.THUMB))

        def set(self, first, last):                 # called by Text.yscrollcommand
            self.first, self.last = float(first), float(last)
            self._redraw()

        def _redraw(self):
            h = self.winfo_height() or 1
            w = self.winfo_width() or 13
            if self.last - self.first >= 0.999:     # everything fits -> hide grip
                self.coords(self.thumb, 0, 0, 0, 0)
                return
            y0 = self.first * h
            y1 = self.last * h
            if y1 - y0 < 20:                         # keep grip grabbable
                y1 = y0 + 20
            self.coords(self.thumb, 3, y0 + 1, w - 3, y1 - 1)

        def _on_press(self, e):
            self._scroll_to(e.y)

        def _on_drag(self, e):
            self._scroll_to(e.y)

        def _scroll_to(self, y):
            h = self.winfo_height() or 1
            span = max(0.0, self.last - self.first)
            frac = (y / h) - span / 2                # center grip under cursor
            self.target.yview_moveto(max(0.0, min(1.0, frac)))

    class App:
        def __init__(self):
            self.root = tk.Tk()
            self.root.title("PHOSPHOR-OS — CRT TERMINAL")
            BG = "#0c0c0c"                      # Windows console default (RGB 12,12,12)
            self.root.configure(bg=BG)
            self.out_q = queue.Queue()
            self.in_q = queue.Queue()
            self.awaiting = False
            self.input_start = "1.0"
            self.cur = ""
            self.hist_idx = None
            self.closed = False
            self._saver_top = None     # the screensaver window, when one is open

            frame = tk.Frame(self.root, bg=BG, borderwidth=0, highlightthickness=0)
            frame.pack(fill="both", expand=True)
            # a Font object we can resize on the fly as the window grows/shrinks
            self.font = tkfont.Font(family=FONT[0], size=FONT[1])
            self.base_size = FONT[1]
            self.text = tk.Text(frame, bg=BG, fg="#7CFF8A",
                                 insertbackground="#7CFF8A", font=self.font,
                                 borderwidth=0, highlightthickness=0,
                                 padx=6, pady=4, wrap="char", undo=False,
                                 selectbackground="#264f2c", selectforeground="#ffffff")
            self.text.tag_configure("fg_default", foreground="#7CFF8A")
            self.text.tag_configure("input", foreground="#CFFFE0")
            # custom dark-gray scrollbar (native one ignores colors on Windows)
            sb = VScroll(frame, self.text)
            self.text.configure(yscrollcommand=sb.set)
            sb.pack(side="right", fill="y")
            self.text.pack(side="left", fill="both", expand=True)
            self.text.focus_set()
            self.emu = Emu(self.text)

            # intercept all typing; we manage the buffer ourselves
            self.text.bind("<Key>", self._on_key)
            self.text.bind("<Return>", self._on_return)
            self.text.bind("<BackSpace>", self._on_back)
            self.text.bind("<Up>", lambda e: self._history(-1) or "break")
            self.text.bind("<Down>", lambda e: self._history(1) or "break")
            self.text.bind("<Tab>", lambda e: self._complete() or "break")
            # --- make the terminal text selectable & copyable ---
            # (these patterns are more specific than <Key>, so they win over the
            #  input interceptor and reach the clipboard.)
            for seq in ("<Control-c>", "<Control-C>", "<Command-c>", "<Control-Insert>"):
                self.text.bind(seq, self._copy_sel)
            for seq in ("<Control-a>", "<Control-A>"):
                self.text.bind(seq, self._select_all)
            for seq in ("<Control-v>", "<Control-V>", "<Command-v>", "<Shift-Insert>"):
                self.text.bind(seq, self._paste_input)
            self._menu = tk.Menu(self.text, tearoff=0, bg="#1b1b1b", fg="#dcdcdc",
                                 activebackground="#2a4a30", activeforeground="#ffffff",
                                 borderwidth=0)
            self._menu.add_command(label="Copy", command=self._copy_sel)
            self._menu.add_command(label="Paste", command=self._paste_input)
            self._menu.add_separator()
            self._menu.add_command(label="Select All", command=self._select_all)
            self.text.bind("<Button-3>", self._popup_menu)
            self.root.protocol("WM_DELETE_WINDOW", self._on_close)
            self.root.bind("<Configure>", self._on_resize)

            # geometry
            self.root.geometry("860x540")
            self._dark_titlebar()
            # size the font to the *actual* window size once it's realized
            self.root.after(60, self._apply_font)

            # start shell thread
            self.shell = Phosphor(input_fn=self._readline)
            self.shell._gui_saver = self._launch_saver   # screensaver opens its own window
            self.shell._gui_bell = lambda: self.root.after(0, self.root.bell)  # audible fallback
            self._stdout_orig = sys.stdout
            sys.stdout = _GuiStdout(self.out_q)
            self.thread = threading.Thread(target=self._run_shell, daemon=True)
            self.thread.start()
            self.root.after(15, self._drain)

            # optional headless self-test (used for automated verification)
            self._test_cmds = os.environ.get("PHOSPHOR_GUI_TEST")
            if self._test_cmds:
                self._test_queue = [c for c in self._test_cmds.split(";;") if c]
                self.root.after(1800, self._feed_next_test)

        # ----- headless test helpers -----
        def _feed_next_test(self):
            if not self._test_queue:
                self.root.after(900, self._dump_and_quit)
                return
            if self.awaiting:
                cmd = self._test_queue.pop(0)
                self.cur = cmd
                self._render_input()
                self.text.insert("end-1c", "\n")
                self.awaiting = False
                self.in_q.put(cmd)
                self.root.after(450, self._feed_next_test)
            else:
                self.root.after(120, self._feed_next_test)

        def _dump_and_quit(self):
            try:
                with open(os.environ.get("PHOSPHOR_GUI_DUMP", "/tmp/gui_dump.txt"),
                          "w", encoding="utf-8") as f:
                    f.write(self.text.get("1.0", "end"))
                    f.write("\n--- TAGS ---\n" + " ".join(sorted(self.emu._tags)))
            except Exception:
                pass
            self._on_close()

        # ----- responsive font: scale text with window size -----
        TARGET_COLS = 82            # keep ~this many columns filling the width
        MIN_SIZE = 7
        MAX_SIZE = 18               # cap so a maximized window isn't huge

        def _font_size_for(self, width):
            avail = width - 29       # minus scrollbar + side padding
            if avail < 20:
                return self.font.cget("size")
            cur_w = self.font.measure("M" * self.TARGET_COLS) or 1
            size = int(round(self.font.cget("size") * avail / cur_w))
            return max(self.MIN_SIZE, min(self.MAX_SIZE, size))

        def _apply_font(self):
            size = self._font_size_for(self.root.winfo_width())
            if size != self.font.cget("size"):
                self.font.configure(size=size)
            self._report_term_size()

        def _report_term_size(self):
            """Tell the shell the current window size in characters, so
            full-screen screensavers can fill the window."""
            try:
                cw = self.font.measure("M") or 8
                ch = self.font.metrics("linespace") or 16
                pw = self.text.winfo_width()
                ph = self.text.winfo_height()
                if pw > 1 and ph > 1 and self.shell is not None:
                    cols = max(24, (pw - 14) // cw)
                    rows = max(8, (ph - 8) // ch)
                    self.shell.term_size = (cols, rows)
            except Exception:
                pass

        def _on_resize(self, e):
            if e.widget is self.root:
                self._apply_font()

        # ----- shell thread -----
        def _dark_titlebar(self):
            """On Windows 10/11, paint the native title bar dark (like cmd)."""
            if os.name != "nt":
                return
            try:
                import ctypes
                self.root.update_idletasks()
                hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
                val = ctypes.c_int(1)
                # DWMWA_USE_IMMERSIVE_DARK_MODE = 20 (newer) / 19 (older builds)
                for attr in (20, 19):
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(
                        hwnd, attr, ctypes.byref(val), ctypes.sizeof(val))
            except Exception:
                pass

        def _run_shell(self):
            try:
                while True:
                    self.shell.run()
                    if not self.shell.reboot_requested:
                        break
                    self.shell = Phosphor(input_fn=self._readline)
                    self.shell._gui_saver = self._launch_saver
            except Exception:
                pass
            finally:
                self.out_q.put(("close", None))

        def _readline(self, prompt=""):
            if self.closed:
                raise EOFError
            self.out_q.put(("prompt", prompt))
            line = self.in_q.get()
            if line is EOF:
                raise EOFError
            return line

        # ----- Tk thread: drain output queue -----
        def _drain(self):
            try:
                while True:
                    kind, payload = self.out_q.get_nowait()
                    if kind == "out":
                        self.emu.feed(payload)
                    elif kind == "prompt":
                        self.emu.feed(payload)
                        self.input_start = self.text.index("end-1c")
                        self.cur = ""
                        self.hist_idx = None
                        self.awaiting = True
                    elif kind == "close":
                        self._shutdown()
                        return
            except queue.Empty:
                pass
            if not self.closed:
                self.root.after(15, self._drain)

        # ----- screensaver: runs in its own fullscreen window (a Toplevel) -----
        SAVER_CELL = 22            # pixel size of each animation block

        def _launch_saver(self, name):
            """Called from the shell thread -> hop to the main (Tk) thread."""
            try:
                self.root.after(0, lambda: self._open_saver(name))
            except Exception:
                pass

        def _open_saver(self, name):
            if getattr(self, "_saver_top", None):
                return                              # one at a time
            render = getattr(self.shell, "_saver_" + name, None)
            if render is None:
                return
            self._saver_render = render
            self._saver_state = {}
            self._saver_dims = (0, 0)
            self._saver_items = []
            self._saver_prev = []
            self._saver_after = None
            self._saver_font = tkfont.Font(family=FONT[0], size=14)
            top = tk.Toplevel(self.root)
            top.title("PHOSPHOR-OS — screensaver")
            top.configure(bg="black")
            try:
                top.attributes("-fullscreen", True)
            except Exception:
                try:
                    top.state("zoomed")
                except Exception:
                    pass
            cv = tk.Canvas(top, bg="black", highlightthickness=0, bd=0)
            cv.pack(fill="both", expand=True)
            self._saver_top = top
            self._saver_canvas = cv
            for seq in ("<Key>", "<Button-1>", "<Button-2>", "<Button-3>"):
                top.bind(seq, self._close_saver)    # any key or click wakes it
            top.protocol("WM_DELETE_WINDOW", self._close_saver)
            top.update_idletasks()
            top.lift(); top.focus_force(); cv.focus_set()
            self._build_saver_grid()
            self._tick_saver()

        def _saver_grid_size(self):
            cv = self._saver_canvas
            pw = cv.winfo_width() or self._saver_top.winfo_screenwidth()
            ph = cv.winfo_height() or self._saver_top.winfo_screenheight()
            cell = self.SAVER_CELL
            W = max(20, min(int(pw) // cell, 110))
            H = max(10, min(int(ph) // cell, 64))
            return W, H, pw, ph

        def _build_saver_grid(self):
            cv = self._saver_canvas
            W, H, pw, ph = self._saver_grid_size()
            cv.delete("all")
            self._saver_dims = (W, H)
            self._saver_items = [[None] * W for _ in range(H)]
            self._saver_prev = [[("", "") for _ in range(W)] for _ in range(H)]
            cw = pw / W; chh = ph / H
            self._saver_font.configure(size=max(8, int(chh * 0.82)))
            for y in range(H):
                iy = self._saver_items[y]; cy = y * chh + chh / 2
                for x in range(W):
                    iy[x] = cv.create_text(x * cw + cw / 2, cy, text="",
                                           fill="#000000", font=self._saver_font)
            self._saver_state = {}                  # restart the animation at the new size

        def _tick_saver(self):
            top = getattr(self, "_saver_top", None)
            if not top:
                return
            cv = self._saver_canvas
            if self._saver_grid_size()[:2] != self._saver_dims:   # resized -> rebuild
                self._build_saver_grid()
            W, H = self._saver_dims
            try:
                chars, colors = self._saver_render(self._saver_state, W, H)
            except Exception:
                chars = [[" "] * W for _ in range(H)]
                colors = [[None] * W for _ in range(H)]
            items = self._saver_items; prev = self._saver_prev; cfg = cv.itemconfigure
            for y in range(H):
                crow = chars[y]; colrow = colors[y]; prow = prev[y]; irow = items[y]
                for x in range(W):
                    col = colrow[x]
                    cell = (crow[x], "#%02x%02x%02x" % col) if col else ("", "")
                    if cell != prow[x]:             # only touch cells that changed
                        if cell[0]:
                            cfg(irow[x], text=cell[0], fill=cell[1])
                        else:
                            cfg(irow[x], text="")
                        prow[x] = cell
            cells = W * H
            delay = 45 if cells < 1800 else 70 if cells < 3200 else 100
            self._saver_after = top.after(delay, self._tick_saver)

        def _close_saver(self, e=None):
            top = getattr(self, "_saver_top", None)
            if not top:
                return
            self._saver_top = None
            try:
                if self._saver_after:
                    top.after_cancel(self._saver_after)
            except Exception:
                pass
            try:
                top.destroy()
            except Exception:
                pass
            try:                                    # hand focus back to the terminal
                self.root.lift(); self.root.focus_force(); self.text.focus_set()
            except Exception:
                pass

        # ----- input handling -----
        def _render_input(self):
            self.text.delete(self.input_start, "end-1c")
            self.text.insert("end-1c", self.cur, "input")
            self.text.see("end")

        def _wake_saver(self):
            """If a screensaver is running, any keystroke wakes it."""
            if getattr(self.shell, "_screensaver", False):
                self.shell._interrupt = True
                return True
            return False

        def _on_key(self, e):
            if self._wake_saver():
                return "break"
            if not self.awaiting:
                return "break"
            if e.char and e.char.isprintable() and len(e.char) == 1:
                self.cur += e.char
                self._render_input()
            return "break"

        # ----- clipboard: select / copy / paste -----
        def _copy_sel(self, e=None):
            try:
                sel = self.text.get("sel.first", "sel.last")
            except tk.TclError:
                sel = ""
            if sel:
                self.root.clipboard_clear()
                self.root.clipboard_append(sel)
            return "break"

        def _select_all(self, e=None):
            self.text.tag_remove("sel", "1.0", "end")
            self.text.tag_add("sel", "1.0", "end-1c")
            return "break"

        def _paste_input(self, e=None):
            """Paste clipboard text into the current input line."""
            if not self.awaiting:
                return "break"
            try:
                data = self.root.clipboard_get()
            except tk.TclError:
                data = ""
            if data:
                # only the first line goes onto the prompt; strip control chars
                first = data.replace("\r", "\n").split("\n")[0]
                self.cur += "".join(ch for ch in first if ch.isprintable())
                self._render_input()
            return "break"

        def _popup_menu(self, e):
            try:
                self._menu.tk_popup(e.x_root, e.y_root)
            finally:
                self._menu.grab_release()
            return "break"

        def _on_back(self, e):
            if self._wake_saver():
                return "break"
            if self.awaiting and self.cur:
                self.cur = self.cur[:-1]
                self._render_input()
            return "break"

        def _on_return(self, e):
            if self._wake_saver():
                return "break"
            if not self.awaiting:
                return "break"
            line = self.cur
            self.text.insert("end-1c", "\n")
            self.awaiting = False
            self.in_q.put(line)
            return "break"

        def _history(self, direction):
            if self._wake_saver():
                return True
            if not self.awaiting:
                return True
            h = self.shell.history
            if not h:
                return True
            if self.hist_idx is None:
                self.hist_idx = len(h)
            self.hist_idx = max(0, min(len(h), self.hist_idx + direction))
            self.cur = h[self.hist_idx] if self.hist_idx < len(h) else ""
            self._render_input()
            return True

        def _complete(self):
            if self._wake_saver():
                return True
            if not self.awaiting:
                return True
            tokens = self.cur.split(" ")
            if len(tokens) <= 1:
                pool = sorted(set(self.shell.commands))
                prefix = tokens[0]
            else:
                node = self.shell._get_node(self.shell.cwd)
                pool = sorted(node["children"]) if node and node["type"] == "dir" else []
                prefix = tokens[-1]
            matches = [p for p in pool if p.startswith(prefix)]
            if not matches:
                return True
            common = os.path.commonprefix(matches)
            if len(tokens) <= 1:
                tokens = [common] + ([""] if len(matches) == 1 else [])
                self.cur = (common + " ") if len(matches) == 1 else common
            else:
                tokens[-1] = common
                self.cur = " ".join(tokens)
            self._render_input()
            return True

        # ----- shutdown -----
        def _on_close(self):
            self.closed = True
            self.in_q.put(EOF)                      # unblock any pending readline
            self.shell.running = False
            self.root.after(120, self._shutdown)

        def _shutdown(self):
            self.closed = True
            try:
                sys.stdout = self._stdout_orig
            except Exception:
                pass
            try:
                self.root.destroy()
            except Exception:
                pass

        def run(self):
            self.root.mainloop()
            sys.stdout = self._stdout_orig

    class _GuiStdout:
        """File-like stdout that funnels shell output to the GUI queue."""
        def __init__(self, q):
            self.q = q
        def write(self, s):
            if s:
                self.q.put(("out", s))
            return len(s)
        def flush(self):
            pass
        def isatty(self):
            return True

    App().run()


def run_eye_gui(level):
    """A small, borderless, randomly-placed window with the entity animation."""
    try:
        import tkinter as tk
    except Exception:
        run_cosmic_eye(level)                       # console fallback
        return
    level = max(1, min(5, level))
    base = _EYE_COLOR[level]
    eyes = _EYE_FRAMES[level]
    texts = _EYE_TEXT[level]
    glitch = "▓▒░#@%&*/\\|<>≈∴×"

    root = tk.Tk()
    root.overrideredirect(True)                     # borderless, floating
    root.configure(bg="#020202")
    try:
        root.attributes("-topmost", True)
    except Exception:
        pass
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    w, h = 230, 250
    x, y = random.randint(0, max(0, sw - w)), random.randint(0, max(0, sh - h))
    root.geometry(f"{w}x{h}+{x}+{y}")
    txt = tk.Text(root, bg="#020202", fg="#%02x%02x%02x" % base, font=("DejaVu Sans Mono", 11),
                  borderwidth=0, highlightthickness=0, padx=6, pady=6, wrap="none")
    txt.pack(fill="both", expand=True)
    root.bind("<Button-1>", lambda e: root.destroy())   # click to banish
    root.bind("<Escape>", lambda e: root.destroy())

    state = {"f": 0}

    def color():
        if level >= 4 and random.random() < 0.3:
            return "#%02x%02x%02x" % (255, random.randint(0, 60), random.randint(0, 80))
        return "#%02x%02x%02x" % base

    def frame():
        if state["f"] >= 130:
            root.destroy()
            return
        eye = eyes[state["f"] % len(eyes)]
        rows = [ln.replace("###", eye).center(18) for ln in _ENTITY[level]]
        out = []
        for ln in rows:
            chars = list(ln)
            for i, ch in enumerate(chars):
                if ch != " " and random.random() < 0.025 * level:
                    chars[i] = random.choice(glitch)
            out.append("".join(chars))
        line = random.choice(texts)
        if level >= 4:
            line = "".join(random.choice(glitch) if (c != " " and random.random() < 0.12) else c
                           for c in line)
        txt.configure(fg=color())
        txt.delete("1.0", "end")
        txt.insert("end", "\n".join(out) + "\n\n " + line[:22])
        state["f"] += 1
        root.after(max(60, 150 - level * 18), frame)

    frame()
    try:
        root.mainloop()
    except Exception:
        pass
