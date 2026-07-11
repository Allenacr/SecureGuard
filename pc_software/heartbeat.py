"""
SecureGuard PC Software — Heartbeat Module
Feature 8: Live PC Status — sends heartbeat to Supabase every 30 seconds.
"""

import time
import logging
import threading

from config import HEARTBEAT_INTERVAL

logger = logging.getLogger("SecureGuard.Heartbeat")


class Heartbeat:
    """
    Sends periodic heartbeat to Supabase so the mobile app
    can determine if the PC software is running.
    """

    def __init__(self, database):
        self.database = database
        self._running = False
        self._thread = None

    def start(self):
        """Start the heartbeat thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._heartbeat_loop, daemon=True, name="Heartbeat")
        self._thread.start()
        logger.info(f"Heartbeat started (interval: {HEARTBEAT_INTERVAL}s)")

    def stop(self):
        """Stop the heartbeat thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Heartbeat stopped")

    def _heartbeat_loop(self):
        """Main heartbeat loop."""
        while self._running:
            try:
                self.database.update_heartbeat()
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

            # Sleep in small increments for responsive shutdown
            for _ in range(HEARTBEAT_INTERVAL * 2):
                if not self._running:
                    break
                time.sleep(0.5)

    def ping(self):
        """Send a single heartbeat ping immediately."""
        try:
            self.database.update_heartbeat()
        except Exception as e:
            logger.error(f"Heartbeat ping error: {e}")
