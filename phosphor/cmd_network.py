"""NetworkMixin: the `network` command group."""

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


class NetworkMixin:
    NET_HOSTS = {
        "gateway.phosphor.net": ("10.0.0.1",      "Local gateway — the only way out."),
        "archive.retronet.org": ("198.51.100.7",  "A dusty file archive from the old net."),
        "bbs.nightcity.bbs":    ("203.0.113.42",  "An after-hours bulletin board. Still up, somehow."),
        "oracle.deepnet":       ("198.51.100.66", "It answers questions. It asks more."),
        "void.null":            ("127.0.0.66",    "There is nothing here. Keep looking."),
        "the-angle.eye":        ("0.0.0.0",       "??? — this should not resolve."),
    }

    NET_PAGES = {
        "gateway.phosphor.net":
            "PHOSPHOR GATEWAY v3\n"
            "  routes: 6 known hosts\n"
            "  uplink: ESTABLISHED (origin unknown)\n"
            "  notice: do not query the-angle.eye",
        "archive.retronet.org":
            "== RETRONET FILE ARCHIVE ==\n"
            "  /warez/ ........ (rotted)\n"
            "  /demos/ ........ 4 files\n"
            "  /readme.txt .... 'we were here first. you are late.'",
        "bbs.nightcity.bbs":
            "*** NIGHT CITY BBS — 2400 baud ***\n"
            "  [M]essages  [F]iles  [D]oor games  [G]oodbye\n"
            "  last caller: you, 11 years ago. welcome back.",
        "oracle.deepnet":
            "the oracle is listening.\n"
            "  ask, and the line will answer.\n"
            "  (it already knows what you typed.)",
        "void.null":
            " ",
    }

    NET_BANNERS = {
        "gateway.phosphor.net": "PHOSPHOR-OS gateway. Authorized phantoms only.",
        "archive.retronet.org": "RETRONET archive login:  (anonymous accepted)\nwelcome, stranger.",
        "bbs.nightcity.bbs":    "Connected to NIGHT CITY BBS.\nThe sysop logged off in 1996 and never came back.",
        "oracle.deepnet":       "ORACLE> you have one question. choose it carefully.",
        "void.null":            "(the connection opens onto nothing)",
    }

    def _local_ip(self):
        """The machine's LAN address. Uses a UDP socket route lookup — no
        packets are actually sent."""
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
            finally:
                s.close()
        except Exception:
            try:
                return socket.gethostbyname(socket.gethostname())
            except Exception:
                return "127.0.0.1"

    def _public_ip(self):
        """The machine's REAL outward-facing IP — i.e. the VPN's exit address
        when a VPN is connected. Returns None if offline."""
        import urllib.request
        for url in ("https://api.ipify.org", "https://ifconfig.me/ip",
                    "https://icanhazip.com", "https://ipinfo.io/ip"):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "PHOSPHOR-OS"})
                with urllib.request.urlopen(req, timeout=4) as r:
                    ip = r.read().decode("utf-8", "replace").strip()
                if ip and len(ip) <= 45 and all(c in "0123456789abcdefABCDEF.:" for c in ip):
                    return ip
            except Exception:
                continue
        return None

    def _fake_mac(self):
        import hashlib, socket
        h = hashlib.md5(socket.gethostname().encode()).hexdigest()[:12].upper()
        return ":".join(h[i:i + 2] for i in range(0, 12, 2))

    def _resolve_host(self, host):
        host = host.lower()
        if host in self.NET_HOSTS:
            return self.NET_HOSTS[host][0]
        import hashlib
        h = hashlib.md5(host.encode()).digest()
        return f"{(h[0] % 223) + 11}.{h[1]}.{h[2]}.{(h[3] % 254) + 1}"

    def cmd_ipconfig(self, args=None):
        import socket
        host = socket.gethostname()
        lan = self._local_ip()
        gw = (lan.rsplit(".", 1)[0] + ".1") if lan.count(".") == 3 else "10.0.0.1"
        self.p("  PHOSPHOR-OS  Network Configuration", "accent")
        self.p("  " + "─" * 50, "dim")
        self.p(f"   Host Name . . . . . . . . : {host}", "text")
        self.p(f"   Adapter . . . . . . . . . : PHOSPHOR Virtual NIC", "text")
        self.p(f"   Physical Address  . . . . : {self._fake_mac()}", "text")
        self.p(f"   IPv4 Address (LAN). . . . : {lan}", "text")
        self.p(f"   Subnet Mask . . . . . . . : 255.255.255.0", "text")
        self.p(f"   Default Gateway . . . . . : {gw}", "text")
        self.p("   querying public address . . .", "dim")
        pub = self._public_ip()
        if pub:
            self.p(f"   Public Address  . . . . . : {pub}", "accent")
            self.p("   (your real outward-facing IP — your VPN's exit IP if one is active)", "dim")
        else:
            self.p("   Public Address  . . . . . : unreachable (offline?)", "warn")

    def cmd_myip(self, args=None):
        self.p("  querying your public IP address...", "dim")
        pub = self._public_ip()
        if pub:
            self.p(f"  your public IP is  {pub}", "accent")
            self.p("  (this reflects your VPN's exit IP when a VPN is connected)", "dim")
        else:
            self.p("  could not reach the network — are you online?", "warn")

    def cmd_ping(self, args=None):
        args = args or []
        if not args:
            self.p("usage: ping <host>", "warn"); return
        host = args[0].lower()
        ip = self._resolve_host(host)
        flaky = host in ("the-angle.eye", "void.null")
        self.p(f"  PING {host} ({ip}): 56 data bytes", "accent")
        times, lost = [], 0
        for seq in range(4):
            if runtime.INTERACTIVE:
                time.sleep(0.3)
            if random.random() < (0.6 if flaky else 0.04):
                self.p(f"    icmp_seq={seq} : request timed out", "warn"); lost += 1
            else:
                ms = round(random.uniform(6, 90), 1)
                times.append(ms)
                self.p(f"    64 bytes from {ip}: icmp_seq={seq} ttl=64 time={ms} ms", "text")
        self.p(f"  --- {host} ping statistics ---", "accent")
        self.p(f"  4 packets transmitted, {4 - lost} received, {lost * 25}% packet loss", "text")
        if times:
            self.p(f"  rtt min/avg/max = {min(times)}/"
                   f"{round(sum(times) / len(times), 1)}/{max(times)} ms", "dim")
        if flaky and lost == 4:
            self.p("  the host is there. it simply chose not to answer.", "err")

    def cmd_nslookup(self, args=None):
        args = args or []
        if not args:
            self.p("usage: nslookup <host>", "warn"); return
        host = args[0].lower()
        self.p("  Server:   gateway.phosphor.net", "dim")
        self.p("  Address:  10.0.0.1#53", "dim")
        self.p("", "text")
        if host == "the-angle.eye":
            self.p(f"  Name:     {host}", "text")
            self.p("  Address:  it is already inside the resolver", "err"); return
        self.p(f"  Name:     {host}", "text")
        self.p(f"  Address:  {self._resolve_host(host)}", "accent")

    def cmd_scan(self, args=None):
        self.p("  scanning local segment 10.0.0.0/24 for live hosts...", "dim")
        for name, (ip, desc) in self.NET_HOSTS.items():
            if runtime.INTERACTIVE:
                time.sleep(0.12)
            state = "??" if name == "the-angle.eye" else "up"
            self.p(f"    {ip:<16} {name:<24} [{state}]  {desc}", "text")
        self.p(f"  {len(self.NET_HOSTS)} hosts responded.", "accent")
        self.p("  try:  ping <host>  |  wget <host>  |  telnet <host>", "dim")

    def cmd_netstat(self, args=None):
        lan = self._local_ip()
        self.p("  Active Connections", "accent")
        self.p("  Proto  Local Address           Foreign Address          State", "dim")
        rows = [
            ("TCP", f"{lan}:51713", "gateway.phosphor.net:443", "ESTABLISHED"),
            ("TCP", f"{lan}:51714", "archive.retronet.org:21",  "TIME_WAIT"),
            ("TCP", f"{lan}:51720", "oracle.deepnet:6667",      "ESTABLISHED"),
            ("UDP", f"{lan}:137",   "*:*",                      ""),
            ("TCP", "127.0.0.66:0", "the-angle.eye:?",          "WATCHING"),
        ]
        for p, l, f, s in rows:
            self.p(f"  {p:<5}  {l:<23} {f:<24} {s}", "text")

    def cmd_route(self, args=None):
        lan = self._local_ip()
        gw = (lan.rsplit(".", 1)[0] + ".1") if lan.count(".") == 3 else "10.0.0.1"
        self.p("  Kernel IP routing table", "accent")
        self.p("  Destination      Gateway          Genmask          Iface", "dim")
        self.p(f"  0.0.0.0          {gw:<16} 0.0.0.0          eth0", "text")
        self.p(f"  10.0.0.0         0.0.0.0          255.255.255.0    eth0", "text")
        self.p(f"  127.0.0.0        0.0.0.0          255.0.0.0        lo", "text")
        self.p("  0.0.0.0          the-angle.eye    0.0.0.0          ????", "err")

    def cmd_wget(self, args=None):
        args = args or []
        if not args:
            self.p("usage: wget <host> [--save <file>]", "warn"); return
        host = args[0].lower().replace("http://", "").replace("https://", "").split("/")[0]
        self.p(f"  connecting to {host} ({self._resolve_host(host)})...", "dim")
        if runtime.INTERACTIVE:
            time.sleep(0.4)
        page = self.NET_PAGES.get(host)
        if page is None:
            self.p(f"  404 — nothing served at {host}", "warn")
            self.p("  (run 'scan' to see which hosts are out there)", "dim"); return
        self.p(f"  200 OK — {len(page)} bytes received", "accent")
        if "--save" in args:
            i = args.index("--save")
            fname = args[i + 1] if i + 1 < len(args) else "page.txt"
            parent, name = self._parent_and_name(fname)
            if parent is None or parent["type"] != "dir":
                self.p("  bad save path.", "err"); return
            parent["children"][name] = _new_file(page)
            self.save_disk()
            self.p(f"  saved to {fname}", "accent"); return
        self.p("  " + "─" * 50, "dim")
        for line in page.split("\n"):
            self.p("  " + line, "text")

    def cmd_telnet(self, args=None):
        args = args or []
        if not args:
            self.p("usage: telnet <host>", "warn"); return
        host = args[0].lower()
        if host not in self.NET_HOSTS:
            self.p(f"  telnet: unable to connect to {host}: host unknown", "err"); return
        self.p(f"  Trying {self._resolve_host(host)}...", "dim")
        self._snd("dialup")
        if runtime.INTERACTIVE:
            time.sleep(0.5)
        self.p(f"  Connected to {host}.", "accent")
        self.p("  Escape character is '^]'.", "dim")
        for line in self.NET_BANNERS.get(host, "(the line is silent)").split("\n"):
            self.p("  " + line, "text")
        if host == "the-angle.eye":
            self._snd("angle")
            self.p("  IT FEELS THE CONNECTION OPEN. IT TURNS TO LOOK.", "err")
            self.p("  try 'the angle' if you dare.", "dim")
        self.p(f"  Connection to {host} closed.", "dim")
