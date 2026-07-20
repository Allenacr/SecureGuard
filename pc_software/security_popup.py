"""
SecureGuard PC Software — Security Questions Popup
Beautiful white-themed popup with security questions.
Responds to owner's Allow/Deny decision in realtime.
"""

import time
import logging
import threading
import tkinter as tk
from tkinter import font as tkfont
from typing import Optional, Callable

from config import POPUP_DENY_DELAY, POPUP_GRANT_DELAY

logger = logging.getLogger("SecureGuard.SecurityPopup")


class SecurityPopup:
    """
    Security questions popup that appears when a protected file is accessed.
    - Beautiful white theme
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
        # Start polling in background
        poll_thread = threading.Thread(target=self._poll_owner_decision, daemon=True)
        poll_thread.start()

        # Start timeout timer
        timeout_thread = threading.Thread(target=self._timeout_timer, daemon=True)
        timeout_thread.start()

        # Create and show the GUI
        self._create_gui()

    def _create_gui(self):
        """Create the tkinter popup window."""
        self.root = tk.Tk()
        self.root.title("SecureGuard — Security Verification")
        self.root.overrideredirect(False)
        self.root.attributes("-topmost", True)
        self.root.resizable(False, False)

        # Window size and centering
        window_width = 500
        window_height = 580
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # White background
        self.root.configure(bg="#FFFFFF")

        # Prevent close via X button
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)

        # ---- Header ----
        header_frame = tk.Frame(self.root, bg="#FFFFFF", pady=15)
        header_frame.pack(fill=tk.X)

        # Shield icon
        shield_label = tk.Label(
            header_frame, text="🛡️", font=("Segoe UI Emoji", 28), bg="#FFFFFF"
        )
        shield_label.pack()

        # Title
        title_font = tkfont.Font(family="Segoe UI", size=14, weight="bold")
        title_label = tk.Label(
            header_frame, text="Security Verification Required",
            font=title_font, bg="#FFFFFF", fg="#1a1a1a"
        )
        title_label.pack(pady=(5, 0))

        # File name in red
        file_font = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        file_label = tk.Label(
            header_frame, text=self.file_name,
            font=file_font, bg="#FFFFFF", fg="#DC3545"
        )
        file_label.pack(pady=(3, 0))

        # Separator
        sep = tk.Frame(self.root, height=2, bg="#E0E0E0")
        sep.pack(fill=tk.X, padx=25)

        # ---- Questions Frame ----
        questions_frame = tk.Frame(self.root, bg="#FFFFFF", padx=30, pady=10)
        questions_frame.pack(fill=tk.BOTH, expand=True)

        q_font = tkfont.Font(family="Segoe UI", size=9, weight="bold")
        a_font = tkfont.Font(family="Segoe UI", size=10)

        self._answer_entries = []

        for i, qa in enumerate(self._questions[:5]):
            question = qa.get("question", f"Question {i + 1}")

            # Question label with Q badge
            q_row = tk.Frame(questions_frame, bg="#FFFFFF")
            q_row.pack(fill=tk.X, pady=(8, 2))

            badge = tk.Label(
                q_row, text=f"Q{i + 1}", font=("Segoe UI", 8, "bold"),
                bg="#3B82F6", fg="white", padx=6, pady=1
            )
            badge.pack(side=tk.LEFT, padx=(0, 8))

            q_label = tk.Label(
                q_row, text=question, font=q_font, bg="#FFFFFF", fg="#333333",
                anchor="w"
            )
            q_label.pack(side=tk.LEFT, fill=tk.X)

            # Answer entry (masked)
            entry = tk.Entry(
                questions_frame, show="●", font=a_font,
                bg="#F8F9FA", fg="#1a1a1a", relief="flat",
                highlightbackground="#D1D5DB", highlightcolor="#3B82F6",
                highlightthickness=1, insertbackground="#333"
            )
            entry.pack(fill=tk.X, ipady=6)
            self._answer_entries.append(entry)

        # ---- Status label ----
        self._status_label = tk.Label(
            self.root, text="Waiting for owner's response...",
            font=("Segoe UI", 9), bg="#FFFFFF", fg="#6B7280"
        )
        self._status_label.pack(pady=(5, 0))

        # ---- Attempts label ----
        self._attempts_label = tk.Label(
            self.root, text="",
            font=("Segoe UI", 9, "bold"), bg="#FFFFFF", fg="#DC3545"
        )
        self._attempts_label.pack()

        # ---- Submit Button ----
        btn_frame = tk.Frame(self.root, bg="#FFFFFF", pady=10)
        btn_frame.pack(fill=tk.X)

        self._submit_btn = tk.Button(
            btn_frame, text="Submit Answers", font=("Segoe UI", 11, "bold"),
            bg="#3B82F6", fg="white", activebackground="#2563EB",
            activeforeground="white", relief="flat", cursor="hand2",
            padx=30, pady=8, command=self._on_submit
        )
        self._submit_btn.pack()

        # Focus first entry
        if self._answer_entries:
            self._answer_entries[0].focus_set()

        # Bind Enter key to submit
        self.root.bind("<Return>", lambda e: self._on_submit())

        # Start checking for owner decision updates in GUI thread
        self.root.after(500, self._check_decision_update)

        try:
            # Run the GUI event loop
            self.root.mainloop()
        except Exception as e:
            logger.error(f"Popup loop error: {e}", exc_info=True)
        finally:
            try:
                if self.root and self.root.winfo_exists():
                    self.root.destroy()
            except Exception:
                pass

    def _on_submit(self):
        """Handle answer submission."""
        if self._owner_decision != "allow":
            self._status_label.configure(text="⏳ Waiting for owner to allow access first...")
            return

        # If no questions are configured, deny access (fail-closed)
        if not self._questions:
            self._status_label.configure(text="🚫 No security questions configured!")
            self._status_label.configure(fg="#DC3545")
            self._attempts_label.configure(text="Configure questions in settings first.")
            self.root.after(1500, self._close_and_deny)
            return

        # Verify answers
        answers_correct = self._verify_answers()

        if answers_correct:
            self._status_label.configure(text="✅ Access granted!")
            self._status_label.configure(fg="#10B981")

            # Update incident
            self.database.update_incident(self.incident_id, {
                "action": "ALLOWED",
                "answers_correct": True,
                "responded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            })

            # Close popup after delay
            self.root.after(POPUP_GRANT_DELAY, self._close_and_grant)
        else:
            self._attempt_count += 1
            remaining = self._max_attempts - self._attempt_count

            if remaining > 0:
                self._attempts_label.configure(text=f"❌ Wrong answers! {remaining} attempt(s) remaining")
                # Clear entries
                for entry in self._answer_entries:
                    entry.delete(0, tk.END)
                if self._answer_entries:
                    self._answer_entries[0].focus_set()

                # Update attempt count in database
                self.database.update_attempt_count(self.file_path, self._attempt_count)
            else:
                # Max attempts reached — block permanently
                self._status_label.configure(text="🚫 File blocked permanently!")
                self._status_label.configure(fg="#DC3545")
                self._attempts_label.configure(text=f"Maximum attempts ({self._max_attempts}) exceeded")

                # Update incident + block file
                self.database.update_incident(self.incident_id, {
                    "action": "BLOCKED",
                    "answers_correct": False,
                    "responded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                })
                self.database.block_file(self.file_path)

                self.root.after(1500, self._close_and_block)

    def _verify_answers(self) -> bool:
        """Check submitted answers against stored answers."""
        # Fail-closed: if no questions exist, answers can't be correct
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
        max_errors = 10  # Auto-deny after 10 consecutive poll failures

        while self._polling and not self._closed:
            try:
                decision = self.database.get_owner_decision(self.incident_id)
                if decision is not None:
                    self._owner_decision = decision
                    logger.info(f"Owner decision received: {decision}")
                    consecutive_errors = 0  # Reset on success

                    if decision == "deny":
                        self._polling = False
                    elif decision == "allow":
                        self._polling = False
                    break
                else:
                    consecutive_errors = 0  # None = pending, DB is reachable
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
            self._status_label.configure(text="✅ Access granted! Enter answers below.")
            self._status_label.configure(fg="#10B981")
            self._submit_btn.configure(state=tk.NORMAL)
        elif self._owner_decision == 'deny':
            self._status_label.configure(text="🚫 Access denied by owner!")
            self._status_label.configure(fg="#DC3545")
            self._attempts_label.configure(text="Closing file...")
            self.root.after(POPUP_DENY_DELAY, self._close_and_deny)
            return
        elif self._owner_decision == 'auto_deny':
            self._handle_auto_deny()
            return

        # Auto-deny check
        elapsed = time.time() - self._start_time
        remaining = max(0, self._timeout - elapsed)

        if remaining <= 0:
            self._handle_auto_deny()
            return

        # Only update the "Waiting for owner" text if a decision hasn't been made yet
        if self._owner_decision is None:
            self._status_label.configure(text=f"⏳ Waiting for owner... ({int(remaining)}s remaining)")

        # Schedule next check
        self.root.after(500, self._check_decision_update)

    def _handle_auto_deny(self):
        """Handle auto-deny after timeout."""
        logger.info(f"Auto-denying access for {self.file_path}")

        self._status_label.configure(text="⏰ Auto-denied — owner did not respond")
        self._status_label.configure(fg="#DC3545")
        self._attempts_label.configure(text="Closing file...")

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
            # Cancel ALL pending after() callbacks to prevent Tcl_AsyncDelete crash
            for after_id in self.root.tk.call('after', 'info'):
                try:
                    self.root.after_cancel(after_id)
                except Exception:
                    pass
            self.root.destroy()
            
            # CRITICAL: Clear all Tkinter references so they are garbage collected 
            # NOW on the main thread, rather than later when the background thread exits.
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
