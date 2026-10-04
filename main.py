#!/usr/bin/env python3
import os
import sys
import subprocess
import importlib

# ---- Silence macOS Tkinter NSButton height warnings ----
# macOS enforces a 32px minimum on native NSButton controls but logs a
# cosmetic warning because its own guideline says <= 30px. Run with
# `python main.py --debug` to keep stderr visible during development.
if sys.platform == 'darwin' and '--debug' not in sys.argv:
    _real_stderr_fd = sys.stderr.fileno()
    _devnull_fd = os.open(os.devnull, os.O_WRONLY)
    os.dup2(_devnull_fd, _real_stderr_fd)

# ---- macOS: make the app menu show "Weekly Scheduler" instead of "Python" ----
if sys.platform == 'darwin':
    try:
        Foundation = importlib.import_module('Foundation')  # type: ignore
        bundle = Foundation.NSBundle.mainBundle()
        info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
        if info is not None:
            info['CFBundleName'] = 'Weekly Scheduler'
    except Exception:
        pass

import tkinter as tk
from tkinter import ttk

from app import SchedulerApp


def bring_to_front(root):
    root.lift()
    root.attributes('-topmost', True)
    root.after(200, lambda: root.attributes('-topmost', False))
    root.focus_force()
    if sys.platform == 'darwin':
        try:
            script = (
                'tell application "System Events" to set frontmost of '
                '(first process whose unix id is {}) to true'
            ).format(os.getpid())
            subprocess.Popen(['osascript', '-e', script],
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        except Exception:
            pass


def main():
    root = tk.Tk()
    style = ttk.Style()
    style.theme_use('clam')
    SchedulerApp(root)

    root.update_idletasks()
    bring_to_front(root)
    root.after(300, lambda: bring_to_front(root))

    root.mainloop()


if __name__ == "__main__":
    main()