"""
SecureGuard PC Software — Settings Panel
Beautiful premium dark themed settings GUI with indigo/slate accents.
Scrollable, responsive, syncs with Supabase.
"""

import os
import logging
import tkinter as tk
from tkinter import font as tkfont, filedialog, messagebox
from typing import Optional, Callable

logger = logging.getLogger("SecureGuard.SettingsPanel")

# --- UI THEME CONSTANTS ---
BG_MAIN = "#0B1120"       # Deep Slate Background
BG_CARD = "#1E293B"       # Elevated Card Background
BG_INPUT = "#0F172A"      # Input Field Background
BG_HEADER = "#090E17"     # Deep Header

FG_PRIMARY = "#F8FAFC"    # Bright White Text 
FG_MUTED = "#94A3B8"      # Muted Slate Text

ACCENT_INDIGO = "#6366F1" # Brand Indigo
ACCENT_GREEN = "#10B981"  # Success Green
ACCENT_RED = "#EF4444"    # Danger Red

BORDER_COLOR = "#334155"  # Lines and Borders

class SettingsPanel:
    """
    Settings panel GUI opened via secret keyword.
    - Gorgeous slate dark theme
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

    def _create_gui(self):
        """Create the settings panel window."""
        self.root = tk.Tk()
        self.root.title("SecureGuard — Settings")
        self.root.configure(bg=BG_MAIN)
        self.root.resizable(True, True)
        self.root.minsize(350, 400)

        window_width = 650
        window_height = 700
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # ---- Scrollable Canvas ----
        canvas = tk.Canvas(self.root, bg=BG_MAIN, highlightthickness=0)
        scrollbar = tk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        # Hack to color the scrollbar frame via container bg
        self.scrollable_frame = tk.Frame(canvas, bg=BG_MAIN)

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
        self._create_header()
        self._create_protection_section()
        self._create_separator()
        self._create_questions_section()
        self._create_separator()
        self._create_keyword_section()
        self._create_separator()
        self._create_files_section()
        self._create_footer()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Run
        self.root.mainloop()

    def _create_header(self):
        header = tk.Frame(self.scrollable_frame, bg=BG_HEADER, pady=25, padx=30)
        header.pack(fill=tk.X)

        title_font = tkfont.Font(family="Segoe UI", size=22, weight="bold")
        tk.Label(
            header, text="🛡️ SecureGuard Settings",
            font=title_font, bg=BG_HEADER, fg=FG_PRIMARY
        ).pack(anchor="center")

        tk.Label(
            header, text="Configure your ultimate file protection system.",
            font=("Segoe UI", 10), bg=BG_HEADER, fg=ACCENT_INDIGO
        ).pack(anchor="center", pady=(5, 0))

        # Bottom elegant border
        tk.Frame(header, height=3, bg=ACCENT_INDIGO).pack(fill=tk.X, pady=(15, 0))

    def _create_separator(self):
        tk.Frame(self.scrollable_frame, height=1, bg=BORDER_COLOR).pack(fill=tk.X, padx=30, pady=15)

    def _section_title(self, parent, text, icon=""):
        frame = tk.Frame(parent, bg=BG_MAIN)
        frame.pack(fill=tk.X, padx=30, pady=(10, 10))
        tk.Label(
            frame, text=f"{icon} {text}",
            font=("Segoe UI", 13, "bold"), bg=BG_MAIN, fg=FG_PRIMARY
        ).pack(anchor="w")

    # ============================================================
    # PROTECTION STATUS SECTION
    # ============================================================

    def _create_protection_section(self):
        self._section_title(self.scrollable_frame, "System Protection", "🔒")

        frame = tk.Frame(self.scrollable_frame, bg=BG_MAIN, padx=30)
        frame.pack(fill=tk.X)

        is_enabled = self.database.get_protection_enabled()
        status_text = "ARMED & ACTIVE" if is_enabled else "OFFLINE"
        status_color = ACCENT_GREEN if is_enabled else ACCENT_RED

        self._protection_status_var = tk.StringVar(value=status_text)

        status_frame = tk.Frame(frame, bg=BG_CARD, padx=15, pady=15, highlightthickness=1, highlightbackground=BORDER_COLOR)
        status_frame.pack(fill=tk.X, pady=5)

        indicator = tk.Label(
            status_frame, text="●", font=("Segoe UI", 16),
            bg=BG_CARD, fg=status_color
        )
        indicator.pack(side=tk.LEFT)
        self._protection_indicator = indicator

        self._protection_label = tk.Label(
            status_frame, textvariable=self._protection_status_var,
            font=("Segoe UI", 12, "bold"), bg=BG_CARD, fg=status_color
        )
        self._protection_label.pack(side=tk.LEFT, padx=10)

        # Techy tracking bar
        bar_frame = tk.Frame(status_frame, bg=BG_INPUT, height=4, width=250)
        bar_frame.pack(side=tk.LEFT, padx=15, fill=tk.X, expand=True)
        bar_frame.pack_propagate(False)
        self._status_bar = tk.Frame(bar_frame, bg=status_color, height=4)
        self._status_bar.pack(side=tk.LEFT, fill=tk.Y)
        if is_enabled:
            self._status_bar.configure(width=250)

        btn_frame = tk.Frame(frame, bg=BG_MAIN)
        btn_frame.pack(fill=tk.X, pady=10)

        tk.Button(
            btn_frame, text="Turn ON", font=("Segoe UI", 10, "bold"),
            bg=ACCENT_GREEN, fg="#FFFFFF", relief="flat", cursor="hand2",
            padx=25, pady=8, activebackground="#059669", activeforeground="#FFFFFF",
            command=lambda: self._toggle_protection(True)
        ).pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(
            btn_frame, text="Turn OFF", font=("Segoe UI", 10, "bold"),
            bg=ACCENT_RED, fg="#FFFFFF", relief="flat", cursor="hand2",
            padx=25, pady=8, activebackground="#DC2626", activeforeground="#FFFFFF",
            command=lambda: self._toggle_protection(False)
        ).pack(side=tk.LEFT)

    def _toggle_protection(self, enable: bool):
        if self.database.update_settings({"protection_enabled": enable}):
            status = "ARMED & ACTIVE" if enable else "OFFLINE"
            color = ACCENT_GREEN if enable else ACCENT_RED
            self._protection_status_var.set(status)
            self._protection_label.configure(fg=color)
            self._protection_indicator.configure(fg=color)
            self._status_bar.configure(bg=color, width=250 if enable else 0)
            logger.info(f"Protection {'enabled' if enable else 'disabled'}")

    # ============================================================
    # SECURITY QUESTIONS SECTION
    # ============================================================

    def _create_questions_section(self):
        self._section_title(self.scrollable_frame, "Decoy Authentication", "❓")

        frame = tk.Frame(self.scrollable_frame, bg=BG_MAIN, padx=30)
        frame.pack(fill=tk.X)

        questions = self.database.get_security_questions()
        self._question_entries = []
        self._answer_entries_settings = []

        card_wrapper = tk.Frame(frame, bg=BG_CARD, padx=20, pady=15, highlightthickness=1, highlightbackground=BORDER_COLOR)
        card_wrapper.pack(fill=tk.X)

        for i, qa in enumerate(questions[:5]):
            q_text = qa.get("question", "")
            a_text = qa.get("answer", "")

            q_frame = tk.Frame(card_wrapper, bg=BG_CARD)
            q_frame.pack(fill=tk.X, pady=(10, 2))

            badge = tk.Label(
                q_frame, text=f"Q{i + 1}", font=("Segoe UI", 9, "bold"),
                bg=ACCENT_INDIGO, fg="#FFFFFF", padx=8, pady=2
            )
            badge.pack(side=tk.LEFT, padx=(0, 10))

            q_entry = tk.Entry(
                q_frame, font=("Segoe UI", 10), bg=BG_INPUT, fg=FG_PRIMARY,
                insertbackground=FG_PRIMARY, relief="flat",
                highlightthickness=1, highlightbackground=BORDER_COLOR, highlightcolor=ACCENT_INDIGO
            )
            q_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)
            q_entry.insert(0, q_text)
            self._question_entries.append(q_entry)

            a_frame = tk.Frame(card_wrapper, bg=BG_CARD)
            a_frame.pack(fill=tk.X, pady=(2, 8))

            tk.Label(
                a_frame, text="↳ Ans:", font=("Segoe UI", 9, "bold"), bg=BG_CARD, fg=FG_MUTED
            ).pack(side=tk.LEFT, padx=(38, 10))

            a_entry = tk.Entry(
                a_frame, font=("Segoe UI", 10), bg=BG_INPUT, fg=ACCENT_GREEN,
                insertbackground=FG_PRIMARY, relief="flat",
                highlightthickness=1, highlightbackground=BORDER_COLOR, highlightcolor=ACCENT_INDIGO
            )
            a_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)
            a_entry.insert(0, a_text)
            self._answer_entries_settings.append(a_entry)

        tk.Button(
            frame, text="💾 Save Questions", font=("Segoe UI", 10, "bold"),
            bg=ACCENT_INDIGO, fg="#FFFFFF", relief="flat", cursor="hand2",
            padx=20, pady=8, activebackground="#4F46E5", activeforeground="#FFFFFF",
            command=self._save_questions
        ).pack(pady=(15, 5), anchor="w")

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
        self._section_title(self.scrollable_frame, "Ghost Activation Keyword", "🔑")

        frame = tk.Frame(self.scrollable_frame, bg=BG_MAIN, padx=30)
        frame.pack(fill=tk.X)

        current_keyword = self.database.get_secret_keyword()

        card = tk.Frame(frame, bg=BG_CARD, padx=20, pady=15, highlightthickness=1, highlightbackground=BORDER_COLOR)
        card.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            card, text="Type this entirely hidden phrase anywhere on your PC to spawn this window:",
            font=("Segoe UI", 9), bg=BG_CARD, fg=FG_MUTED
        ).pack(anchor="w", pady=(0, 10))

        entry_frame = tk.Frame(card, bg=BG_CARD)
        entry_frame.pack(fill=tk.X)

        self._keyword_entry = tk.Entry(
            entry_frame, font=("Segoe UI", 12, "bold"), bg=BG_INPUT, fg=ACCENT_INDIGO,
            insertbackground=FG_PRIMARY, relief="flat",
            highlightthickness=1, highlightbackground=BORDER_COLOR, highlightcolor=ACCENT_INDIGO, show="●"
        )
        self._keyword_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=(0, 10))
        self._keyword_entry.insert(0, current_keyword)

        self._keyword_visible = False

        self._toggle_keyword_btn = tk.Button(
            entry_frame, text="👁️", font=("Segoe UI", 12),
            bg=BORDER_COLOR, fg=FG_PRIMARY, relief="flat", cursor="hand2", padx=8, pady=3,
            command=self._toggle_keyword_visibility
        )
        self._toggle_keyword_btn.pack(side=tk.RIGHT)

        tk.Button(
            frame, text="💾 Update Keyword", font=("Segoe UI", 10, "bold"),
            bg=ACCENT_INDIGO, fg="#FFFFFF", relief="flat", cursor="hand2",
            padx=20, pady=8, activebackground="#4F46E5", activeforeground="#FFFFFF",
            command=self._save_keyword
        ).pack(anchor="w")

    def _toggle_keyword_visibility(self):
        if self._keyword_visible:
            self._keyword_entry.configure(show="●")
            self._toggle_keyword_btn.configure(bg=BORDER_COLOR)
        else:
            self._keyword_entry.configure(show="")
            self._toggle_keyword_btn.configure(bg=ACCENT_INDIGO)
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
        self._section_title(self.scrollable_frame, "Protected Decoy Targets", "📁")

        frame = tk.Frame(self.scrollable_frame, bg=BG_MAIN, padx=30)
        frame.pack(fill=tk.X)

        btn_frame = tk.Frame(frame, bg=BG_MAIN)
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Button(
            btn_frame, text="+ Add File", font=("Segoe UI", 9, "bold"),
            bg=BG_CARD, fg=FG_PRIMARY, relief="flat", cursor="hand2",
            highlightthickness=1, highlightbackground=BORDER_COLOR,
            padx=18, pady=6, activebackground=BORDER_COLOR, activeforeground=FG_PRIMARY,
            command=self._add_file
        ).pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(
            btn_frame, text="+ Add Folder", font=("Segoe UI", 9, "bold"),
            bg=BG_CARD, fg=FG_PRIMARY, relief="flat", cursor="hand2",
            highlightthickness=1, highlightbackground=BORDER_COLOR,
            padx=18, pady=6, activebackground=BORDER_COLOR, activeforeground=FG_PRIMARY,
            command=self._add_folder
        ).pack(side=tk.LEFT)

        self._files_list_frame = tk.Frame(frame, bg=BG_MAIN)
        self._files_list_frame.pack(fill=tk.X)

        self._refresh_files_list()

    def _refresh_files_list(self):
        for widget in self._files_list_frame.winfo_children():
            widget.destroy()

        files = self.database.get_protected_files(force_refresh=True)

        if not files:
            card = tk.Frame(self._files_list_frame, bg=BG_CARD, padx=20, pady=20, highlightthickness=1, highlightbackground=BORDER_COLOR)
            card.pack(fill=tk.X)
            tk.Label(
                card, text="No active decoys detected. Add files to bait intruders.",
                font=("Segoe UI", 10, "italic"), bg=BG_CARD, fg=FG_MUTED
            ).pack()
            return

        for f in files:
            row = tk.Frame(self._files_list_frame, bg=BG_CARD, padx=15, pady=10, highlightthickness=1, highlightbackground=BORDER_COLOR)
            row.pack(fill=tk.X, pady=3)

            icon = "📁" if f.get("file_type") == "folder" else "📄"
            blocked = f.get("is_blocked", False)
            if blocked:
                icon = "🔒"

            tk.Label(
                row, text=icon, font=("Segoe UI Emoji", 14), bg=BG_CARD, fg=ACCENT_INDIGO
            ).pack(side=tk.LEFT, padx=(0, 12))

            name_frame = tk.Frame(row, bg=BG_CARD)
            name_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

            tk.Label(
                name_frame, text=f["file_name"],
                font=("Segoe UI", 10, "bold"), bg=BG_CARD, fg=FG_PRIMARY,
                anchor="w"
            ).pack(fill=tk.X)

            tk.Label(
                name_frame, text=f["path"],
                font=("Segoe UI", 8), bg=BG_CARD, fg=FG_MUTED,
                anchor="w"
            ).pack(fill=tk.X)

            if blocked:
                tk.Label(
                    row, text="BLOCKED", font=("Segoe UI", 8, "bold"),
                    bg="#450a0a", fg="#fca5a5", padx=8, pady=3
                ).pack(side=tk.RIGHT, padx=10)

            tk.Button(
                row, text="✕", font=("Segoe UI", 10, "bold"),
                bg=BG_CARD, fg=ACCENT_RED, relief="flat", cursor="hand2",
                activebackground="#450a0a", activeforeground=ACCENT_RED,
                padx=8, command=lambda p=f["path"]: self._remove_file(p)
            ).pack(side=tk.RIGHT)

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
            self.database.add_protected_file(file_path, file_name, "file")
            self._refresh_files_list()
            messagebox.showinfo("Success", f"File protected: {file_name}")
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
        footer = tk.Frame(self.scrollable_frame, bg=BG_MAIN, pady=20, padx=30)
        footer.pack(fill=tk.X, pady=(20, 0))

        tk.Frame(footer, height=1, bg=BORDER_COLOR).pack(fill=tk.X, pady=(0, 15))

        from config import SOFTWARE_VERSION
        tk.Label(
            footer, text=f"SecureGuard Ghost System v{SOFTWARE_VERSION}",
            font=("Segoe UI", 9, "bold"), bg=BG_MAIN, fg=BORDER_COLOR
        ).pack(anchor="center")

    def _on_close(self):
        self._closed = True
        try:
            self.root.destroy()
        except Exception:
            pass
