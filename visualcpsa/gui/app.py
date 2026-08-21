"""Main Tkinter application shell for VisualCPSA."""
from __future__ import annotations
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, simpledialog, ttk
from visualcpsa.export import generate_cpsa, validate_project
from visualcpsa.gui.about import AboutDialog
from visualcpsa.gui.splash import SplashScreen
from visualcpsa.io import load_project, save_project
from visualcpsa.math_markup import math_lite_to_unicode
from visualcpsa.meta import DOCUMENTATION_HTML, file_url
from visualcpsa.model import CPSAGraphicalProject, LifelineView, MessageExchangeDraft, MessageExchangeView, ParticipantDraft, TermDraft
from visualcpsa.settings import Settings


class VisualCPSAApp(tk.Tk):
    """Tkinter application for drawing CPSA protocol-flow diagrams."""
    def __init__(self, settings: Settings, config_path: Path) -> None:
        """Initialize the app, optionally showing splash before revealing GUI."""
        super().__init__()
        self.settings = settings
        self.config_path = config_path
        self.withdraw()
        start_intro_or_reveal(self, settings, config_path)
        self.title("VisualCPSA")
        self.iconbitmap(r"VCPSA.ico")
        self.geometry("1200x800")
        self.project = CPSAGraphicalProject.new_default()
        self.current_tool = tk.StringVar(value="select")
        self.current_file: str | None = None
        self.canvas_to_kind: dict[int, str] = {}
        self.canvas_to_object: dict[int, str] = {}
        self.drag_lifeline_id: str | None = None
        self.drag_start_x = 0.0
        self.drag_original_x = 0.0
        self.message_start_lifeline_id: str | None = None
        self.message_preview_id: int | None = None
        self.singleton_tabs: dict[str, object] = {}
        self._build_menu()
        self._build_toolbar()
        self._build_tabs()
        self.render()
        self.refresh_previews()


    def _finish_splash(self) -> None:
        """Persist settings and reveal the main window after splash closes."""
        self.settings.save(self.config_path)
        self.deiconify()
        self.lift()
        assert self.winfo_viewable(), "main window should be visible after splash"

    def _build_menu(self) -> None:
        """Build the application menu bar, including Help menu."""
        menu_bar = tk.Menu(self)
        file_menu = tk.Menu(menu_bar, tearoff=False)
        file_menu.add_command(label="Open...", command=self.open_project)
        file_menu.add_command(label="Save As...", command=self.save_project_as)
        file_menu.add_command(label="Exit", command=self.destroy)
        menu_bar.add_cascade(label="File", menu=file_menu)
        help_menu = tk.Menu(menu_bar, tearoff=False)
        help_menu.add_command(label="Documentation", command=lambda: webbrowser.open(file_url(DOCUMENTATION_HTML)))
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
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Button-3>", self.on_right_click)

    def render(self) -> None:
        """Render the active diagram from persistent state."""
        self.canvas.delete("all")
        self.canvas_to_kind.clear()
        self.canvas_to_object.clear()
        diagram = self.project.active_diagram()
        model = self.project.semantic_model
        if not diagram:
            return
        participants = model.participants_by_id()
        radius = diagram.style.endpoint_radius()
        for lifeline in diagram.lifelines:
            participant = participants.get(lifeline.participant_id)
            label = participant.display_name if participant else lifeline.participant_id
            line_item = self.canvas.create_line(lifeline.x, lifeline.y_top, lifeline.x, lifeline.y_bottom, width=2)
            label_item = self.canvas.create_text(lifeline.x, lifeline.y_top - 20, text=label)
            self.bind_item(line_item, "lifeline", lifeline.id)
            self.bind_item(label_item, "lifeline", lifeline.id)
        lifelines = diagram.lifelines_by_id()
        exchanges = model.exchanges_by_id()
        for message_view in diagram.sorted_message_views():
            exchange = exchanges.get(message_view.exchange_id)
            source = lifelines.get(message_view.source_lifeline_id or "")
            target = lifelines.get(message_view.target_lifeline_id or "")
            if not (exchange and source and target):
                continue
            row_y = message_view.row_y()
            line_item = self.canvas.create_line(source.x, row_y, target.x, row_y, arrow=tk.LAST, width=2, fill="#004c99")
            circle_one = self.canvas.create_oval(source.x - radius, row_y - radius, source.x + radius, row_y + radius, outline="#004c99")
            circle_two = self.canvas.create_oval(target.x - radius, row_y - radius, target.x + radius, row_y + radius, outline="#004c99")
            label_x, label_y = message_view.label_position or ((source.x + target.x) / 2, row_y - 15)
            text_item = self.canvas.create_text(label_x, label_y, text=math_lite_to_unicode(model.term_label_markup(exchange.message_term_id)), fill="#003366")
            for item in (line_item, circle_one, circle_two, text_item):
                self.bind_item(item, "message", exchange.id)

    def bind_item(self, item: int, kind: str, object_id: str) -> None:
        """Bind a canvas item to a persistent object id."""
        self.canvas_to_kind[item] = kind
        self.canvas_to_object[item] = object_id

    def item_under_pointer(self) -> tuple[str | None, str | None]:
        """Return kind and object id under pointer."""
        current_items = self.canvas.find_withtag("current")
        if not current_items:
            return None, None
        item = current_items[0]
        return self.canvas_to_kind.get(item), self.canvas_to_object.get(item)

    def add_participant(self) -> None:
        """Add a new participant lifeline."""
        diagram = self.project.active_diagram()
        protocol = self.project.active_protocol()
        assert diagram and protocol
        index = len(diagram.lifelines) + 1
        participant = ParticipantDraft(display_name=f"P{index}", role_name=f"role{index}")
        self.project.semantic_model.participants.append(participant)
        protocol.participant_ids.append(participant.id)
        diagram.lifelines.append(LifelineView(participant_id=participant.id, x=120 + (index - 1) * diagram.style.default_participant_spacing))
        self.project.mark_dirty()
        self.render()
        self.refresh_previews()

    def on_press(self, event) -> None:
        """Begin moving a lifeline or drawing a message."""
        kind, object_id = self.item_under_pointer()
        x_position = self.canvas.canvasx(event.x)
        y_position = self.canvas.canvasy(event.y)
        if self.current_tool.get() == "message" and kind == "lifeline":
            self.message_start_lifeline_id = object_id
            self.message_preview_id = self.canvas.create_line(x_position, y_position, x_position, y_position, arrow=tk.LAST, dash=(4, 3))
        elif self.current_tool.get() == "select" and kind == "lifeline":
            self.drag_lifeline_id = object_id
            self.drag_start_x = x_position
            active_diagram = self.project.active_diagram()
            assert active_diagram is not None
            lifeline = active_diagram.lifelines_by_id().get(object_id or "")
            self.drag_original_x = lifeline.x if lifeline else x_position

    def on_drag(self, event) -> None:
        """Continue moving a lifeline or drawing preview line."""
        x_position = self.canvas.canvasx(event.x)
        y_position = self.canvas.canvasy(event.y)
        if self.message_preview_id:
            coords = self.canvas.coords(self.message_preview_id)
            self.canvas.coords(self.message_preview_id, coords[0], coords[1], x_position, y_position)
        elif self.drag_lifeline_id:
            active_diagram = self.project.active_diagram()
            assert active_diagram is not None
            lifeline = active_diagram.lifelines_by_id().get(self.drag_lifeline_id)
            if lifeline:
                lifeline.x = self.drag_original_x + (x_position - self.drag_start_x)
                self.render()

    def on_release(self, event) -> None:
        """Complete a drag operation."""
        x_position = self.canvas.canvasx(event.x)
        y_position = self.canvas.canvasy(event.y)
        if self.message_preview_id:
            self.canvas.delete(self.message_preview_id)
            self.message_preview_id = None
            target = self.find_lifeline_near(x_position, y_position)
            if self.message_start_lifeline_id and target and target.id != self.message_start_lifeline_id:
                self.create_exchange(self.message_start_lifeline_id, target.id, y_position)
            self.message_start_lifeline_id = None
        self.drag_lifeline_id = None

    def find_lifeline_near(self, x_position: float, y_position: float) -> LifelineView | None:
        """Find a lifeline near a coordinate."""
        diagram = self.project.active_diagram()
        assert diagram
        for lifeline in diagram.lifelines:
            if lifeline.y_top <= y_position <= lifeline.y_bottom and abs(lifeline.x - x_position) <= 18:
                return lifeline
        return None

    def create_exchange(self, source_life_id: str, target_life_id: str, raw_y: float) -> None:
        """Create a new exchange and shift lower messages globally."""
        diagram = self.project.active_diagram()
        protocol = self.project.active_protocol()
        assert diagram and protocol
        first_row = diagram.style.participant_top_margin + diagram.style.message_spacing
        row = first_row + round((raw_y - first_row) / diagram.style.message_spacing) * diagram.style.message_spacing
        for message_view in diagram.message_views:
            if message_view.row_y() >= row:
                message_view.y += diagram.style.message_spacing
        lifelines = diagram.lifelines_by_id()
        source = lifelines[source_life_id]
        target = lifelines[target_life_id]
        term = TermDraft()
        self.project.semantic_model.terms.append(term)
        exchange = MessageExchangeDraft(source_participant_id=source.participant_id, target_participant_id=target.participant_id, message_term_id=term.id, ordinal_hint=row)
        self.project.semantic_model.exchanges.append(exchange)
        protocol.message_exchange_ids.append(exchange.id)
        diagram.message_views.append(MessageExchangeView(exchange_id=exchange.id, source_lifeline_id=source_life_id, target_lifeline_id=target_life_id, y=float(row), label_position=((source.x + target.x) / 2, row - 15)))
        self.project.mark_dirty()
        self.render()
        self.refresh_previews()

    def edit_message(self, exchange_id: str) -> None:
        """Edit CPSA term and display markup."""
        exchange = self.project.semantic_model.exchanges_by_id().get(exchange_id)
        assert exchange
        term = self.project.semantic_model.terms_by_id().get(exchange.message_term_id or "")
        assert term
        cpsa_text = simpledialog.askstring("CPSA Term", "CPSA term:", initialvalue=term.text)
        if cpsa_text is not None:
            term.text = cpsa_text
        markup = simpledialog.askstring("Display Markup", "Display markup:", initialvalue=term.display_markup if term.display_markup is not None else term.text)
        if markup is not None:
            term.display_markup = markup
        self.project.mark_dirty()
        self.render()
        self.refresh_previews()

    def on_right_click(self, event) -> None:
        """Show context menu for clicked object."""
        kind, object_id = self.item_under_pointer()
        menu = tk.Menu(self, tearoff=False)
        if kind == "message" and object_id:
            menu.add_command(label="Edit Message...", command=lambda: self.edit_message(object_id))
        else:
            menu.add_command(label="Add Participant", command=self.add_participant)
        menu.tk_popup(event.x_root, event.y_root)

    def refresh_previews(self) -> None:
        """Refresh generated CPSA and diagnostics."""
        self.cpsa_text.delete("1.0", tk.END)
        self.cpsa_text.insert("1.0", generate_cpsa(self.project))
        diagnostics = validate_project(self.project)
        self.diagnostics_text.delete("1.0", tk.END)
        self.diagnostics_text.insert("1.0", "\n".join(diagnostics) if diagnostics else "No diagnostics.")

    def save_project_as(self) -> None:
        """Save current project as JSON."""
        path = filedialog.asksaveasfilename(defaultextension=".vcpsa.json")
        if path:
            save_project(self.project, path)
            self.current_file = path

    def open_project(self) -> None:
        """Open saved JSON project."""
        path = filedialog.askopenfilename(filetypes=[("VisualCPSA JSON", "*.vcpsa.json"), ("JSON", "*.json"), ("All files", "*.*")])
        if path:
            self.project = load_project(path)
            self.render()
            self.refresh_previews()

def start_intro_or_reveal(application:VisualCPSAApp, settings: Settings, config_path: Path) -> None:
    """Schedule the splash or reveal the main window without blocking startup."""
    assert isinstance(application, tk.Tk), "application must be a Tk root"
    assert isinstance(settings, Settings), "settings must be Settings"

    if settings.show_intro:
        # after_idle is crucial: the constructor must finish before Toplevel work.
        application.after_idle(lambda: SplashScreen(application, settings, application._finish_splash))
    else:
        application.after_idle(application._finish_splash)

        # Build the remainder of the GUI while hidden.

        if settings.show_intro:
            application.after_idle(
                lambda: SplashScreen(
                    application,
                    settings,
                    application._finish_splash,
                )
            )
        else:
            application.after_idle(application._finish_splash)

