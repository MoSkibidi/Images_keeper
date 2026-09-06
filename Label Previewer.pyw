"""Windowless launcher: double-click this on Windows to run the app without
a console window popping up (pythonw.exe is used to run .pyw files)."""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name("label_previewer.py")), run_name="__main__")
