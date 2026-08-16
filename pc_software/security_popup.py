"""
SecureGuard PC Software — Security Questions Popup

"""

import time
import logging
import threading
import tkinter as tk
from tkinter import font as tkfont
from typing import Optional, Callable

from config import POPUP_DENY_DELAY, POPUP_GRANT_DELAY

logger = logging.getLogger("SecureGuard.SecurityPopup")


# ---------------------------------------------------------------- palette ---
PAPER      = "#F6F3EC"   # warm off-white canvas
PAPER_SOFT = "#FFFDF8"   # raised card
INK        = "#12213A"   # deep navy ink
INK_SOFT   = "#5A6A80"   # muted ink
RULE       = "#E2DCCF"   # hairline rule
AMBER      = "#C8862B"   # seal / accent
AMBER_DEEP = "#A76D18"
CRIMSON    = "#A62B2B"   # alerts
GREEN      = "#2E7D5B"   # success
FIELD      = "#FFFFFF"
FIELD_LINE = "#D9D2C4"


class RoundButton(tk.Canvas):
    """Flat rounded 'wax seal' button drawn on a canvas (pure tk, no ttk)."""

    def __init__(self, master, text, command, width=260, height=46,
                 fill=INK, hover=AMBER_DEEP, fg=PAPER_SOFT, bg=PAPER):
        super().__init__(master, width=width, height=height, bg=bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self._command = command
        self._fill, self._hover = fill, hover
        self._state = tk.NORMAL
        r = height // 2
        self._shape = [
            self.create_oval(0, 0, height, height, fill=fill, outline=fill),
            self.create_oval(width - height, 0, width, height, fill=fill, outline=fill),
            self.create_rectangle(r, 0, width - r, height, fill=fill, outline=fill),
        ]
        self._label = self.create_text(width // 2, height // 2, text=text,
                                       fill=fg, font=("Segoe UI Semibold", 11))
        self.bind("<Enter>", lambda e: self._paint(self._hover))
        self.bind("<Leave>", lambda e: self._paint(self._fill))
        self.bind("<Button-1>", self._click)

    def _paint(self, color):
        if self._state != tk.NORMAL:
            return
        for item in self._shape:
            self.itemconfig(item, fill=color, outline=color)

    def _click(self, _event=None):
        if self._state == tk.NORMAL and self._command:
            self._command()

    def configure(self, **kwargs):          # keeps `state=tk.NORMAL` calls working
        if "state" in kwargs:
            self._state = kwargs.pop("state")
            color = self._fill if self._state == tk.NORMAL else "#B9B2A5"
            for item in self._shape:
                self.itemconfig(item, fill=color, outline=color)
            self.configure_cursor()
        if "text" in kwargs:
            self.itemconfig(self._label, text=kwargs.pop("text"))
        if kwargs:
            super().configure(**kwargs)

    config = configure

    def configure_cursor(self):
        super().configure(cursor="hand2" if self._state == tk.NORMAL else "arrow")


class SecurityPopup:
    """
    Security questions popup that appears when a protected file is accessed.
    - Vault-ledger visual theme
    - 5 security questions with masked answer fields
    - Polls owner decision from database
    - Responds to Allow/Deny/Auto-deny
    """

    def __init__(self, database, file_name: str, file_path: str, incident_id: str,
                 on_granted: Callable, on_denied: Callable, on_blocked: Callable):
        self.database = database
        self.file_name = file_name
        self.file_path = file_path
        self.incident_id = incident_id
        self.on_granted = on_granted
        self.on_denied = on_denied
        self.on_blocked = on_blocked

        self._owner_decision: Optional[str] = None
        self._polling = True
        self._closed = False
        self._attempt_count = 0
        self._max_attempts = database.get_max_attempts()
        self._timeout = database.get_alert_timeout()
        self._questions = database.get_security_questions()
        self._start_time = time.time()

        self.root: Optional[tk.Tk] = None
        self._answer_entries = []

    def show(self):
        """Show the security popup — blocks until closed."""
        poll_thread = threading.Thread(target=self._poll_owner_decision, daemon=True)
        poll_thread.start()

        timeout_thread = threading.Thread(target=self._timeout_timer, daemon=True)
        timeout_thread.start()

        self._create_gui()

    # ------------------------------------------------------------- drawing --
    def _draw_crest(self, parent):
        """Hand-drawn shield crest — no emoji, crisp on every DPI."""
        c = tk.Canvas(parent, width=58, height=64, bg=PAPER,
                      highlightthickness=0, bd=0)
        c.create_polygon(29, 4, 53, 14, 53, 34, 29, 60, 5, 34, 5, 14,
                         fill=INK, outline=INK)
        c.create_polygon(29, 11, 47, 18, 47, 33, 29, 52, 11, 33, 11, 18,
                         fill="", outline=AMBER, width=1)
        c.create_line(29, 22, 29, 40, fill=AMBER, width=3)
        c.create_oval(25, 16, 33, 24, fill=AMBER, outline=AMBER)
        return c

    def _rule(self, parent, pad=0, color=RULE):
        line = tk.Frame(parent, height=1, bg=color)
        line.pack(fill=tk.X, padx=pad)
        return line

    def _create_gui(self):
        """Create the tkinter popup window."""
        self.root = tk.Tk()
        self.root.title("SecureGuard — Security Verification")
        self.root.overrideredirect(False)
        self.root.attributes("-topmost", True)
        self.root.resizable(False, False)

        window_width = 560
        window_height = 660
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

        self.root.configure(bg=INK)          # ink border showing through
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)

        # Left accent rail + paper canvas
        rail = tk.Frame(self.root, bg=AMBER, width=6)
        rail.pack(side=tk.LEFT, fill=tk.Y)

        shell = tk.Frame(self.root, bg=PAPER)
        shell.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # ---- Header ----
        header = tk.Frame(shell, bg=PAPER, padx=28, pady=18)
        header.pack(fill=tk.X)

        crest_row = tk.Frame(header, bg=PAPER)
        crest_row.pack(fill=tk.X)

        self._draw_crest(crest_row).pack(side=tk.LEFT)

        titles = tk.Frame(crest_row, bg=PAPER)
        titles.pack(side=tk.LEFT, padx=(14, 0), anchor="w")

        tk.Label(titles, text="S E C U R E G U A R D",
                 font=("Consolas", 9), bg=PAPER, fg=AMBER_DEEP).pack(anchor="w")

        title_font = tkfont.Font(family="Georgia", size=17, weight="bold")
        tk.Label(titles, text="Security Verification",
                 font=title_font, bg=PAPER, fg=INK).pack(anchor="w", pady=(2, 0))

        tk.Label(titles, text="Protected file access request",
                 font=("Segoe UI", 9), bg=PAPER, fg=INK_SOFT).pack(anchor="w")

        # File chip
        chip = tk.Frame(header, bg="#F4E7DA", highlightbackground="#E3C9AE",
                        highlightthickness=1)
        chip.pack(fill=tk.X, pady=(16, 0))
        tk.Label(chip, text="FILE", font=("Consolas", 8, "bold"),
                 bg=AMBER, fg=PAPER_SOFT, padx=8, pady=4).pack(side=tk.LEFT)
        tk.Label(chip, text=f"  {self.file_name}",
                 font=("Consolas", 10, "bold"), bg="#F4E7DA", fg=CRIMSON,
                 anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True, pady=4)

        self._rule(shell, pad=28)

        # ---- Questions ----
        questions_frame = tk.Frame(shell, bg=PAPER, padx=28, pady=14)
        questions_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(questions_frame, text="IDENTITY LEDGER",
                 font=("Consolas", 8, "bold"), bg=PAPER, fg=INK_SOFT,
                 anchor="w").pack(fill=tk.X, pady=(0, 6))

        q_font = tkfont.Font(family="Segoe UI", size=9, weight="bold")
        a_font = tkfont.Font(family="Consolas", size=11)

        self._answer_entries = []

        for i, qa in enumerate(self._questions[:5]):
            question = qa.get("question", f"Question {i + 1}")

            card = tk.Frame(questions_frame, bg=PAPER_SOFT,
                            highlightbackground=RULE, highlightthickness=1)
            card.pack(fill=tk.X, pady=4)

            stripe = tk.Frame(card, bg=INK, width=3)
            stripe.pack(side=tk.LEFT, fill=tk.Y)

            body = tk.Frame(card, bg=PAPER_SOFT, padx=12, pady=9)
            body.pack(side=tk.LEFT, fill=tk.X, expand=True)

            q_row = tk.Frame(body, bg=PAPER_SOFT)
            q_row.pack(fill=tk.X)

            tk.Label(q_row, text=f"{i + 1:02d}", font=("Consolas", 9, "bold"),
                     bg=PAPER_SOFT, fg=AMBER_DEEP).pack(side=tk.LEFT, padx=(0, 8))

            tk.Label(q_row, text=question, font=q_font, bg=PAPER_SOFT,
                     fg=INK, anchor="w").pack(side=tk.LEFT, fill=tk.X)

            entry = tk.Entry(
                body, show="•", font=a_font,
                bg=FIELD, fg=INK, relief="flat",
                highlightbackground=FIELD_LINE, highlightcolor=AMBER,
                highlightthickness=1, insertbackground=INK
            )
            entry.pack(fill=tk.X, ipady=5, pady=(7, 0))
            self._answer_entries.append(entry)

        # ---- Status ----
        status_wrap = tk.Frame(shell, bg=PAPER, padx=28)
        status_wrap.pack(fill=tk.X)

        self._rule(status_wrap)

        self._status_label = tk.Label(
            status_wrap, text="Waiting for owner's response...",
            font=("Segoe UI", 10), bg=PAPER, fg=INK_SOFT
        )
        self._status_label.pack(pady=(10, 0))

        self._attempts_label = tk.Label(
            status_wrap, text="",
            font=("Consolas", 9, "bold"), bg=PAPER, fg=CRIMSON
        )
        self._attempts_label.pack()

        # ---- Submit ----
        btn_frame = tk.Frame(shell, bg=PAPER, pady=14)
        btn_frame.pack(fill=tk.X)

        self._submit_btn = RoundButton(
            btn_frame, text="SUBMIT ANSWERS", command=self._on_submit,
            width=280, height=46, fill=INK, hover=AMBER_DEEP,
            fg=PAPER_SOFT, bg=PAPER
        )
        self._submit_btn.pack()

        tk.Label(shell, text="This window cannot be dismissed until a decision is made.",
                 font=("Segoe UI", 8), bg=PAPER, fg="#9B9282").pack(pady=(0, 12))

        if self._answer_entries:
            self._answer_entries[0].focus_set()

        self.root.bind("<Return>", lambda e: self._on_submit())

        self.root.after(500, self._check_decision_update)

        try:
            self.root.mainloop()
        except Exception as e:
            logger.error(f"Popup loop error: {e}", exc_info=True)
        finally:
            try:
                if self.root and self.root.winfo_exists():
                    self.root.destroy()
            except Exception:
                pass

    # ------------------------------------------------------------- logic ----
    def _on_submit(self):
        """Handle answer submission."""
        if self._owner_decision != "allow":
            self._status_label.configure(text="Waiting for owner to allow access first...")
            return

        if not self._questions:
            self._status_label.configure(text="No security questions configured!")
            self._status_label.configure(fg=CRIMSON)
            self._attempts_label.configure(text="Configure questions in settings first.")
            self.root.after(1500, self._close_and_deny)
            return

        answers_correct = self._verify_answers()

        if answers_correct:
            self._status_label.configure(text="Access granted")
            self._status_label.configure(fg=GREEN)

            self.database.update_incident(self.incident_id, {
                "action": "ALLOWED",
                "answers_correct": True,
                "responded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            })

            self.root.after(POPUP_GRANT_DELAY, self._close_and_grant)
        else:
            self._attempt_count += 1
            remaining = self._max_attempts - self._attempt_count

            if remaining > 0:
                self._attempts_label.configure(
                    text=f"WRONG ANSWERS — {remaining} ATTEMPT(S) REMAINING")
                for entry in self._answer_entries:
                    entry.delete(0, tk.END)
                if self._answer_entries:
                    self._answer_entries[0].focus_set()

                self.database.update_attempt_count(self.file_path, self._attempt_count)
            else:
                self._status_label.configure(text="File blocked permanently")
                self._status_label.configure(fg=CRIMSON)
                self._attempts_label.configure(
                    text=f"MAXIMUM ATTEMPTS ({self._max_attempts}) EXCEEDED")

                self.database.update_incident(self.incident_id, {
                    "action": "BLOCKED",
                    "answers_correct": False,
                    "responded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                })
                self.database.block_file(self.file_path)

                self.root.after(1500, self._close_and_block)

    def _verify_answers(self) -> bool:
        """Check submitted answers against stored answers."""
        if not self._questions:
            return False

        for i, qa in enumerate(self._questions[:5]):
            if i >= len(self._answer_entries):
                break
            expected = qa.get("answer", "").strip().lower()
            submitted = self._answer_entries[i].get().strip().lower()
            if expected and submitted != expected:
                return False
        return True

    def _poll_owner_decision(self):
        """Background thread: poll Supabase for owner's decision."""
        consecutive_errors = 0
        max_errors = 10

        while self._polling and not self._closed:
            try:
                decision = self.database.get_owner_decision(self.incident_id)
                if decision is not None:
                    self._owner_decision = decision
                    logger.info(f"Owner decision received: {decision}")
                    consecutive_errors = 0

                    if decision == "deny":
                        self._polling = False
                    elif decision == "allow":
                        self._polling = False
                    break
                else:
                    consecutive_errors = 0
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Error polling decision ({consecutive_errors}/{max_errors}): {e}")

                if consecutive_errors >= max_errors:
                    logger.error(f"Max poll errors reached — auto-denying {self.incident_id}")
                    self._owner_decision = "auto_deny"
                    self._polling = False
                    break

            time.sleep(0.5)

    def _check_decision_update(self):
        """Called periodically from GUI thread to respond to owner decision."""
        if self._closed:
            return

        if self._owner_decision == 'allow':
            self._status_label.configure(text="Owner approved — enter your answers below")
            self._status_label.configure(fg=GREEN)
            self._submit_btn.configure(state=tk.NORMAL)
        elif self._owner_decision == 'deny':
            self._status_label.configure(text="Access denied by owner")
            self._status_label.configure(fg=CRIMSON)
            self._attempts_label.configure(text="CLOSING FILE...")
            self.root.after(POPUP_DENY_DELAY, self._close_and_deny)
            return
        elif self._owner_decision == 'auto_deny':
            self._handle_auto_deny()
            return

        elapsed = time.time() - self._start_time
        remaining = max(0, self._timeout - elapsed)

        if remaining <= 0:
            self._handle_auto_deny()
            return

        if self._owner_decision is None:
            self._status_label.configure(
                text=f"Awaiting owner decision — {int(remaining)}s remaining")

        self.root.after(500, self._check_decision_update)

    def _handle_auto_deny(self):
        """Handle auto-deny after timeout."""
        logger.info(f"Auto-denying access for {self.file_path}")

        self._status_label.configure(text="Auto-denied — owner did not respond")
        self._status_label.configure(fg=CRIMSON)
        self._attempts_label.configure(text="CLOSING FILE...")

        self.database.update_incident(self.incident_id, {
            "action": "AUTO_DENIED",
            "auto_denied": True,
            "responded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        })

        self.root.after(POPUP_DENY_DELAY, self._close_and_deny)

    def _timeout_timer(self):
        """Background thread: auto-deny after timeout."""
        time.sleep(self._timeout)
        if self._owner_decision is None and not self._closed:
            logger.info(f"Auto-denying incident {self.incident_id} after {self._timeout}s timeout")
            self._owner_decision = "auto_deny"

    def _safe_destroy(self):
        """Safely destroy the tkinter window, cancelling all pending after() callbacks."""
        try:
            for after_id in self.root.tk.call('after', 'info'):
                try:
                    self.root.after_cancel(after_id)
                except Exception:
                    pass
            self.root.destroy()

            self.root = None
            self._answer_entries = []
            self._status_label = None
            self._attempts_label = None
            self._submit_btn = None
        except Exception:
            pass

    def _close_and_grant(self):
        """Close popup and trigger granted callback."""
        self._closed = True
        self._polling = False
        self._safe_destroy()
        self.on_granted(self.file_path, self.incident_id)

    def _close_and_deny(self):
        """Close popup and trigger denied callback."""
        self._closed = True
        self._polling = False
        self._safe_destroy()
        self.on_denied(self.file_path, self.incident_id)

    def _close_and_block(self):
        """Close popup and trigger blocked callback."""
        self._closed = True
        self._polling = False
        self._safe_destroy()
        self.on_blocked(self.file_path, self.incident_id)
