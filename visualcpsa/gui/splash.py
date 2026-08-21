"""Reliable native-Tk startup splash screen for VisualCPSA.

The introduction is animated directly on a Tkinter Canvas. It does not depend
on GIF decoding, Pillow, Matplotlib, SVG support, or a resource file path. This
avoids the startup failure where the splash remained on "Preparing
introduction..." because Tk could not load the first GIF frame.
"""
from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from visualcpsa.meta import ANNOUNCEMENTS_MD, PROGRAM_NAME, RELEASE_DATE, VERSION
from visualcpsa.settings import Settings


class SplashScreen(tk.Toplevel):
    """Dismissible one-shot VisualCPSA introduction animated on a Canvas."""

    CANVAS_WIDTH = 860
    CANVAS_HEIGHT = 470
    FRAME_DELAY_MS = 45

    ARROW_FRAMES = 18
    TYPING_FRAMES = 60
    MESSAGE_PAUSE_FRAMES = 12
    FINAL_HOLD_FRAMES = 30

    FIRST_MESSAGE_START = 80

    MESSAGE_DURATION = (
        ARROW_FRAMES
        + TYPING_FRAMES
        + MESSAGE_PAUSE_FRAMES
    )

    SECOND_MESSAGE_START = (
        FIRST_MESSAGE_START
        + MESSAGE_DURATION
    )

    THIRD_MESSAGE_START = (
        SECOND_MESSAGE_START
        + MESSAGE_DURATION
    )

    TOTAL_FRAMES = (
        THIRD_MESSAGE_START
        + ARROW_FRAMES
        + TYPING_FRAMES
        + FINAL_HOLD_FRAMES
        + 1
    )

    def __init__(
        self,
        parent: tk.Tk,
        settings: Settings,
        on_close: Callable[[], None],
    ) -> None:
        """Create the splash and schedule its non-blocking one-shot animation."""
        assert isinstance(parent, tk.Tk), "parent must be a Tk root"
        assert isinstance(settings, Settings), "settings must be Settings"
        assert callable(on_close), "on_close must be callable"
        super().__init__(parent)
        self.settings = settings
        self.on_close = on_close
        self.frame_number = 0
        self.animation_after_id: str | None = None
        self.dismissed = False
        self.show_intro_var = tk.BooleanVar(self, value=settings.show_intro)

        self.withdraw()
        self.title(f"Welcome to {PROGRAM_NAME}")
        self.iconbitmap(r"VCPSA.ico")

        self.geometry("900x650")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.dismiss)
        self._build_widgets()
        self.after_idle(self._show_and_start)
        assert self.winfo_exists(), "splash construction failed"

    def _build_widgets(self) -> None:
        """Build the splash banner, canvas, translucent panel, and controls."""
        ttk.Label(
            self,
            text=f"Welcome to {PROGRAM_NAME} {VERSION}",
            font=("Arial", 22, "bold"),
        ).pack(pady=(12, 4))
        ttk.Label(self, text=RELEASE_DATE).pack()

        self.canvas = tk.Canvas(
            self,
            width=self.CANVAS_WIDTH,
            height=self.CANVAS_HEIGHT,
            bg="white",
            highlightthickness=1,
            highlightbackground="#88aacc",
        )
        self.canvas.pack(padx=16, pady=10)

        controls = ttk.Frame(self)
        controls.pack(fill=tk.X, padx=16, pady=(0, 12))
        ttk.Checkbutton(
            controls,
            text="show introduction",
            variable=self.show_intro_var,
        ).pack(side=tk.LEFT)
        ttk.Button(controls, text="Dismiss", command=self.dismiss).pack(side=tk.RIGHT)
        assert self.canvas.winfo_exists(), "splash canvas was not created"

    def _show_and_start(self) -> None:
        """Map and focus the splash before starting the animation timer."""
        if self.dismissed or not self.winfo_exists():
            return
        self.deiconify()
        self.lift()
        self.attributes("-topmost", True)
        self.update_idletasks()
        self.focus_force()
        try:
            self.grab_set()
        except tk.TclError:
            pass
        self.after(250, self._remove_topmost)
        self._draw_frame()
        assert self.winfo_viewable(), "splash should be visible before animation"

    def _remove_topmost(self) -> None:
        """Remove temporary topmost state after the splash has received focus."""
        if not self.dismissed and self.winfo_exists():
            self.attributes("-topmost", False)

    def _draw_frame(self) -> None:
        """Draw one complete animation frame and schedule the next frame."""
        if self.dismissed or not self.winfo_exists():
            return
        self.canvas.delete("all")
        self._draw_application_mockup()
        self._draw_animation_content(self.frame_number)
        self._draw_announcements_overlay()
        self.frame_number += 1
        if self.frame_number < self.TOTAL_FRAMES:
            self.animation_after_id = self.after(self.FRAME_DELAY_MS, self._draw_frame)
        else:
            self.animation_after_id = None
        assert 0 <= self.frame_number <= self.TOTAL_FRAMES, "frame counter invariant failed"

    def _draw_application_mockup(self) -> None:
        """Draw a simplified VisualCPSA application window behind the animation."""
        self.canvas.create_rectangle(15, 15, 845, 455, fill="#eef3f8", outline="#557799")
        self.canvas.create_rectangle(15, 15, 845, 47, fill="#dce7f2", outline="#557799")
        self.canvas.create_text(30, 31, text="VisualCPSA", anchor="w", font=("Arial", 12, "bold"))
        self.canvas.create_text(135, 31, text="File   Model   View   Help", anchor="w", font=("Arial", 10))
        self.canvas.create_rectangle(30, 58, 830, 310, fill="white", outline="#aab7c4")
        self.canvas.create_text(45, 68, text="Protocol Flow", anchor="nw", font=("Arial", 11, "bold"), fill="#234")

    def _draw_animation_content(self, frame_number: int) -> None:
        """Draw participants, messages, typing text, and the moving mouse cursor."""
        alice_x = 230
        bob_x = 650
        lifeline_top = 110
        lifeline_bottom = 295

        # Participant creation is staged so the cursor appears to add each one.
        if frame_number >= 25:
            self._draw_participant(alice_x, lifeline_top, lifeline_bottom, "Alice")
        if frame_number >= 55:
            self._draw_participant(bob_x, lifeline_top, lifeline_bottom, "Bob")

        messages = (
            (
                self.FIRST_MESSAGE_START,
                135,
                alice_x,
                bob_x,
                "1  {N_a, A}_{K_B}",
            ),
            (
                self.SECOND_MESSAGE_START,
                195,
                bob_x,
                alice_x,
                "2  {N_a, N_b}_{K_A}",
            ),
            (
                self.THIRD_MESSAGE_START,
                255,
                alice_x,
                bob_x,
                "3  {N_b}_{K_B}",
            ),
        )

        for start_frame, row_y, source_x, target_x, markup in messages:
            self._draw_message_stage(frame_number, start_frame, row_y, source_x, target_x, markup)

        cursor_x, cursor_y = self._cursor_position(frame_number)
        self._draw_cursor(cursor_x, cursor_y)

    def _draw_participant(self, x_position: int, y_top: int, y_bottom: int, name: str) -> None:
        """Draw one participant label and vertical lifeline."""
        assert name, "participant name must not be empty"
        self.canvas.create_text(x_position, y_top - 18, text=name, font=("Arial", 11, "bold"))
        self.canvas.create_line(x_position, y_top, x_position, y_bottom, fill="#222", width=2)

    def _draw_message_stage(
        self,
        frame_number: int,
        start_frame: int,
        row_y: int,
        source_x: int,
        target_x: int,
        markup: str,
    ) -> None:
        """Animate one horizontal arrow followed by typewriter-style label text."""
        if frame_number < start_frame:
            return
        arrow_frames = self.ARROW_FRAMES
        typing_frames = self.TYPING_FRAMES

        elapsed = frame_number - start_frame
        arrow_progress = min(1.0, elapsed / arrow_frames)
        current_x = source_x + (target_x - source_x) * arrow_progress
        self.canvas.create_line(source_x, row_y, current_x, row_y, fill="#005baa", width=2)
        self.canvas.create_oval(source_x - 6, row_y - 6, source_x + 6, row_y + 6, fill="white", outline="#005baa", width=2)
        if arrow_progress >= 1.0:
            self._draw_arrow_head(target_x, row_y, target_x > source_x)
            self.canvas.create_oval(target_x - 6, row_y - 6, target_x + 6, row_y + 6, fill="white", outline="#005baa", width=2)

            typing_elapsed = max(0, elapsed - arrow_frames)
            display_markup = self._display_markup(markup)

            if typing_elapsed >= typing_frames:
                visible_text = display_markup
            else:
                typing_progress = typing_elapsed / typing_frames

                character_count = int(
                    len(display_markup) * typing_progress
                )

                visible_text = display_markup[:character_count]

            self.canvas.create_text(
                (source_x + target_x) / 2,
                row_y - 15,
                text=visible_text,
                font=("Arial", 11),
                fill="#003b70",
            )

    def _display_markup(self, markup: str) -> str:
        """Translate nonce and key subscripts to Unicode characters."""
        assert isinstance(markup, str), "markup must be a string"

        translations = {
            "N_a": "Nₐ",
            "N_b": "Nᵦ",
            "K_A": "Kₐ",
            "K_B": "Kᵦ",
        }

        display_text = markup

        for source_text, target_text in translations.items():
            display_text = display_text.replace(
                source_text,
                target_text,
            )

        assert isinstance(
            display_text,
            str,
        ), "display markup translation must return text"

        return display_text

    def _draw_arrow_head(self, x_position: int, y_position: int, points_right: bool) -> None:
        """Draw an arrow head facing right or left."""
        direction = -1 if points_right else 1
        self.canvas.create_polygon(
            x_position,
            y_position,
            x_position + 11 * direction,
            y_position - 6,
            x_position + 11 * direction,
            y_position + 6,
            fill="#005baa",
            outline="#005baa",
        )

    def _cursor_position(self, frame_number: int) -> tuple[float, float]:
        """Move the cursor in synchronization with message creation."""

        first_arrow_end = self.FIRST_MESSAGE_START + self.ARROW_FRAMES
        first_typing_end = first_arrow_end + self.TYPING_FRAMES
        second_arrow_end = self.SECOND_MESSAGE_START + self.ARROW_FRAMES
        second_typing_end = second_arrow_end + self.TYPING_FRAMES
        third_arrow_end = self.THIRD_MESSAGE_START + self.ARROW_FRAMES
        third_typing_end = third_arrow_end + self.TYPING_FRAMES

        keyframes = (
            # Move to the participant creation positions.
            (0, 90, 85),
            (25, 230, 95),
            (55, 650, 95),

            # Move to the start of message 1.
            (self.FIRST_MESSAGE_START, 230, 135),

            # Drag message 1 from Alice to Bob.
            (first_arrow_end, 650, 135),

            # Stay at Bob while message 1 is typed.
            (first_typing_end, 650, 135),

            # Pause before moving to message 2.
            (
                self.SECOND_MESSAGE_START,
                650,
                195,
            ),

            # Drag message 2 from Bob to Alice.
            (second_arrow_end, 230, 195),

            # Stay at Alice while message 2 is typed.
            (second_typing_end, 230, 195),

            # Pause before moving to message 3.
            (
                self.THIRD_MESSAGE_START,
                230,
                255,
            ),

            # Drag message 3 from Alice to Bob.
            (third_arrow_end, 650, 255),

            # Stay at Bob while message 3 is typed.
            (third_typing_end, 650, 255),

            # Move away during the final hold.
            (
                self.TOTAL_FRAMES - 1,
                740,
                285,
            ),
        )

        for keyframe_index in range(len(keyframes) - 1):
            (
                start_frame,
                start_x,
                start_y,
            ) = keyframes[keyframe_index]

            (
                end_frame,
                end_x,
                end_y,
            ) = keyframes[keyframe_index + 1]

            if start_frame <= frame_number <= end_frame:
                frame_span = max(
                    1,
                    end_frame - start_frame,
                )
                fraction = (
                    frame_number - start_frame
                ) / frame_span

                cursor_x = (
                    start_x
                    + (end_x - start_x) * fraction
                )
                cursor_y = (
                    start_y
                    + (end_y - start_y) * fraction
                )

                return cursor_x, cursor_y

        return 740.0, 285.0


    def _draw_cursor(self, x_position: float, y_position: float) -> None:
        """Draw a mouse-pointer shape at the requested canvas coordinate."""
        self.canvas.create_polygon(
            x_position,
            y_position,
            x_position + 18,
            y_position + 8,
            x_position + 9,
            y_position + 12,
            x_position + 15,
            y_position + 27,
            x_position + 9,
            y_position + 30,
            x_position + 3,
            y_position + 15,
            x_position - 2,
            y_position + 22,
            fill="#202020",
            outline="white",
        )

    def _draw_announcements_overlay(self) -> None:
        """Draw announcements over the animation using simulated transparency."""
        self.canvas.create_rectangle(
            40,
            330,
            820,
            440,
            fill="#f8fbff",
            outline="#6688aa",
            stipple="gray75",
        )
        self.canvas.create_text(60, 345, text="Announcements", anchor="nw", font=("Arial", 12, "bold"), fill="#102030")
        self.canvas.create_text(60, 370, text=self._load_announcements(), anchor="nw", width=730, font=("Arial", 10), fill="#102030")

    @staticmethod
    def _load_announcements() -> str:
        """Return announcements file contents or ``None``."""
        if not ANNOUNCEMENTS_MD.exists():
            return "None"
        content = ANNOUNCEMENTS_MD.read_text(encoding="utf-8").strip()
        return content or "None"

    def dismiss(self) -> None:
        """Stop the animation, persist checkbox state, and reveal the main GUI."""
        if self.dismissed:
            return
        self.dismissed = True
        if self.animation_after_id is not None:
            try:
                self.after_cancel(self.animation_after_id)
            except tk.TclError:
                pass
            self.animation_after_id = None
        self.settings.show_intro = bool(self.show_intro_var.get())
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()
        self.on_close()
        assert isinstance(self.settings.show_intro, bool), "show_intro must remain boolean"
