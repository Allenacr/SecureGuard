"""
SecureGuard Settings Panel 
"""

import os
import logging
import tkinter as tk
from tkinter import font as tkfont, filedialog, messagebox
from typing import Optional, Callable

logger = logging.getLogger("SecureGuard.SettingsPanel")

# ======================================================================
# AURORA THEME
# ======================================================================
INK          = "#05070C"   # window ink
INK_DEEP     = "#030407"   # rail / banner
PANEL        = "#0D1119"   # card surface
PANEL_HI     = "#141A25"   # card hover / elevated
FIELD        = "#080C13"   # input well

TXT          = "#EAF0FA"   # primary text
TXT_SOFT     = "#8D9BB5"   # secondary
TXT_FAINT    = "#4F5B72"   # tertiary

CYAN         = "#22D3EE"
CYAN_DK      = "#0E9BB5"
VIOLET       = "#A78BFA"
VIOLET_DK    = "#7C5CF0"
AMBER        = "#FBBF24"
EMERALD      = "#34D399"
EMERALD_DK   = "#12A97B"
ROSE         = "#FB7185"
ROSE_DK      = "#E11D48"

LINE         = "#1A2130"
LINE_HI      = "#2A3548"

AURORA = ["#22D3EE", "#4CC9F0", "#7C5CF0", "#A78BFA", "#F472B6", "#FBBF24"]

FONT_UI = "Segoe UI"


# ----------------------------------------------------------------------
# presentation helpers
# ----------------------------------------------------------------------
def _hover(widget, normal_bg, hover_bg, normal_fg=None, hover_fg=None):
    def on_enter(_e):
        widget.configure(bg=hover_bg)
        if hover_fg:
            widget.configure(fg=hover_fg)

    def on_leave(_e):
        widget.configure(bg=normal_bg)
        if normal_fg:
            widget.configure(fg=normal_fg)

    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)


def _lerp_hex(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _gradient_ramp(colors, steps):
    out = []
    segs = len(colors) - 1
    for i in range(steps):
        p = i / max(steps - 1, 1) * segs
        k = min(int(p), segs - 1)
        out.append(_lerp_hex(colors[k], colors[k + 1], p - k))
    return out


class GradientStrip(tk.Canvas):
    """Horizontal aurora gradient line/band."""

    def __init__(self, parent, height=2, colors=None, bg=INK, **kw):
        super().__init__(parent, height=height, bg=bg, highlightthickness=0, bd=0, **kw)
        self._colors = colors or AURORA
        self._h = height
        self.bind("<Configure>", self._paint)

    def _paint(self, _e=None):
        self.delete("all")
        w = max(self.winfo_width(), 1)
        steps = 90
        ramp = _gradient_ramp(self._colors, steps)
        for i, c in enumerate(ramp):
            self.create_rectangle(i * w / steps, 0, (i + 1) * w / steps + 1,
                                  self._h, fill=c, outline=c)


class GlowCard(tk.Frame):
    """Rounded canvas card with layered glow outline and a gradient cap."""

    def __init__(self, parent, bg=PANEL, radius=16, padx=20, pady=18,
                 accent=None, **kwargs):
        super().__init__(parent, bg=parent["bg"], **kwargs)
        self._radius, self._bg, self._accent = radius, bg, accent
        self.canvas = tk.Canvas(self, bg=parent["bg"], highlightthickness=0, bd=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.body = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window(padx, pady, window=self.body, anchor="nw")
        self._padx, self._pady = padx, pady
        self.body.bind("<Configure>", self._on_body)
        self.canvas.bind("<Configure>", self._on_canvas)

    def _on_body(self, _e=None):
        self.canvas.configure(height=self.body.winfo_reqheight() + self._pady * 2)
        self._draw()

    def _on_canvas(self, event=None):
        w = (event.width if event else self.canvas.winfo_width()) - self._padx * 2
        self.canvas.itemconfig(self._win, width=max(w, 1))
        self._draw()

    def _draw(self):
        self.canvas.delete("shape")
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 4 or h < 4:
            return
        r = self._radius
        # outer soft halo
        self._round(2, 3, w - 3, h - 2, r + 2, fill="", outline="#0F1622")
        # card body
        self._round(3, 2, w - 4, h - 4, r, fill=self._bg, outline=LINE)
        # accent cap along the top edge
        if self._accent:
            self.canvas.create_line(3 + r, 3, w - 4 - r, 3,
                                    fill=self._accent, width=2, tags="shape")
        self.canvas.tag_lower("shape")

    def _round(self, x1, y1, x2, y2, r, **kw):
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
               x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        self.canvas.create_polygon(pts, smooth=True, tags="shape", width=1, **kw)


def _ghost_button(parent, text, command, accent=CYAN, bg=PANEL, hover=PANEL_HI,
                  font=(FONT_UI, 10, "bold"), padx=20, pady=9):
    b = tk.Button(parent, text=text, font=font, bg=bg, fg=accent, relief="flat",
                  bd=0, cursor="hand2", padx=padx, pady=pady,
                  activebackground=hover, activeforeground=TXT,
                  highlightthickness=1, highlightbackground=LINE, command=command)
    _hover(b, bg, hover, accent, TXT)
    return b


def _solid_button(parent, text, command, bg=VIOLET_DK, hover=VIOLET, fg="#07080D",
                  font=(FONT_UI, 10, "bold"), padx=24, pady=10):
    b = tk.Button(parent, text=text, font=font, bg=bg, fg=fg, relief="flat", bd=0,
                  cursor="hand2", padx=padx, pady=pady, activebackground=hover,
                  activeforeground=fg, highlightthickness=0, command=command)
    _hover(b, bg, hover)
    return b


def _field(parent, show=None, fg=TXT, font=(FONT_UI, 10), accent=CYAN):
    e = tk.Entry(parent, font=font, bg=FIELD, fg=fg, insertbackground=accent,
                 relief="flat", bd=0, highlightthickness=1,
                 highlightbackground=LINE, highlightcolor=accent)
    if show:
        e.configure(show=show)
    return e


class SettingsPanel:
    """
    Settings panel GUI opened via secret keyword.
    - Aurora obsidian theme with side rail navigation
    - Scrollable with mouse wheel
    - Responsive layout
    """

    def __init__(self, database, file_protector, file_watcher,
                 attempt_tracker, keyboard_listener):
        self.database = database
        self.file_protector = file_protector
        self.file_watcher = file_watcher
        self.attempt_tracker = attempt_tracker
        self.keyboard_listener = keyboard_listener
        self.root: Optional[tk.Tk] = None
        self._closed = False

    def show(self):
        """Show the settings panel."""
        if self._closed:
            self._closed = False
        self._create_gui()

    # ============================================================
    # WINDOW / SHELL
    # ============================================================

    def _create_gui(self):
        self.root = tk.Tk()
        self.root.title("SecureGuard — Settings")
        self.root.configure(bg=INK)
        self.root.resizable(True, True)
        self.root.minsize(460, 500)

        window_width = 900
        window_height = 780
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = max((screen_height - window_height) // 2, 0)
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

        shell = tk.Frame(self.root, bg=INK)
        shell.pack(fill=tk.BOTH, expand=True)

        self._create_rail(shell)

        right = tk.Frame(shell, bg=INK)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._create_header(right)

        body = tk.Frame(right, bg=INK)
        body.pack(fill=tk.BOTH, expand=True)

        # ---- Scrollable Canvas ----
        canvas = tk.Canvas(body, bg=INK, highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(
            body, orient="vertical", command=canvas.yview,
            bg=LINE_HI, troughcolor=INK, activebackground=CYAN,
            highlightthickness=0, bd=0, relief="flat", width=8,
        )
        self.scrollable_frame = tk.Frame(canvas, bg=INK)
        self._canvas = canvas

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        self._frame_id = canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        def _on_canvas_resize(event):
            canvas.itemconfig(self._frame_id, width=event.width)
        canvas.bind("<Configure>", _on_canvas_resize)

        # ---- Sections ----
        self._section_anchors = {}
        self._create_protection_section()
        self._create_separator()
        self._create_questions_section()
        self._create_separator()
        self._create_keyword_section()
        self._create_separator()
        self._create_files_section()
        self._create_footer()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    # ------------------------------------------------------------
    # LEFT RAIL (navigation + identity)
    # ------------------------------------------------------------
    def _create_rail(self, parent):
        rail = tk.Frame(parent, bg=INK_DEEP, width=210)
        rail.pack(side=tk.LEFT, fill=tk.Y)
        rail.pack_propagate(False)

        brand = tk.Frame(rail, bg=INK_DEEP, padx=22, pady=26)
        brand.pack(fill=tk.X)

        mark = tk.Canvas(brand, width=38, height=38, bg=INK_DEEP,
                         highlightthickness=0, bd=0)
        mark.pack(anchor="w")
        ramp = _gradient_ramp([CYAN, VIOLET], 38)
        for i, c in enumerate(ramp):
            mark.create_line(0, i, 38, i, fill=c)
        mark.create_text(19, 20, text="SG", fill="#04060B",
                         font=(FONT_UI, 13, "bold"))

        tk.Label(brand, text="SecureGuard", font=(FONT_UI, 14, "bold"),
                 bg=INK_DEEP, fg=TXT).pack(anchor="w", pady=(14, 0))
        tk.Label(brand, text="ghost protection suite", font=(FONT_UI, 8),
                 bg=INK_DEEP, fg=TXT_FAINT).pack(anchor="w", pady=(2, 0))

        GradientStrip(rail, height=1, bg=INK_DEEP).pack(fill=tk.X, padx=22)

        nav = tk.Frame(rail, bg=INK_DEEP, pady=18)
        nav.pack(fill=tk.X)

        items = [
            ("◈", "Protection", "protection", CYAN),
            ("✦", "Decoy Auth", "questions", VIOLET),
            ("⌘", "Keyword", "keyword", AMBER),
            ("▣", "Targets", "files", EMERALD),
        ]
        for icon, label, key, col in items:
            row = tk.Frame(nav, bg=INK_DEEP, cursor="hand2")
            row.pack(fill=tk.X, padx=12, pady=2)
            bar = tk.Frame(row, width=2, bg=INK_DEEP)
            bar.pack(side=tk.LEFT, fill=tk.Y)
            inner = tk.Frame(row, bg=INK_DEEP, padx=12, pady=9)
            inner.pack(side=tk.LEFT, fill=tk.X, expand=True)
            ic = tk.Label(inner, text=icon, font=(FONT_UI, 10), bg=INK_DEEP, fg=col)
            ic.pack(side=tk.LEFT, padx=(0, 10))
            tx = tk.Label(inner, text=label, font=(FONT_UI, 10),
                          bg=INK_DEEP, fg=TXT_SOFT)
            tx.pack(side=tk.LEFT)

            def enter(_e, r=row, i=inner, ic=ic, t=tx, b=bar, c=col):
                for wdg in (r, i, ic, t):
                    wdg.configure(bg=PANEL)
                t.configure(fg=TXT)
                b.configure(bg=c)

            def leave(_e, r=row, i=inner, ic=ic, t=tx, b=bar):
                for wdg in (r, i, ic, t):
                    wdg.configure(bg=INK_DEEP)
                t.configure(fg=TXT_SOFT)
                b.configure(bg=INK_DEEP)

            for wdg in (row, inner, ic, tx):
                wdg.bind("<Enter>", enter)
                wdg.bind("<Leave>", leave)
                wdg.bind("<Button-1>", lambda _e, k=key: self._scroll_to(k))

        # live status chip pinned to bottom of the rail
        chip_wrap = tk.Frame(rail, bg=INK_DEEP, padx=18, pady=20)
        chip_wrap.pack(side=tk.BOTTOM, fill=tk.X)
        self._rail_chip = tk.Label(
            chip_wrap, text="", font=(FONT_UI, 8, "bold"), bg=PANEL,
            fg=TXT_SOFT, padx=12, pady=7, anchor="w"
        )
        self._rail_chip.pack(fill=tk.X)

    def _scroll_to(self, key):
        widget = self._section_anchors.get(key)
        if not widget or not self._canvas:
            return
        self._canvas.update_idletasks()
        top = widget.winfo_y()
        total = max(self.scrollable_frame.winfo_height(), 1)
        self._canvas.yview_moveto(max(min(top / total, 1.0), 0.0))

    def _create_header(self, parent):
        header = tk.Frame(parent, bg=INK_DEEP)
        header.pack(fill=tk.X)

        banner = tk.Canvas(header, height=112, bg=INK_DEEP,
                           highlightthickness=0, bd=0)
        banner.pack(fill=tk.X)

        def _paint(_e=None):
            banner.delete("all")
            w = max(banner.winfo_width(), 1)
            # soft diagonal aurora wash
            ramp = _gradient_ramp(["#05070C", "#0B1520", "#101326", "#05070C"], 80)
            for i, c in enumerate(ramp):
                banner.create_rectangle(i * w / 80, 0, (i + 1) * w / 80 + 1, 112,
                                        fill=c, outline=c)
            for i, c in enumerate(_gradient_ramp(AURORA, 70)):
                banner.create_rectangle(i * w / 70, 109, (i + 1) * w / 70 + 1, 112,
                                        fill=c, outline=c)
            banner.create_text(34, 44, anchor="w", text="Settings",
                               fill=TXT, font=(FONT_UI, 24, "bold"))
            banner.create_text(34, 76, anchor="w",
                               text="Tune the ghost engine · decoys · activation",
                               fill=TXT_SOFT, font=(FONT_UI, 10))
        banner.bind("<Configure>", _paint)

    def _create_separator(self):
        GradientStrip(self.scrollable_frame, height=1,
                      colors=[INK, LINE_HI, INK]).pack(fill=tk.X, padx=34, pady=20)

    def _section_title(self, parent, text, icon="", subtitle="", accent=CYAN, key=None):
        frame = tk.Frame(parent, bg=INK)
        frame.pack(fill=tk.X, padx=34, pady=(18, 12))
        if key:
            self._section_anchors[key] = frame

        row = tk.Frame(frame, bg=INK)
        row.pack(fill=tk.X)

        tk.Label(row, text=icon, font=(FONT_UI, 11), bg=PANEL, fg=accent,
                 padx=8, pady=5).pack(side=tk.LEFT, padx=(0, 12))
        tk.Label(row, text=text.upper(), font=(FONT_UI, 11, "bold"),
                 bg=INK, fg=TXT).pack(side=tk.LEFT)
        tk.Frame(row, height=1, bg=LINE).pack(side=tk.LEFT, fill=tk.X,
                                              expand=True, padx=16)

        if subtitle:
            tk.Label(frame, text=subtitle, font=(FONT_UI, 9),
                     bg=INK, fg=TXT_FAINT).pack(anchor="w", padx=(2, 0), pady=(8, 0))

    # ============================================================
    # PROTECTION STATUS SECTION
    # ============================================================

    def _create_protection_section(self):
        self._section_title(self.scrollable_frame, "System Protection", "◈",
                            "Arm or disarm the ghost monitoring engine.",
                            accent=CYAN, key="protection")

        frame = tk.Frame(self.scrollable_frame, bg=INK, padx=34)
        frame.pack(fill=tk.X)

        is_enabled = self.database.get_protection_enabled()
        status_text = "ARMED & ACTIVE" if is_enabled else "OFFLINE"
        status_color = EMERALD if is_enabled else ROSE

        self._protection_status_var = tk.StringVar(value=status_text)

        card = GlowCard(frame, accent=status_color)
        card.pack(fill=tk.X, pady=4)
        status_frame = card.body

        left = tk.Frame(status_frame, bg=PANEL)
        left.pack(side=tk.LEFT)

        indicator = tk.Label(left, text="●", font=(FONT_UI, 15),
                             bg=PANEL, fg=status_color)
        indicator.pack(side=tk.LEFT)
        self._protection_indicator = indicator

        self._protection_label = tk.Label(
            left, textvariable=self._protection_status_var,
            font=(FONT_UI, 13, "bold"), bg=PANEL, fg=status_color
        )
        self._protection_label.pack(side=tk.LEFT, padx=10)

        # slim telemetry track
        bar_frame = tk.Frame(status_frame, bg=FIELD, height=4)
        bar_frame.pack(side=tk.LEFT, padx=20, fill=tk.X, expand=True, pady=12)
        bar_frame.pack_propagate(False)
        self._status_bar = tk.Frame(bar_frame, bg=status_color, height=4)
        self._status_bar.pack(side=tk.LEFT, fill=tk.Y)
        if is_enabled:
            self._status_bar.configure(width=250)

        self._pulse_on = True
        self._pulse()
        self._sync_chip(is_enabled)

        btn_frame = tk.Frame(frame, bg=INK)
        btn_frame.pack(fill=tk.X, pady=14)

        _solid_button(btn_frame, "◉  ARM SYSTEM", lambda: self._toggle_protection(True),
                      bg=EMERALD_DK, hover=EMERALD).pack(side=tk.LEFT, padx=(0, 10))
        _ghost_button(btn_frame, "○  DISARM", lambda: self._toggle_protection(False),
                      accent=ROSE).pack(side=tk.LEFT)

    def _pulse(self):
        """Purely cosmetic breathing dot."""
        if not self.root or self._closed:
            return
        try:
            base = self._protection_label.cget("fg")
            self._protection_indicator.configure(
                fg=base if self._pulse_on else _lerp_hex(base, PANEL, 0.6))
            self._pulse_on = not self._pulse_on
            self.root.after(700, self._pulse)
        except Exception:
            pass

    def _sync_chip(self, enabled: bool):
        try:
            self._rail_chip.configure(
                text=("●  ENGINE ARMED" if enabled else "●  ENGINE OFFLINE"),
                fg=(EMERALD if enabled else ROSE))
        except Exception:
            pass

    def _toggle_protection(self, enable: bool):
        if self.database.update_settings({"protection_enabled": enable}):
            status = "ARMED & ACTIVE" if enable else "OFFLINE"
            color = EMERALD if enable else ROSE
            self._protection_status_var.set(status)
            self._protection_label.configure(fg=color)
            self._protection_indicator.configure(fg=color)
            self._status_bar.configure(bg=color, width=250 if enable else 0)
            self._sync_chip(enable)
            logger.info(f"Protection {'enabled' if enable else 'disabled'}")

    # ============================================================
    # SECURITY QUESTIONS SECTION
    # ============================================================

    def _create_questions_section(self):
        self._section_title(self.scrollable_frame, "Decoy Authentication", "✦",
                            "Questions shown to anyone trying to open a protected target.",
                            accent=VIOLET, key="questions")

        frame = tk.Frame(self.scrollable_frame, bg=INK, padx=34)
        frame.pack(fill=tk.X)

        questions = self.database.get_security_questions()
        self._question_entries = []
        self._answer_entries_settings = []

        for i, qa in enumerate(questions[:5]):
            q_text = qa.get("question", "")
            a_text = qa.get("answer", "")

            card = GlowCard(frame, padx=16, pady=14, radius=14, accent=VIOLET)
            card.pack(fill=tk.X, pady=5)
            block = card.body

            q_frame = tk.Frame(block, bg=PANEL)
            q_frame.pack(fill=tk.X)

            tk.Label(q_frame, text=f"{i + 1:02d}", font=(FONT_UI, 10, "bold"),
                     bg=PANEL, fg=VIOLET, padx=6).pack(side=tk.LEFT, padx=(0, 12))

            q_entry = _field(q_frame, accent=VIOLET)
            q_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8)
            q_entry.insert(0, q_text)
            self._question_entries.append(q_entry)

            a_frame = tk.Frame(block, bg=PANEL)
            a_frame.pack(fill=tk.X, pady=(8, 0))

            tk.Label(a_frame, text="ANSWER", font=(FONT_UI, 8, "bold"),
                     bg=PANEL, fg=TXT_FAINT).pack(side=tk.LEFT, padx=(6, 12))

            a_entry = _field(a_frame, fg=EMERALD, accent=EMERALD)
            a_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8)
            a_entry.insert(0, a_text)
            self._answer_entries_settings.append(a_entry)

        _solid_button(frame, "SAVE QUESTIONS", self._save_questions,
                      bg=VIOLET_DK, hover=VIOLET).pack(pady=(18, 4), anchor="w")

    def _save_questions(self):
        questions = []
        for i in range(5):
            if i < len(self._question_entries) and i < len(self._answer_entries_settings):
                questions.append({
                    "question": self._question_entries[i].get().strip(),
                    "answer": self._answer_entries_settings[i].get().strip()
                })

        if self.database.update_settings({"questions": questions}):
            messagebox.showinfo("Saved", "Security questions updated successfully!")
        else:
            messagebox.showerror("Error", "Failed to save questions")

    # ============================================================
    # SECRET KEYWORD SECTION
    # ============================================================

    def _create_keyword_section(self):
        self._section_title(self.scrollable_frame, "Ghost Activation Keyword", "⌘",
                            accent=AMBER, key="keyword")

        frame = tk.Frame(self.scrollable_frame, bg=INK, padx=34)
        frame.pack(fill=tk.X)

        current_keyword = self.database.get_secret_keyword()

        card = GlowCard(frame, accent=AMBER)
        card.pack(fill=tk.X, pady=(0, 14))
        body = card.body

        tk.Label(body, text="Type this hidden phrase anywhere on your PC to spawn this window.",
                 font=(FONT_UI, 9), bg=PANEL, fg=TXT_SOFT).pack(anchor="w", pady=(0, 14))

        entry_frame = tk.Frame(body, bg=PANEL)
        entry_frame.pack(fill=tk.X)

        self._keyword_entry = _field(entry_frame, show="•", fg=AMBER,
                                     font=(FONT_UI, 13, "bold"), accent=AMBER)
        self._keyword_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=10, padx=(0, 10))
        self._keyword_entry.insert(0, current_keyword)

        self._keyword_visible = False

        self._toggle_keyword_btn = tk.Button(
            entry_frame, text="◐", font=(FONT_UI, 12),
            bg=FIELD, fg=TXT_SOFT, relief="flat", bd=0, cursor="hand2",
            padx=14, pady=7, highlightthickness=1, highlightbackground=LINE,
            activebackground=LINE_HI, activeforeground=TXT,
            command=self._toggle_keyword_visibility
        )
        self._toggle_keyword_btn.pack(side=tk.RIGHT)

        _solid_button(frame, "UPDATE KEYWORD", self._save_keyword,
                      bg="#B45309", hover=AMBER).pack(anchor="w")

    def _toggle_keyword_visibility(self):
        if self._keyword_visible:
            self._keyword_entry.configure(show="•")
            self._toggle_keyword_btn.configure(bg=FIELD, fg=TXT_SOFT)
        else:
            self._keyword_entry.configure(show="")
            self._toggle_keyword_btn.configure(bg=AMBER, fg="#07080D")
        self._keyword_visible = not self._keyword_visible

    def _save_keyword(self):
        new_keyword = self._keyword_entry.get().strip()
        if not new_keyword:
            messagebox.showwarning("Warning", "Keyword cannot be empty!")
            return
        if len(new_keyword) < 3:
            messagebox.showwarning("Warning", "Keyword must be at least 3 characters!")
            return

        if self.database.update_settings({"secret_keyword": new_keyword}):
            self.keyboard_listener.update_keyword(new_keyword)
            messagebox.showinfo("Saved", "Secret keyword updated!")
        else:
            messagebox.showerror("Error", "Failed to save keyword")

    # ============================================================
    # PROTECTED FILES & FOLDERS SECTION
    # ============================================================

    def _create_files_section(self):
        self._section_title(self.scrollable_frame, "Protected Decoy Targets", "▣",
                            accent=EMERALD, key="files")

        frame = tk.Frame(self.scrollable_frame, bg=INK, padx=34)
        frame.pack(fill=tk.X)

        btn_frame = tk.Frame(frame, bg=INK)
        btn_frame.pack(fill=tk.X, pady=(0, 14))

        _ghost_button(btn_frame, "+   ADD FILE", self._add_file,
                      accent=CYAN).pack(side=tk.LEFT, padx=(0, 10))
        _ghost_button(btn_frame, "+   ADD FOLDER", self._add_folder,
                      accent=EMERALD).pack(side=tk.LEFT)

        self._files_list_frame = tk.Frame(frame, bg=INK)
        self._files_list_frame.pack(fill=tk.X)

        self._refresh_files_list()

    def _refresh_files_list(self):
        for widget in self._files_list_frame.winfo_children():
            widget.destroy()

        files = self.database.get_protected_files(force_refresh=True)

        if not files:
            card = GlowCard(self._files_list_frame, padx=20, pady=26)
            card.pack(fill=tk.X)
            tk.Label(card.body, text="◌   No active decoys. Add files to bait intruders.",
                     font=(FONT_UI, 10), bg=PANEL, fg=TXT_FAINT).pack(anchor="center")
            return

        for f in files:
            blocked = f.get("is_blocked", False)
            accent = ROSE if blocked else (EMERALD if f.get("file_type") == "folder" else CYAN)

            card = GlowCard(self._files_list_frame, padx=16, pady=13,
                            radius=13, accent=accent)
            card.pack(fill=tk.X, pady=5)
            row = card.body

            icon = "▤" if blocked else ("▣" if f.get("file_type") == "folder" else "▢")

            tk.Label(row, text=icon, font=(FONT_UI, 14),
                     bg=PANEL, fg=accent).pack(side=tk.LEFT, padx=(2, 14))

            tk.Button(
                row, text="✕", font=(FONT_UI, 10, "bold"),
                bg=PANEL, fg=TXT_FAINT, relief="flat", bd=0, cursor="hand2",
                activebackground="#2A0F17", activeforeground=ROSE,
                padx=8, highlightthickness=0,
                command=lambda p=f["path"]: self._remove_file(p)
            ).pack(side=tk.RIGHT, padx=(8, 2))

            if blocked:
                tk.Label(row, text="BLOCKED", font=(FONT_UI, 8, "bold"),
                         bg="#2A0F17", fg=ROSE, padx=10, pady=3
                         ).pack(side=tk.RIGHT, padx=10)

            name_frame = tk.Frame(row, bg=PANEL)
            name_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

            tk.Label(name_frame, text=f["file_name"], font=(FONT_UI, 10, "bold"),
                     bg=PANEL, fg=TXT, anchor="w").pack(fill=tk.X)

            tk.Label(name_frame, text=f["path"], font=(FONT_UI, 8),
                     bg=PANEL, fg=TXT_FAINT, anchor="w").pack(fill=tk.X)

    def _add_file(self):
        file_path = filedialog.askopenfilename(title="Select file to block/protect")
        if not file_path:
            return
        file_path = os.path.normpath(file_path)
        if not os.path.exists(file_path):
            messagebox.showerror("Error", "File does not exist!")
            return
        if self.file_protector.protect_file(file_path):
            file_name = os.path.basename(file_path)
            added = self.database.add_protected_file(file_path, file_name, "file")
            if added:
                self._refresh_files_list()
                messagebox.showinfo("Success", f"File protected: {file_name}")
            else:
                self._refresh_files_list()
                messagebox.showwarning(
                    "Notice",
                    f"File protected locally but failed to add to monitor list "
                    f"(it may already be monitored): {file_name}"
                )
        else:
            messagebox.showerror("Error", "Failed to protect file")

    def _add_folder(self):
        folder_path = filedialog.askdirectory(title="Select folder to track")
        if not folder_path:
            return
        folder_path = os.path.normpath(folder_path)
        if not os.path.isdir(folder_path):
            messagebox.showerror("Error", "Folder does not exist!")
            return
        count = self.file_protector.protect_folder(folder_path)
        folder_name = os.path.basename(folder_path)
        self.database.add_protected_file(folder_path, folder_name, "folder")
        self.file_watcher.watch_folder(folder_path)
        self._refresh_files_list()
        messagebox.showinfo("Success", f"Folder protected: {folder_name} ({count} files)")

    def _remove_file(self, path: str):
        confirm = messagebox.askyesno("Confirm", f"Remove protection from:\n{path}?")
        if not confirm:
            return
        self.file_protector.remove_protection(path)
        self.database.remove_protected_file(path)
        self.attempt_tracker.reset(path)
        self.file_watcher.unwatch_folder(path)
        self._refresh_files_list()
        logger.info(f"Removed from protection: {path}")

    # ============================================================
    # FOOTER
    # ============================================================

    def _create_footer(self):
        footer = tk.Frame(self.scrollable_frame, bg=INK, pady=24, padx=34)
        footer.pack(fill=tk.X, pady=(26, 0))

        GradientStrip(footer, height=1, colors=[INK, LINE_HI, INK]).pack(
            fill=tk.X, pady=(0, 18))

        from config import SOFTWARE_VERSION
        tk.Label(footer, text=f"SECUREGUARD GHOST SYSTEM   ·   v{SOFTWARE_VERSION}",
                 font=(FONT_UI, 9, "bold"), bg=INK, fg=TXT_SOFT).pack(anchor="center")
        tk.Label(footer, text="protected  ·  silent  ·  always watching",
                 font=(FONT_UI, 8), bg=INK, fg=TXT_FAINT).pack(anchor="center", pady=(5, 0))

    def _on_close(self):
        self._closed = True
        try:
            self.root.destroy()
        except Exception:
            pass
