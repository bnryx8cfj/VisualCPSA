"""Recoverable About dialog for VisualCPSA."""
from __future__ import annotations

import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk

from visualcpsa.exceptions import ResourceError
from visualcpsa.logging_config import get_logger, traced
from visualcpsa.meta import PROGRAM_NAME, REFERENCES_HTML, RELEASE_DATE, VERSION, file_url


class AboutDialog(tk.Toplevel):
    """Modal About dialog linked to centralized package metadata."""

    @traced
    def __init__(self, parent: tk.Misc) -> None:
        """Create, focus, and safely grab the About dialog."""
        if not isinstance(parent, tk.Misc):
            raise TypeError("AboutDialog parent must be a Tk widget.")
        super().__init__(parent)
        self.title(f"About {PROGRAM_NAME}")
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self.close)
        frame = ttk.Frame(self, padding=16)
        frame.grid(row=0, column=0)
        ttk.Label(frame, text=PROGRAM_NAME, font=("Arial", 16, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(frame, text=f"Version {VERSION}").grid(row=1, column=0, sticky="w")
        ttk.Label(frame, text=RELEASE_DATE).grid(row=2, column=0, sticky="w")
        link = ttk.Label(frame, text="Open HTML References", foreground="blue", cursor="hand2")
        link.grid(row=3, column=0, sticky="w", pady=(8, 0))
        link.bind("<Button-1>", self.open_references)
        ttk.Button(frame, text="Close", command=self.close).grid(row=4, column=0, sticky="e", pady=(12, 0))
        self.focus_force()
        try:
            self.grab_set()
        except tk.TclError:
            get_logger(self).warning("Could not establish About dialog input grab", exc_info=True)
        assert self.winfo_exists(), "About dialog construction failed"

    @traced
    def open_references(self, event: tk.Event) -> None:
        """Open the references page, reporting recoverable browser and resource failures."""
        del event
        try:
            if not webbrowser.open(file_url(REFERENCES_HTML)):
                raise ResourceError("The default browser did not accept the references page.")
        except (ResourceError, webbrowser.Error) as error:
            get_logger(self).error("Could not open references: %s", error)
            messagebox.showerror("References", str(error), parent=self)

    @traced
    def close(self) -> None:
        """Release any input grab and close the dialog."""
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()
