"""
SecureGuard PC Software — Main Entry Point
Orchestrates all modules: file protection, monitoring, notifications, UI.
Runs silently in the background on Windows.
"""

import os
import sys
import time
import threading
import ctypes

# Hide console window on Windows
try:
    ctypes.windll.user32.ShowWindow(
        ctypes.windll.kernel32.GetConsoleWindow(), 0
    )
except Exception:
    pass

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import logger, DATA_DIR
from database import Database
from file_protector import FileProtector
from file_watcher import FileWatcher
from decoy_monitor import DecoyMonitor
from notification_sender import NotificationSender
from security_popup import SecurityPopup
from done_popup import DonePopup
from photo_capture import PhotoCapture
from attempt_tracker import AttemptTracker
from keyboard_listener import KeyboardListener
from settings_panel import SettingsPanel
from heartbeat import Heartbeat
from startup import ensure_startup
from utils import get_file_name, close_file_process

import queue
import tkinter as tk

class SecureGuardApp:
    """Main application class — orchestrates all SecureGuard modules."""

    # Mutex: only one popup at a time to prevent tkinter multi-Tk crashes
    _popup_lock = threading.Lock()

    # Queue for alerts that need GUI (tkinter must run on main thread)
    _gui_queue = queue.Queue()

    def __init__(self):
        logger.info("=" * 60)
        logger.info("SecureGuard starting...")
        logger.info("=" * 60)

        # Initialize database
        self.db = Database()
        if not self.db.authenticate():
            logger.error("Authentication failed — exiting")
            sys.exit(1)

        # Initialize modules
        self.file_protector = FileProtector()
        self.notification_sender = NotificationSender(self.db)
        self.photo_capture = PhotoCapture(self.db)
        self.attempt_tracker = AttemptTracker(self.db)
        self.heartbeat_service = Heartbeat(self.db)

        # File watcher (needs file_protector and database)
        self.file_watcher = FileWatcher(self.file_protector, self.db)

        # Decoy monitor (needs file_protector, database, and callback)
        self.decoy_monitor = DecoyMonitor(
            self.file_protector, self.db, self._on_access_detected
        )

        # Keyboard listener (needs database and callback)
        self.keyboard_listener = KeyboardListener(self.db, self._open_settings)

        # Subscribe to realtime changes
        self._setup_realtime_subscriptions()

        # Load attempt data from database
        self.attempt_tracker.load_from_database()

        # Protect all files from database that aren't already protected
        self._initial_protection()

    def _setup_realtime_subscriptions(self):
        """Set up Supabase realtime subscriptions."""
        # Settings changes (from phone)
        self.db.subscribe_to_settings(self.keyboard_listener.on_settings_changed)

        # Protected files changes (from phone — Features 4, 5, 6)
        self.db.subscribe_to_protected_files(self.file_watcher.on_protected_files_changed)

    def _initial_protection(self):
        """Protect all files from database on startup."""
        files = self.db.get_protected_files(force_refresh=True)

        for f in files:
            if not f.get("is_active", True):
                continue

            path = f["path"]
            file_type = f.get("file_type", "file")

            if file_type == "folder":
                if os.path.isdir(path):
                    self.file_protector.protect_folder(path)
                    self.file_watcher.watch_folder(path)
            else:
                if os.path.exists(path) and not self.file_protector.is_protected(path):
                    self.file_protector.protect_file(path)

        logger.info(f"Initial protection applied to {len(files)} items")

    def start(self):
        """Start all services."""
        # Register for Windows startup
        ensure_startup()

        # Start services
        self.heartbeat_service.start()
        self.decoy_monitor.start()
        self.file_watcher.start()
        self.keyboard_listener.start()

        # Retry any pending photo uploads (skip — no incident to link to)
        # Photos from failed uploads stay local until next alert triggers upload

        logger.info("All services started — SecureGuard is active")

        self._running = True

        # Main loop — process GUI tasks on the main thread.
        # tkinter MUST run on the main thread or it crashes with Tcl_AsyncDelete.
        # NEVER crash — catch everything and keep running.
        while True:
            try:
                # Check for GUI tasks (popups) from worker threads
                try:
                    gui_task = self._gui_queue.get(timeout=0.5)
                    gui_task()  # Execute the popup on the main thread
                except queue.Empty:
                    pass
            except KeyboardInterrupt:
                logger.info("Shutdown requested")
                self.stop()
                break
            except Exception as e:
                logger.error(f"Main loop error (non-fatal): {e}", exc_info=True)

    def stop(self):
        """Stop all services gracefully."""
        if getattr(self, '_running', False) == False:
            return
            
        logger.info("Shutting down SecureGuard...")
        self._running = False

        self.decoy_monitor.stop()
        self.file_watcher.stop()
        self.keyboard_listener.stop()
        self.heartbeat_service.stop()
        self.notification_sender.stop_all_repeats()

        logger.info("SecureGuard stopped")

    # ============================================================
    # ALERT PIPELINE
    # ============================================================

    def _on_access_detected(self, file_path: str):
        """
        Called when a decoy file access is detected (from worker thread).
        Does all non-GUI work, then enqueues the popup for the main thread.
        """
        file_name = get_file_name(file_path)
        logger.warning(f"ACCESS DETECTED: {file_name} ({file_path})")

        try:
            # IMMEDIATELY close any process that opened the file
            # This prevents the decoy from actually opening — only the popup will appear
            close_file_process(file_path)
            logger.info(f"File process closed immediately: {file_path}")

            # Check if file is blocked
            if self.db.is_file_blocked(file_path):
                logger.info(f"File is blocked — denying access: {file_path}")
                close_file_process(file_path)
                # Clean up processing state so monitor can re-detect if needed
                self.decoy_monitor.mark_done(file_path)
                return

            # Check if protection is enabled
            if not self.db.get_protection_enabled():
                logger.info("Protection is disabled — ignoring access")
                # Clean up processing state
                self.decoy_monitor.mark_done(file_path)
                return

            # Acquire popup lock — only ONE popup at a time
            # If another popup is already showing, skip this alert
            if not self._popup_lock.acquire(blocking=False):
                logger.warning(f"Another popup is active — skipping alert for {file_name}")
                self.decoy_monitor.mark_done(file_path)
                return

            try:
                # Step 1: Create incident
                incident_id = self.db.create_incident(file_path, file_name)
                if not incident_id:
                    logger.error("Failed to create incident")
                    self.decoy_monitor.mark_done(file_path)
                    return

                # Step 2: Send notification in background (don't block popup)
                threading.Thread(
                    target=self.notification_sender.send_alert,
                    args=(incident_id, file_name, file_path),
                    daemon=True,
                    name="SendAlert"
                ).start()

                # Step 3: Enqueue popup for the MAIN THREAD
                # tkinter must be created/run on the main thread or it crashes
                self._gui_queue.put(lambda fp=file_path, fn=file_name, iid=incident_id: 
                    self._show_popup(fp, fn, iid))
                
                # DON'T release popup lock here — _show_popup will release it when done
                return
                
            except Exception:
                self._popup_lock.release()
                raise

        except Exception as e:
            logger.error(f"Alert pipeline error for {file_path}: {e}", exc_info=True)
            # Always clean up the decoy monitor so the file can be re-triggered later
            self.decoy_monitor.mark_done(file_path)

    def _show_popup(self, file_path: str, file_name: str, incident_id: str):
        """Show the security popup — MUST be called from the main thread."""
        try:
            popup = SecurityPopup(
                database=self.db,
                file_name=file_name,
                file_path=file_path,
                incident_id=incident_id,
                on_granted=self._on_access_granted,
                on_denied=self._on_access_denied,
                on_blocked=self._on_file_blocked
            )
            popup.show()
        except Exception as e:
            logger.error(f"Popup error for {file_path}: {e}", exc_info=True)
            self.decoy_monitor.mark_done(file_path)
        finally:
            self._popup_lock.release()

    def _on_access_granted(self, file_path: str, incident_id: str):
        """
        Called when access is granted (owner allowed + correct answers).
        1. Stop repeat notifications
        2. Restore and open the real file
        3. Show done popup
        4. Re-protect after done
        """
        logger.info(f"ACCESS GRANTED: {file_path}")

        # Stop repeat notifications
        self.notification_sender.stop_repeat(incident_id)

        # Restore and open the real file
        if self.file_protector.restore_and_open(file_path):
            # Enqueue the Done popup to run cleanly on the main thread
            file_name = get_file_name(file_path)
            self._gui_queue.put(lambda fp=file_path, fn=file_name: self._show_done_popup(fp, fn))
        else:
            logger.error(f"Failed to restore file: {file_path}")
            # Reset decoy monitor tracking if it failed
            self.decoy_monitor.mark_done(file_path)

    def _show_done_popup(self, file_path: str, file_name: str):
        """Show the done popup cleanly on the main thread."""
        try:
            done_popup = DonePopup(
                file_name=file_name,
                file_path=file_path,
                on_done=self._on_done_viewing
            )
            done_popup.show()
        except Exception as e:
            logger.error(f"Done popup error: {e}", exc_info=True)
            self.decoy_monitor.mark_done(file_path)

    def _on_access_denied(self, file_path: str, incident_id: str):
        """
        Called when access is denied (owner denied / auto-denied / wrong answers).
        1. Stop repeat notifications
        2. Take intruder photo
        3. Close the file process
        """
        logger.info(f"ACCESS DENIED: {file_path}")

        # Stop repeat notifications
        self.notification_sender.stop_repeat(incident_id)

        # Take intruder photo
        threading.Thread(
            target=self.photo_capture.capture_and_upload,
            args=(incident_id,),
            daemon=True,
            name="PhotoCapture"
        ).start()

        # Close any process that opened the file
        close_file_process(file_path)

        # Reset decoy monitor tracking
        self.decoy_monitor.mark_done(file_path)

    def _on_file_blocked(self, file_path: str, incident_id: str):
        """
        Called when a file is permanently blocked (max attempts exceeded).
        Same as denied but also blocks the file permanently.
        """
        logger.warning(f"FILE BLOCKED: {file_path}")

        # Stop repeat notifications
        self.notification_sender.stop_repeat(incident_id)

        # Take intruder photo
        threading.Thread(
            target=self.photo_capture.capture_and_upload,
            args=(incident_id,),
            daemon=True,
            name="PhotoCapture"
        ).start()

        # Close any process that opened the file
        close_file_process(file_path)

        # Reset decoy monitor tracking
        self.decoy_monitor.mark_done(file_path)

    def _on_done_viewing(self, file_path: str):
        """Called when user clicks Done after viewing a file."""
        logger.info(f"Done viewing: {file_path}")

        # Completely sever any active instance reading the loaded target
        close_file_process(file_path)
        time.sleep(0.5)

        # Re-protect the file
        self.file_protector.re_protect_file(file_path)

        # Reset decoy monitor
        self.decoy_monitor.reset_file(file_path)

    # ============================================================
    # SETTINGS
    # ============================================================

    def _open_settings(self):
        """Open the settings panel (enqueued to run on main thread)."""
        self._gui_queue.put(self._show_settings_panel)

    def _show_settings_panel(self):
        """Show the settings panel on the main thread."""
        logger.info("Opening settings panel")
        try:
            panel = SettingsPanel(
                database=self.db,
                file_protector=self.file_protector,
                file_watcher=self.file_watcher,
                attempt_tracker=self.attempt_tracker,
                keyboard_listener=self.keyboard_listener
            )
            panel.show()
        except Exception as e:
            logger.error(f"Error opening settings panel: {e}", exc_info=True)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    app = SecureGuardApp()
    app.start()
