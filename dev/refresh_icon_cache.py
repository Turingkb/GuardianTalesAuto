"""Notify Windows Explorer after verifying the selected embedded EXE icon."""

import ctypes as ct
from ctypes import wintypes as wt
import os
from pathlib import Path

from set_exe_icon import verify_icon

ROOT = Path(__file__).resolve().parents[1]


def main():
    executable = ROOT / "GTAssistant.exe"
    verify_icon(executable, ROOT / "logo-v2.ico")
    # Explorer keys executable icons by path and modification time. Updating the
    # timestamp invalidates the old entry without replacing a running apphost.
    os.utime(executable, None)
    notify = ct.WinDLL("shell32", use_last_error=True).SHChangeNotify
    notify.argtypes = [wt.LONG, wt.UINT, ct.c_void_p, ct.c_void_p]
    notify.restype = None
    for path in (executable, ROOT / "logo-v2.ico", ROOT.parent / "坎公骑冠剑助手.lnk"):
        if path.exists():
            value = ct.c_wchar_p(str(path))
            notify(0x00002000, 0x2005, ct.cast(value, ct.c_void_p), None)
    # Refresh the shell's association image cache as well as individual items.
    notify(0x08000000, 0, None, None)
    print("Embedded icon verified; Windows shell icon cache refresh requested")
    return 0


if __name__ == "__main__": raise SystemExit(main())
