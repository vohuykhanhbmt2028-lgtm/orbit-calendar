"""Launch the ORBIT Calendar editor as a separate process."""

import os
import sys
import subprocess


CALENDAR_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'calendar_app.py')


def launch_editor(file_path=None):
    """Launch calendar_app.py. If a file path is given, it opens that file."""
    args = [sys.executable, CALENDAR_SCRIPT]
    if file_path:
        args.append(file_path)
    subprocess.Popen(args)