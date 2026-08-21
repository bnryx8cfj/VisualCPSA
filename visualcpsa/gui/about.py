"""About dialog for VisualCPSA."""
from __future__ import annotations
import tkinter as tk
import webbrowser
from tkinter import ttk
from visualcpsa.meta import PROGRAM_NAME, REFERENCES_HTML, RELEASE_DATE, VERSION, file_url


class AboutDialog(tk.Toplevel):
    """Modal About dialog with a references link."""
    def __init__(self, parent) -> None:
        """Create the About dialog."""
        super().__init__(parent)
        self.title(f"About {PROGRAM_NAME}")
        self.transient(parent)
        self.grab_set()
        frame = ttk.Frame(self, padding=16)
        frame.grid(row=0, column=0)
        ttk.Label(frame, text=PROGRAM_NAME, font=("Arial", 16, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(frame, text=f"Version {VERSION}").grid(row=1, column=0, sticky="w")
        ttk.Label(frame, text=RELEASE_DATE).grid(row=2, column=0, sticky="w")
        link = ttk.Label(frame, text="Open HTML References", foreground="blue", cursor="hand2")
        link.grid(row=3, column=0, sticky="w", pady=(8, 0))
        link.bind("<Button-1>", lambda event: webbrowser.open(file_url(REFERENCES_HTML)))
        ttk.Button(frame, text="Close", command=self.destroy).grid(row=4, column=0, sticky="e", pady=(12, 0))
        assert self.winfo_exists(), "about dialog was not created"
