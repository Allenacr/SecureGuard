"""
SecureGuard PC Software — Attempt Tracker Module
Tracks wrong answer attempts per file.
Blocks files permanently after MAX_ATTEMPTS.
Resets when file is unblocked or removed from protection.
"""

import logging
import threading
from typing import Dict

from config import MAX_ATTEMPTS

logger = logging.getLogger("SecureGuard.AttemptTracker")


class AttemptTracker:
    """
    Tracks wrong answer attempts per protected file.
    - Blocks file permanently after MAX_ATTEMPTS
    - Resets on unblock or removal from protection
    - Syncs with Supabase protected_files table
    """

    def __init__(self, database):
        self.database = database
        self._attempts: Dict[str, int] = {}
        self._lock = threading.Lock()

    def get_attempts(self, file_path: str) -> int:
        """Get current attempt count for a file."""
        with self._lock:
            return self._attempts.get(file_path, 0)

    def increment(self, file_path: str) -> int:
        """
        Increment attempt count for a file.
        Returns the new count.
        Blocks the file if MAX_ATTEMPTS is reached.
        """
        with self._lock:
            count = self._attempts.get(file_path, 0) + 1
            self._attempts[file_path] = count

        # Sync to database
        self.database.update_attempt_count(file_path, count)

        max_attempts = self.database.get_max_attempts()

        if count >= max_attempts:
            logger.warning(f"File blocked after {count} attempts: {file_path}")
            self.database.block_file(file_path)

        return count

    def get_remaining(self, file_path: str) -> int:
        """Get remaining attempts before blocking."""
        max_attempts = self.database.get_max_attempts()
        current = self.get_attempts(file_path)
        return max(0, max_attempts - current)

    def is_blocked(self, file_path: str) -> bool:
        """Check if file is blocked due to max attempts."""
        max_attempts = self.database.get_max_attempts()
        return self.get_attempts(file_path) >= max_attempts

    def reset(self, file_path: str):
        """Reset attempt count for a file (on unblock or removal)."""
        with self._lock:
            self._attempts.pop(file_path, None)
        self.database.update_attempt_count(file_path, 0)
        logger.info(f"Attempt count reset for: {file_path}")

    def reset_all(self):
        """Reset all attempt counts."""
        with self._lock:
            self._attempts.clear()
        logger.info("All attempt counts reset")

    def load_from_database(self):
        """Load attempt counts from database on startup."""
        try:
            files = self.database.get_protected_files(force_refresh=True)
            with self._lock:
                for f in files:
                    if f.get("attempts", 0) > 0:
                        self._attempts[f["path"]] = f["attempts"]
            logger.info(f"Loaded {len(self._attempts)} attempt records from database")
        except Exception as e:
            logger.error(f"Error loading attempts from database: {e}")
