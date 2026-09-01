"""Metro Exodus Enhanced Edition - Controller Sensitivity Unlock.

Why the game feels capped (see README "How it works"):
  * preset 3 (the default "sensitivity preset"): joy_sens_x is normalised to a
    0..1 slider position and mapped to a hard-coded 0.5..1.5 speed multiplier,
    so raising the cvar's max alone changes nothing at the top end.
  * presets 0-2: speed = sqrt(joy_sens_x) - a real multiplier, but capped by the
    cvar descriptor max of 1.0.

This tool patches MetroExodus.exe (backup kept) so that in every preset the
look speed multiplier == joy_sens_x (stock in-game max == 1.5), ADS speed ==
joy_sens_aiming_x * look speed (0.05..1.0, as the engine intends), and raises
the descriptor max for joy_sens_x to NEW_MAX. It then writes your values to
user.cfg. Nothing runs while you play: no resident process, no memory writes,
no DLL injection.

  MetroSensUnlock.exe                    GUI
  python metro_sens_unlock.py --check    print what the patcher sees, change nothing
"""
import hashlib
import os
import re
import shutil
import struct
import subprocess
import sys
import winreg
from pathlib import Path

VERSION = "1.0.0"
NEW_MAX = 20.0
ENGINE_MAX = 1.0
LOOK = ["joy_sens_x"] + [f"preset{i}_joy_sens_x" for i in range(4)]
AIM = ["joy_sens_aiming_x"] + [f"preset{i}_joy_sens_aiming_x" for i in range(4)]
CVARS = LOOK + AIM
WANT_MAX = {**{c: NEW_MAX for c in LOOK}, **{c: ENGINE_MAX for c in AIM}}
ENTRY = 0x30  # descriptor: name* | 0 | value* | f32 min | f32 max | f32 value | type*
GAME_DIRS = ("Metro Exodus Enhanced Edition", "Metro Exodus")
BAK_SUFFIX = ".sensunlock.bak"


# ---------------------------------------------------------------- pe helpers
def pe_sections(data):
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    nsec, optsz = struct.unpack_from("<H", data, pe + 6)[0], struct.unpack_from("<H", data, pe + 20)[0]
    base = struct.unpack_from("<Q", data, pe + 24 + 24)[0]
    secs = []
    for i in range(nsec):
        s = pe + 24 + optsz + i * 40
        va, rawsz, rawptr = struct.unpack_from("<III", data, s + 12)
        secs.append((va, rawsz, rawptr))
    return base, secs


def off2rva(secs, off):
    for va, sz, ptr in secs:
        if ptr <= off < ptr + sz:
            return va + off - ptr
    return None


def rva2off(secs, rva):
    for va, sz, ptr in secs:
        if va <= rva < va + sz:
            return ptr + rva - va
    return None


# ---------------------------------------------------------------- descriptors
def find_entries(data):
    """{cvar: file offset of its descriptor entry} - validated by layout, not fixed offsets."""
    base, secs = pe_sections(data)
    found = {}
    for name in CVARS:
        needle = name.encode() + b"\0"
        spos = 0
        while (spos := data.find(needle, spos)) != -1:
            if not (chr(data[spos - 1]).isalnum() or data[spos - 1] == 95):  # standalone string
                ptr = struct.pack("<Q", base + off2rva(secs, spos))
                p = 0
                while (p := data.find(ptr, p)) != -1:
                    dflt_ptr = struct.unpack_from("<Q", data, p + 0x10)[0]
                    lo, hi = struct.unpack_from("<ff", data, p + 0x18)
                    if dflt_ptr == base + off2rva(secs, p + 0x20) and 0 < lo <= 1 and hi in (ENGINE_MAX, NEW_MAX):
                        found.setdefault(name, []).append(p)
                    p += 1
            spos += 1
    return {n: ps[0] for n, ps in found.items() if len(ps) == 1}  # ambiguous match == not found (fail closed)


# ---------------------------------------------------------------- code sites
def _rip_sites(data, base, secs, prefixes, target_va):
    """Offsets of instructions `prefix disp32` whose rip-relative target is target_va."""
    out = []
    for prefix in prefixes:
        p = 0
        while (p := data.find(prefix, p)) != -1:
            n = len(prefix) + 4
            rva = off2rva(secs, p)
            if rva is not None:
                disp = struct.unpack_from("<i", data, p + len(prefix))[0]
                if base + rva + n + disp == target_va:
                    out.append(p)
            p += 1
    return out


def find_code_patches(data, entries):
    """[(offset, stock_bytes, patched_bytes)] for the four look-speed code sites."""
    base, secs = pe_sections(data)
    sx, sa = entries["joy_sens_x"], entries["joy_sens_aiming_x"]
    va = lambda off: base + off2rva(secs, off)
    sx_min, sx_max, sx_val, sa_val = va(sx + 0x18), va(sx + 0x1C), va(sx + 0x20), va(sa + 0x20)

    def disp(site, n, target):
        return struct.pack("<i", target - (va(site) + n))

    def f32_at(target):
        o = rva2off(secs, target - base)
        return struct.unpack_from("<f", data, o)[0] if o else None

    patches = []
    # preset 3 model: hip = lerp(0.5, 1.5, t)  ->  lerp(min, max, t) == joy_sens_x
    anchors = _rip_sites(data, base, secs, [b"\xf3\x0f\x10\x15"], sx_val)  # movss xmm2, [joy_sens_x]
    for a in anchors:
        win = data[a:a + 0x100]
        for prefix, n, const, target in ((b"\xf3\x0f\x59\x1d", 8, 1.5, sx_max),        # mulss xmm3,  [1.5]
                                         (b"\xf3\x44\x0f\x59\x15", 9, 0.5, sx_min)):    # mulss xmm10, [0.5]
            q = win.find(prefix)
            while q != -1:
                site = a + q
                cur = va(site) + n + struct.unpack_from("<i", data, site + n - 4)[0]
                if cur == target or f32_at(cur) == const:
                    stock = prefix + data[site + n - 4:site + n] if cur != target else None  # None: already patched
                    patches.append((site, stock, prefix + disp(site, n, target)))
                    break
                q = win.find(prefix, q + 1)
    # presets 0-2 model: sqrt(joy_sens_x) -> joy_sens_x ; sqrt(joy_sens_aiming_x) -> joy_sens_aiming_x
    for op_sqrt, op_mov, target in ((b"\xf3\x44\x0f\x51\x1d", b"\xf3\x44\x0f\x10\x1d", sx_val),   # xmm11
                                    (b"\xf3\x0f\x51\x05", b"\xf3\x0f\x10\x05", sa_val)):          # xmm0
        for site in _rip_sites(data, base, secs, [op_sqrt, op_mov], target):
            d = data[site + len(op_sqrt):site + len(op_sqrt) + 4]
            patches.append((site, op_sqrt + d, op_mov + d))
    return patches


def code_state(data, patches):
    got = [data[o:o + len(new)] == new for o, _, new in patches]
    return "patched" if all(got) else "stock" if not any(got) else "mixed"


def patch_state(data, entries, patches=None):
    """'patched' | 'stock' | 'partial' (e.g. v1 max-only patch)"""
    maxes = {c: struct.unpack_from("<f", data, p + 0x1C)[0] for c, p in entries.items()}
    desc = "patched" if maxes == WANT_MAX else "stock" if set(maxes.values()) == {ENGINE_MAX} else "mixed"
    if patches is None:
        patches = find_code_patches(data, entries)
    code = code_state(data, patches) if len(patches) == 4 else "missing"
    if desc == code == "patched":
        return "patched"
    if desc == code == "stock":
        return "stock"
    return "partial"


def apply_patch(exe: Path):
    data = bytearray(exe.read_bytes())
    entries = find_entries(data)
    missing = [c for c in CVARS if c not in entries]
    if missing:
        raise RuntimeError(f"unsupported game build - descriptors not found for: {', '.join(missing)}")
    patches = find_code_patches(data, entries)
    if len(patches) != 4:
        raise RuntimeError(f"unsupported game build - found {len(patches)}/4 look-speed code sites")
    state = patch_state(data, entries, patches)
    if state == "patched":
        return "already patched"
    bak = exe.with_name(exe.name + BAK_SUFFIX)
    if state == "stock" or not bak.exists():  # a verified-stock exe is always the right backup; never overwrite otherwise
        shutil.copy2(exe, bak)
    for c, p in entries.items():
        struct.pack_into("<f", data, p + 0x1C, WANT_MAX[c])
    for o, _, new in patches:
        data[o:o + len(new)] = new
    tmp = exe.with_suffix(".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, exe)  # fails if the game is running - exactly what we want
    return f"patched {len(entries)} descriptors + {len(patches)} code sites (backup: {bak.name})"


def restore(exe: Path):
    bak = exe.with_name(exe.name + BAK_SUFFIX)
    if not bak.exists():
        raise RuntimeError("no backup found - use Steam > Verify integrity of game files instead")
    shutil.copy2(bak, exe)
    return "original exe restored"


# ---------------------------------------------------------------- locate
def find_exe():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
            steam = Path(winreg.QueryValueEx(k, "SteamPath")[0])
    except OSError:
        return None
    libs = [steam]
    try:
        vdf = (steam / "config/libraryfolders.vdf").read_text(errors="ignore")
        libs += [Path(p.replace("\\\\", "\\")) for p in re.findall(r'"path"\s+"([^"]+)"', vdf)]
    except OSError:
        pass
    for lib in libs:
        for gd in GAME_DIRS:
            exe = lib / "steamapps/common" / gd / "MetroExodus.exe"
            if exe.exists():
                return exe
    return None


def find_cfg():
    cfgs = sorted((Path.home() / "Saved Games/Metro Exodus").glob("*/user.cfg"),
                  key=lambda p: p.stat().st_mtime, reverse=True)
    return cfgs[0] if cfgs else None


def game_running():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq MetroExodus.exe"], capture_output=True,
                         text=True, creationflags=0x08000000).stdout
    return "MetroExodus.exe" in out


# ---------------------------------------------------------------- cfg
def cfg_read(cfg: Path):
    return cfg.read_text(errors="ignore", newline="")  # keep the game's CRLF intact


def cfg_get(text, key, default=None):
    m = re.search(rf"(?m)^{re.escape(key)} (\S+)\r?$", text)
    return m.group(1) if m else default


def cfg_set(text, key, val):
    line = f"{key} {val}"
    new, n = re.subn(rf"(?m)^{re.escape(key)} \S+(?=\r?$)", line, text)
    return new if n else new + ("" if new.endswith("\n") else "\r\n") + line + "\r\n"


def write_sens(cfg: Path, hip, ads):
    text = cfg_read(cfg)
    presets = {cfg_get(text, "gamepad_preset", "0"), cfg_get(text, "_gamepad_preset_sens", "3")}
    keys = [""] + [f"preset{p}_" for p in sorted(presets) if p.isdigit()]
    for k in keys:
        text = cfg_set(text, f"{k}joy_sens_x", f"{hip:g}")
        text = cfg_set(text, f"{k}joy_sens_aiming_x", f"{ads:g}")
    cfg.write_text(text, newline="")
    return keys


def read_sens(cfg: Path):
    text = cfg_read(cfg)
    return float(cfg_get(text, "joy_sens_x", "0.95")), float(cfg_get(text, "joy_sens_aiming_x", "0.7"))


def stock_to_multiplier(cfg: Path, v):
    """What a stock-exe slider value feels like, in patched units - so Apply keeps the player's current speed."""
    if cfg_get(cfg_read(cfg), "_gamepad_preset_sens", "3") == "3":
        return round(0.5 + (v - 0.1) / (ENGINE_MAX - 0.1), 2)  # lerp(0.5, 1.5, t)
    return round(v ** 0.5, 2)  # legacy presets: sqrt


# ---------------------------------------------------------------- GUI
def gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    root = tk.Tk()
    root.title(f"Metro Exodus - Controller Sensitivity Unlock {VERSION}")
    root.resizable(False, False)
    pad = {"padx": 14, "pady": 6}
    state = {"exe": find_exe(), "cfg": find_cfg()}

    def exe_status():
        exe = state["exe"]
        if not exe:
            return "game not found - click Browse"
        try:
            data = exe.read_bytes()
            entries = find_entries(data)
            if len(entries) < len(CVARS):
                return f"{exe.parent.name}: unsupported build"
            return f"{exe.parent.name}: {patch_state(data, entries)}"
        except OSError as e:
            return f"cannot read exe: {e}"

    hip = tk.DoubleVar(value=0.95)  # engine defaults; overwritten by the player's own user.cfg values below
    ads = tk.DoubleVar(value=0.7)
    if state["cfg"]:
        try:
            h, a = read_sens(state["cfg"])
            if state["exe"] and "patched" not in exe_status():  # cfg still holds stock slider units - show the equivalent
                h = stock_to_multiplier(state["cfg"], min(h, ENGINE_MAX))
            hip.set(min(max(h, 0.1), NEW_MAX)); ads.set(min(max(a, 0.05), 1.0))
        except (OSError, ValueError):
            pass

    frm = ttk.Frame(root, padding=12); frm.grid()
    ttk.Label(frm, text="Game folder").grid(row=0, column=0, sticky="w", **pad)
    exe_var = tk.StringVar(value=str(state["exe"].parent) if state["exe"] else "")
    ttk.Entry(frm, textvariable=exe_var, width=44, state="readonly").grid(row=0, column=1, sticky="we", **pad)
    status = ttk.Label(frm, text=exe_status(), foreground="#555")
    status.grid(row=1, column=0, columnspan=3, sticky="w", **pad)

    def row(r, label, var, lo, hi, step):
        ttk.Label(frm, text=label).grid(row=r, column=0, sticky="w", **pad)
        ttk.Scale(frm, from_=lo, to=hi, variable=var, length=260,
                  command=lambda v, s=var: s.set(round(float(v), 2))).grid(row=r, column=1, **pad)
        ttk.Spinbox(frm, from_=lo, to=hi, increment=step, textvariable=var, width=6, format="%.2f").grid(row=r, column=2, **pad)

    row(2, "Look speed", hip, 0.1, NEW_MAX, 0.1)
    row(3, "ADS speed (x look)", ads, 0.05, 1.0, 0.05)
    ttk.Label(frm, text="Look: stock in-game max is 1.5 - try 2.5-5.   ADS: fraction of look speed (stock 0.45-0.7).",
              foreground="#777").grid(row=4, column=0, columnspan=3, sticky="w", **pad)
    ttk.Label(frm, text="Do NOT touch the in-game controller sensitivity sliders after applying - "
                        "they overwrite these values and undo the tweak. Change speed here instead.",
              foreground="#c00000", wraplength=520, justify="left").grid(row=5, column=0, columnspan=3, sticky="w", **pad)

    def browse():
        d = filedialog.askdirectory(title="Select the Metro Exodus game folder (contains MetroExodus.exe)")
        if not d:
            return
        exe = Path(d) / "MetroExodus.exe"
        if not exe.exists():
            return messagebox.showerror("Not found", f"No MetroExodus.exe in: {d}")
        state["exe"] = exe
        exe_var.set(d)
        status.config(text=exe_status())

    def apply():
        if not state["exe"]:
            return messagebox.showerror("Not found", "Select MetroExodus.exe first.")
        if game_running():
            return messagebox.showerror("Game running", "Close Metro Exodus first.")
        try:
            h, a = float(hip.get()), float(ads.get())
            if not (0.1 <= h <= NEW_MAX and 0.05 <= a <= 1.0):
                raise ValueError(f"look must be 0.1-{NEW_MAX:g}, ADS 0.05-1")
            msg = apply_patch(state["exe"])
            if state["cfg"]:
                write_sens(state["cfg"], h, a)
                msg += f"\nuser.cfg: look {h:g}, ADS {a:g} x look"
            else:
                msg += "\nuser.cfg not found - launch the game once, then apply again"
        except (RuntimeError, OSError, ValueError) as e:
            return messagebox.showerror("Failed", str(e))
        status.config(text=exe_status())
        messagebox.showinfo("Done", msg + "\n\nDon't touch the in-game look sensitivity slider - it only writes 0.1-1.0.")

    def undo():
        if not state["exe"]:
            return
        if game_running():
            return messagebox.showerror("Game running", "Close Metro Exodus first.")
        try:
            msg = restore(state["exe"])
            if state["cfg"]:
                write_sens(state["cfg"], min(hip.get(), 1.0), min(ads.get(), 1.0))
        except (RuntimeError, OSError) as e:
            return messagebox.showerror("Failed", str(e))
        status.config(text=exe_status())
        messagebox.showinfo("Restored", msg)

    def copy_report():
        try:
            text = report(state["exe"], state["cfg"])
        except OSError as e:
            text = f"report failed: {e}"
        root.clipboard_clear(); root.clipboard_append(text)
        messagebox.showinfo("Copied", "Diagnostic report copied to clipboard - paste it in your bug report.")

    ttk.Button(frm, text="Browse...", command=browse).grid(row=0, column=2, **pad)
    btns = ttk.Frame(frm); btns.grid(row=6, column=0, columnspan=3, sticky="e", **pad)
    ttk.Button(btns, text="Copy report", command=copy_report).pack(side="left", padx=4)
    ttk.Button(btns, text="Restore original", command=undo).pack(side="left", padx=4)
    ttk.Button(btns, text="Apply", command=apply, default="active").pack(side="left", padx=4)
    root.bind("<Return>", lambda e: apply())
    root.mainloop()


def report(exe, cfg):
    """Diagnostic text for --check and the GUI's Copy report button. Read-only."""
    out = [f"MetroSensUnlock {VERSION}", f"exe: {exe}", f"cfg: {cfg}"]
    if exe:
        data = exe.read_bytes()
        out += [f"edition folder: {exe.parent.name}", f"exe size: {len(data)}",
                f"exe sha256: {hashlib.sha256(data).hexdigest()}",
                f"backup: {'present' if exe.with_name(exe.name + BAK_SUFFIX).exists() else 'none'}"]
        entries = find_entries(data)
        for c in CVARS:
            p = entries.get(c)
            if p is None:
                out.append(f"  {c:28} MISSING"); continue
            lo, hi, d = struct.unpack_from("<fff", data, p + 0x18)
            out.append(f"  {c:28} entry@{p:#x} min={lo:g} max={hi:g} value={d:g} want_max={WANT_MAX[c]:g}")
        if len(entries) == len(CVARS):
            patches = find_code_patches(data, entries)
            for o, old, new in patches:
                cur = data[o:o + len(new)]
                out.append(f"  code@{o:#x} {cur.hex()}  {'PATCHED' if cur == new else 'stock' if cur == old else '???'}")
            out.append(f"code sites: {len(patches)}/4")
            out.append(f"state: {patch_state(data, entries, patches)}")
        else:
            out.append(f"descriptors: {len(entries)}/{len(CVARS)}")
            out.append("state: unsupported")
    if cfg:
        try:
            h, a = read_sens(cfg)
            out.append(f"cfg look: {h:g}  ads: {a:g}")
        except (OSError, ValueError) as e:
            out.append(f"cfg unreadable: {e}")
    return "\n".join(out)


if __name__ == "__main__":
    print(report(find_exe(), find_cfg())) if "--check" in sys.argv else gui()
