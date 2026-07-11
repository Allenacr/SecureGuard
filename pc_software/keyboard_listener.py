"""
SecureGuard PC Software — Keyboard Listener Module
Detects secret keyword typed anywhere on the system.
Opens settings panel when keyword is detected.
"""

import logging
import threading
from typing import Callable, Optional

from pynput import keyboard

logger = logging.getLogger("SecureGuard.KeyboardListener")


class KeyboardListener:
    """
    Global keyboard listener that detects the secret keyword.
    When the keyword is typed anywhere, triggers the settings panel.
    Subscribes to Supabase for remote keyword changes.
    """

    def __init__(self, database, on_keyword_detected: Callable):
        self.database = database
        self.on_keyword_detected = on_keyword_detected
        self._current_keyword: str = ""
        self._typed_buffer: str = ""
        self._listener: Optional[keyboard.Listener] = None
        self._running = False
        self._lock = threading.Lock()
        self._settings_open = False

    def start(self):
        """Start listening for keyboard input."""
        if self._running:
            return

        # Load current keyword from database
        self._current_keyword = self.database.get_secret_keyword()
        logger.info(f"Keyboard listener started (keyword length: {len(self._current_keyword)})")

        self._running = True
        self._listener = keyboard.Listener(on_press=self._on_key_press)
        self._listener.daemon = True
        self._listener.start()

    def stop(self):
        """Stop listening."""
        self._running = False
        if self._listener:
            self._listener.stop()
        logger.info("Keyboard listener stopped")

    def update_keyword(self, new_keyword: str):
        """Update the secret keyword (called when settings change)."""
        with self._lock:
            self._current_keyword = new_keyword
            self._typed_buffer = ""
        logger.info(f"Secret keyword updated (length: {len(new_keyword)})")

    def _on_key_press(self, key):
        """Handle each key press."""
        if not self._running:
            return

        try:
            # Get the character
            if hasattr(key, "char") and key.char:
                char = key.char
            else:
                # Non-character key — reset buffer
                with self._lock:
                    self._typed_buffer = ""
                return

            with self._lock:
                self._typed_buffer += char

                # Keep buffer trimmed to keyword length
                keyword = self._current_keyword
                if len(self._typed_buffer) > len(keyword):
                    self._typed_buffer = self._typed_buffer[-len(keyword):]

                # Check for keyword match
                if self._typed_buffer == keyword:
                    self._typed_buffer = ""

                    if not self._settings_open:
                        logger.info("Secret keyword detected — opening settings")
                        self._settings_open = True
                        # Open settings panel in a separate thread
                        threading.Thread(
                            target=self._trigger_settings,
                            daemon=True,
                            name="SettingsTrigger"
                        ).start()

        except Exception as e:
            logger.error(f"Keyboard listener error: {e}")

    def _trigger_settings(self):
        """Trigger the settings panel callback."""
        try:
            self.on_keyword_detected()
        except Exception as e:
            logger.error(f"Error opening settings: {e}")
        finally:
            self._settings_open = False

    def on_settings_changed(self, payload):
        """
        Callback for realtime subscription on settings table.
        Updates the keyword when changed remotely from phone.
        """
        try:
            new_record = payload.get("new", {})
            if new_record:
                new_keyword = new_record.get("secret_keyword", "")
                if new_keyword and new_keyword != self._current_keyword:
                    self.update_keyword(new_keyword)
        except Exception as e:
            logger.error(f"Error handling settings change: {e}")
