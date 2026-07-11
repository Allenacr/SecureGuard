"""
SecureGuard PC Software — Done Viewing Popup
Small popup at bottom-right corner that appears when a file is being viewed.
User clicks "Done" when finished viewing, which triggers re-protection.
"""

import logging
import tkinter as tk
from tkinter import font as tkfont
from typing import Callable, Optional

from config import DONE_POPUP_WIDTH, DONE_POPUP_HEIGHT

logger = logging.getLogger("SecureGuard.DonePopup")


class DonePopup:
    """
    Small popup at bottom-right of screen.
    Shows "Done" button for user to signal they're done viewing the file.
    Works for all file types — txt, jpg, png, mp4, pdf, docx, xlsx, etc.
    """

    def __init__(self, file_name: str, file_path: str, on_done: Callable):
        self.file_name = file_name
        self.file_path = file_path
        self.on_done = on_done
        self.root: Optional[tk.Tk] = None
        self._closed = False

    def show(self):
        """Show the done popup — blocks until user clicks Done."""
        self._create_gui()

    def _create_gui(self):
        """Create the done popup window."""
        self.root = tk.Tk()
        self.root.title("SecureGuard")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)

        # Position at bottom-right of screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = screen_width - DONE_POPUP_WIDTH - 20
        y = screen_height - DONE_POPUP_HEIGHT - 60  # Above taskbar
        self.root.geometry(f"{DONE_POPUP_WIDTH}x{DONE_POPUP_HEIGHT}+{x}+{y}")

        # Rounded look with shadow effect
        self.root.configure(bg="#1E293B")

        # Inner frame
        inner = tk.Frame(self.root, bg="#FFFFFF", padx=12, pady=8)
        inner.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # File info
        info_font = tkfont.Font(family="Segoe UI", size=8)
        info_label = tk.Label(
            inner, text=f"📂 Viewing: {self.file_name}",
            font=info_font, bg="#FFFFFF", fg="#6B7280",
            anchor="w"
        )
        info_label.pack(fill=tk.X, pady=(0, 5))

        # Subtitle
        sub_label = tk.Label(
            inner, text="Click Done when finished viewing",
            font=("Segoe UI", 7), bg="#FFFFFF", fg="#9CA3AF",
            anchor="w"
        )
        sub_label.pack(fill=tk.X, pady=(0, 5))

        # Done button
        done_btn = tk.Button(
            inner, text="✅ Done", font=("Segoe UI", 10, "bold"),
            bg="#10B981", fg="white", activebackground="#059669",
            activeforeground="white", relief="flat", cursor="hand2",
            padx=20, pady=4, command=self._on_done
        )
        done_btn.pack(fill=tk.X)

        # Prevent close via other means
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)

        # Run
        self.root.mainloop()

    def _on_done(self):
        """Handle Done button click."""
        if self._closed:
            return

        self._closed = True
        logger.info(f"User done viewing: {self.file_name}")

        try:
            self.root.destroy()
        except Exception:
            pass

        # Trigger re-protection callback
        self.on_done(self.file_path)

    def close(self):
        """Programmatically close the popup."""
        self._closed = True
        try:
            if self.root:
                self.root.destroy()
        except Exception:
            pass
