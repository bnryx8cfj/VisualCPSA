"""Main recoverable Tkinter application shell for VisualCPSA."""
from __future__ import annotations

import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from visualcpsa.exceptions import CPSAExportError, PersistenceError, ResourceError, UnresolvedReferenceError, VisualCPSAError
from visualcpsa.export import generate_cpsa, validate_project
from visualcpsa.gui.about import AboutDialog
from visualcpsa.gui.splash import SplashScreen
from visualcpsa.io import load_project, save_project
from visualcpsa.logging_config import get_logger, traced
from visualcpsa.math_markup import math_lite_to_unicode
from visualcpsa.meta import DOCUMENTATION_HTML, ICON_PATH, file_url
from visualcpsa.model import CPSAGraphicalProject, LifelineView, MessageExchangeDraft, MessageExchangeView, ParticipantDraft, TermDraft
from visualcpsa.settings import Settings


class VisualCPSAApp(tk.Tk):
    """Tkinter application for drawing CPSA protocol-flow diagrams."""

    @traced
    def __init__(self, settings: Settings, config_path: Path) -> None:
        """Build the hidden GUI completely, then schedule one splash or reveal operation."""
        if not isinstance(settings, Settings) or not isinstance(config_path, Path):
            raise TypeError("VisualCPSAApp requires Settings and pathlib.Path.")
        super().__init__()
        self.settings = settings
        self.config_path = config_path
        self.withdraw()
        self.title("VisualCPSA")
        if ICON_PATH.exists():
            try:
                self.iconbitmap(str(ICON_PATH))
            except tk.TclError:
                get_logger(self).warning("Could not apply application icon %s", ICON_PATH, exc_info=True)
        self.geometry("1200x800")
        self.project = CPSAGraphicalProject.new_default()
        self.current_tool = tk.StringVar(value="select")
        self.current_file = ""
        self.canvas_to_kind: dict[int, str] = {}
        self.canvas_to_object: dict[int, str] = {}
        self.drag_lifeline_id = ""
        self.drag_start_x = 0.0
        self.drag_original_x = 0.0
        self.message_start_lifeline_id = ""
        self.message_preview_id = 0
        self._build_menu(); self._build_toolbar(); self._build_tabs(); self.render(); self.refresh_previews()
        start_intro_or_reveal(self, settings, config_path)
        assert self.notebook.winfo_exists(), "application notebook construction failed"

    @traced
    def _finish_splash(self) -> None:
        """Persist settings and reveal the main window after splash closes."""
        try:
            self.settings.save(self.config_path)
        except VisualCPSAError as error:
            get_logger(self).error("Could not save settings after splash: %s", error)
            messagebox.showwarning("Settings", str(error), parent=self)
        self.deiconify(); self.lift(); self.focus_force()

    def _build_menu(self) -> None:
        """Build File and Help menus with recoverable browser handling."""
        menu_bar = tk.Menu(self)
        file_menu = tk.Menu(menu_bar, tearoff=False)
        file_menu.add_command(label="Open...", command=self.open_project)
        file_menu.add_command(label="Save As...", command=self.save_project_as)
        file_menu.add_command(label="Exit", command=self.destroy)
        menu_bar.add_cascade(label="File", menu=file_menu)
        help_menu = tk.Menu(menu_bar, tearoff=False)
        help_menu.add_command(label="Documentation", command=self.open_documentation)
        help_menu.add_command(label="About...", command=lambda: AboutDialog(self))
        menu_bar.add_cascade(label="Help", menu=help_menu)
        self.config(menu=menu_bar)

    def _build_toolbar(self) -> None:
        """Build the main toolbar."""
        toolbar = ttk.Frame(self)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        ttk.Button(toolbar, text="Add Participant", command=self.add_participant).pack(side=tk.LEFT)
        ttk.Radiobutton(toolbar, text="Select/Move", value="select", variable=self.current_tool).pack(side=tk.LEFT)
        ttk.Radiobutton(toolbar, text="Message", value="message", variable=self.current_tool).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Refresh CPSA", command=self.refresh_previews).pack(side=tk.LEFT)

    def _build_tabs(self) -> None:
        """Build singleton tabs identified by type."""
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(self.notebook, bg="white", scrollregion=(0, 0, 2200, 1600))
        self.notebook.add(self.canvas, text="Protocol Flow")
        self.cpsa_text = tk.Text(self.notebook)
        self.notebook.add(self.cpsa_text, text="Generated CPSA")
        self.diagnostics_text = tk.Text(self.notebook)
        self.notebook.add(self.diagnostics_text, text="Diagnostics")
        self.canvas.bind("<ButtonPress-1>", self.on_press); self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release); self.canvas.bind("<Button-3>", self.on_right_click)

    @traced
    def open_documentation(self) -> None:
        """Open documentation in the system browser or report a recoverable failure."""
        try:
            if not webbrowser.open(file_url(DOCUMENTATION_HTML)):
                raise ResourceError("The default browser did not accept the documentation page.")
        except (ResourceError, webbrowser.Error) as error:
            get_logger(self).error("Could not open documentation: %s", error)
            messagebox.showerror("Documentation", str(error), parent=self)

    @traced
    def render(self) -> None:
        """Render permissive editor state, skipping unresolved draft objects with diagnostics."""
        self.canvas.delete("all"); self.canvas_to_kind.clear(); self.canvas_to_object.clear()
        diagram = self.project.active_diagram()
        participants = self.project.semantic_model.participants_by_id()
        radius = diagram.style.endpoint_radius()
        for lifeline in diagram.lifelines:
            participant = participants.get(lifeline.participant_id)
            label = participant.display_name if participant else lifeline.participant_id or "Unassigned"
            line_item = self.canvas.create_line(lifeline.x_position, lifeline.y_top, lifeline.x_position, lifeline.y_bottom, width=2)
            label_item = self.canvas.create_text(lifeline.x_position, lifeline.y_top - 20, text=label)
            self.bind_item(line_item, "lifeline", lifeline.id); self.bind_item(label_item, "lifeline", lifeline.id)
        lifelines = diagram.lifelines_by_id(); exchanges = self.project.semantic_model.exchanges_by_id()
        for message_view in diagram.sorted_message_views():
            exchange = exchanges.get(message_view.exchange_id)
            source = lifelines.get(message_view.source_lifeline_id); target = lifelines.get(message_view.target_lifeline_id)
            if not exchange or not source or not target:
                continue
            row_y = message_view.row_y()
            line_item = self.canvas.create_line(source.x_position, row_y, target.x_position, row_y, arrow=tk.LAST,
                                                width=2, fill="#004c99")
            circle_one = self.canvas.create_oval(source.x_position - radius, row_y - radius,
                                                 source.x_position + radius, row_y + radius, outline="#004c99")
            circle_two = self.canvas.create_oval(target.x_position - radius, row_y - radius,
                                                 target.x_position + radius, row_y + radius, outline="#004c99")
            if message_view.label_position == (0.0, 0.0):
                label_x, label_y = (source.x_position + target.x_position) / 2, row_y - 15
            else:
                label_x, label_y = message_view.label_position
            markup = self.project.semantic_model.term_label_or_placeholder(exchange.message_term_id)
            text_item = self.canvas.create_text(label_x, label_y, text=math_lite_to_unicode(markup), fill="#003366")
            for canvas_item in (line_item, circle_one, circle_two, text_item):
                self.bind_item(canvas_item, "message", exchange.id)

    def bind_item(self, item: int, kind: str, object_id: str) -> None:
        """Bind a positive canvas item to a supported object kind and non-empty id."""
        if item <= 0 or kind not in {"lifeline", "message"} or not object_id:
            raise ValueError("Invalid canvas item binding.")
        self.canvas_to_kind[item] = kind; self.canvas_to_object[item] = object_id
        assert self.canvas_to_object[item] == object_id, "canvas binding postcondition failed"

    def item_under_pointer(self) -> tuple[str, str]:
        """Return kind and object id under the pointer, using empty strings when no item is present."""
        current_items = self.canvas.find_withtag("current")
        if not current_items:
            return "", ""
        item = current_items[0]
        return self.canvas_to_kind.get(item, ""), self.canvas_to_object.get(item, "")

    @traced
    def add_participant(self) -> None:
        """Add a participant and lifeline to the active protocol and diagram."""
        diagram = self.project.active_diagram(); protocol = self.project.active_protocol()
        index = len(diagram.lifelines) + 1
        participant = ParticipantDraft(display_name=f"P{index}", role_name=f"role{index}")
        self.project.semantic_model.participants.append(participant); protocol.participant_ids.append(participant.id)
        diagram.lifelines.append(LifelineView(participant_id=participant.id,
                                              x_position=120 + (index - 1) * diagram.style.default_participant_spacing))
        self.project.mark_dirty(); self.render(); self.refresh_previews()
        assert participant.id in protocol.participant_ids, "participant addition postcondition failed"

    def on_press(self, event: tk.Event) -> None:
        """Begin moving a lifeline or drawing a message."""
        kind, object_id = self.item_under_pointer()
        x_position, y_position = self.canvas.canvasx(event.x_position), self.canvas.canvasy(event.y)
        if self.current_tool.get() == "message" and kind == "lifeline":
            self.message_start_lifeline_id = object_id
            self.message_preview_id = self.canvas.create_line(x_position, y_position, x_position, y_position,
                                                               arrow=tk.LAST, dash=(4, 3))
        elif self.current_tool.get() == "select" and kind == "lifeline":
            self.drag_lifeline_id = object_id; self.drag_start_x = x_position
            lifeline = self.project.active_diagram().lifelines_by_id().get(object_id)
            self.drag_original_x = lifeline.x_position if lifeline else x_position

    def on_drag(self, event: tk.Event) -> None:
        """Continue moving a lifeline or drawing a preview line."""
        x_position, y_position = self.canvas.canvasx(event.x_position), self.canvas.canvasy(event.y)
        if self.message_preview_id:
            coords = self.canvas.coords(self.message_preview_id)
            if len(coords) == 4:
                self.canvas.coords(self.message_preview_id, coords[0], coords[1], x_position, y_position)
        elif self.drag_lifeline_id:
            lifeline = self.project.active_diagram().lifelines_by_id().get(self.drag_lifeline_id)
            if lifeline:
                lifeline.x_position = self.drag_original_x + (x_position - self.drag_start_x); self.render()

    def on_release(self, event: tk.Event) -> None:
        """Complete a drag operation and reset runtime interaction sentinels."""
        x_position, y_position = self.canvas.canvasx(event.x_position), self.canvas.canvasy(event.y)
        if self.message_preview_id:
            self.canvas.delete(self.message_preview_id); self.message_preview_id = 0
            target = self.find_lifeline_near(x_position, y_position)
            if self.message_start_lifeline_id and target.id and target.id != self.message_start_lifeline_id:
                self.create_exchange(self.message_start_lifeline_id, target.id, y_position)
            self.message_start_lifeline_id = ""
        self.drag_lifeline_id = ""

    def find_lifeline_near(self, x_position: float, y_position: float) -> LifelineView:
        """Return a nearby lifeline or a documented empty draft sentinel."""
        for lifeline in self.project.active_diagram().lifelines:
            if lifeline.y_top <= y_position <= lifeline.y_bottom and abs(lifeline.x_position - x_position) <= 18:
                return lifeline
        return LifelineView()

    @traced
    def create_exchange(self, source_life_id: str, target_life_id: str, raw_y: float) -> None:
        """Create one exchange and shift all message rows at or below its insertion row."""
        diagram = self.project.active_diagram(); protocol = self.project.active_protocol(); lifelines = diagram.lifelines_by_id()
        if source_life_id not in lifelines or target_life_id not in lifelines:
            raise UnresolvedReferenceError("Message endpoints do not resolve to lifelines.")
        first_row = diagram.style.participant_top_margin + diagram.style.message_spacing
        row = first_row + round((raw_y - first_row) / diagram.style.message_spacing) * diagram.style.message_spacing
        for message_view in diagram.message_views:
            if message_view.row_y() >= row:
                message_view.y_position += diagram.style.message_spacing
        source, target = lifelines[source_life_id], lifelines[target_life_id]
        term = TermDraft(); self.project.semantic_model.terms.append(term)
        exchange = MessageExchangeDraft(source_participant_id=source.require_participant_id(),
                                        target_participant_id=target.require_participant_id(), message_term_id=term.id,
                                        ordinal_hint=row)
        self.project.semantic_model.exchanges.append(exchange); protocol.message_exchange_ids.append(exchange.id)
        diagram.message_views.append(MessageExchangeView(exchange_id=exchange.id, source_lifeline_id=source_life_id,
                                                          target_lifeline_id=target_life_id, y_position=float(row),
                                                          label_position=((source.x_position + target.x_position) / 2, row - 15)))
        self.project.mark_dirty(); self.render(); self.refresh_previews()

    @traced
    def edit_message(self, exchange_id: str) -> None:
        """Edit CPSA term and display markup, treating dialog cancellation as normal."""
        exchange = self.project.semantic_model.require_exchange(exchange_id)
        term = self.project.semantic_model.require_term(exchange.require_message_term_id())
        cpsa_text = simpledialog.askstring("CPSA Term", "CPSA term:", initialvalue=term.text, parent=self)
        if cpsa_text is None:
            get_logger(self).debug("CPSA term edit canceled")
            return
        markup = simpledialog.askstring("Display Markup", "Display markup:", initialvalue=term.label_markup(), parent=self)
        term.text = cpsa_text; term.display_markup = markup if markup is not None else term.display_markup
        self.project.mark_dirty(); self.render(); self.refresh_previews()

    def on_right_click(self, event: tk.Event) -> None:
        """Show a context menu for the clicked object."""
        kind, object_id = self.item_under_pointer(); menu = tk.Menu(self, tearoff=False)
        if kind == "message" and object_id:
            menu.add_command(label="Edit Message...", command=lambda: self._safe_gui_call(self.edit_message, object_id))
        else:
            menu.add_command(label="Add Participant", command=lambda: self._safe_gui_call(self.add_participant))
        menu.tk_popup(event.x_position_root, event.y_root)

    @traced
    def refresh_previews(self) -> None:
        """Refresh strict CPSA output or display its export error, plus permissive diagnostics."""
        self.cpsa_text.delete("1.0", tk.END)
        try:
            self.cpsa_text.insert("1.0", generate_cpsa(self.project))
        except CPSAExportError as error:
            self.cpsa_text.insert("1.0", f"; CPSA preview unavailable: {error}")
        diagnostics = validate_project(self.project)
        self.diagnostics_text.delete("1.0", tk.END)
        self.diagnostics_text.insert("1.0", "\n".join(diagnostics) if diagnostics else "No diagnostics.")

    @traced
    def save_project_as(self) -> None:
        """Save current project, handling cancellation and recoverable persistence errors."""
        path = filedialog.asksaveasfilename(defaultextension=".vcpsa.json", parent=self)
        if not path:
            get_logger(self).debug("Save As canceled")
            return
        try:
            save_project(self.project, path); self.current_file = path
        except PersistenceError as error:
            messagebox.showerror("Save Project", str(error), parent=self)

    @traced
    def open_project(self) -> None:
        """Open a project, handling cancellation and recoverable persistence errors."""
        path = filedialog.askopenfilename(filetypes=[("VisualCPSA JSON", "*.vcpsa.json"), ("JSON", "*.json"),
                                                       ("All files", "*.*")], parent=self)
        if not path:
            get_logger(self).debug("Open Project canceled")
            return
        try:
            loaded_project = load_project(path)
        except PersistenceError as error:
            messagebox.showerror("Open Project", str(error), parent=self)
            return
        self.project = loaded_project; self.current_file = path; self.render(); self.refresh_previews()

    def _safe_gui_call(self, function: object, *arguments: object) -> None:
        """Run a GUI command and show recoverable errors without terminating Tk's event loop."""
        if not callable(function):
            raise TypeError("GUI command must be callable.")
        try:
            function(*arguments)
        except VisualCPSAError as error:
            get_logger(self).error("Recoverable GUI command failure: %s", error, exc_info=True)
            messagebox.showerror("VisualCPSA", str(error), parent=self)
        except Exception as error:
            get_logger(self).exception("Unexpected GUI command failure")
            messagebox.showerror("VisualCPSA", f"Unexpected error: {error}", parent=self)


@traced
def start_intro_or_reveal(application: VisualCPSAApp, settings: Settings, config_path: Path) -> None:
    """Schedule exactly one splash or main-window reveal operation after GUI construction."""
    if not isinstance(application, VisualCPSAApp) or not isinstance(settings, Settings) or not isinstance(config_path, Path):
        raise TypeError("start_intro_or_reveal received invalid arguments.")
    if settings.show_intro:
        application.after_idle(lambda: SplashScreen(application, settings, application._finish_splash))
    else:
        application.after_idle(application._finish_splash)
