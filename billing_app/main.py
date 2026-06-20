"""
main.py - Application entry point.

Run with:
    python main.py
"""
import sys
import os
import tkinter as tk
from tkinter import messagebox

# Ensure billing_app directory is on path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database as db


def main():
    # Initialise the database first
    try:
        db.initialize_database()
    except Exception as e:
        # Can't show a window yet, fall back to stderr
        print(f"Failed to initialise database: {e}", file=sys.stderr)
        sys.exit(1)

    root = tk.Tk()
    root.withdraw()  # hide until fully built

    try:
        from ui.main_window import MainWindow
        app = MainWindow(root)
    except Exception as e:
        messagebox.showerror("Startup Error",
                             f"Failed to load application UI:\n{e}")
        sys.exit(1)

    # Windows DPI awareness for sharper fonts
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass  # Non-Windows platform — safe to ignore

    root.deiconify()    # show the window
    root.mainloop()


if __name__ == "__main__":
    main()
