"""
SecureGuard PC Software — File Watcher Module
Uses watchdog library to monitor protected folders for new files.
Auto-detects and protects new files added to protected folders.
"""

import os
import time
import logging
import threading
from typing import Dict, Optional

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent

logger = logging.getLogger("SecureGuard.FileWatcher")


class ProtectedFolderHandler(FileSystemEventHandler):
    """Handles file system events in protected folders."""

    def __init__(self, file_protector, database):
        super().__init__()
        self.file_protector = file_protector
        self.database = database
        self._recently_handled = {}
        self._lock = threading.Lock()

    def on_created(self, event):
        """When a new file is created in a protected folder, protect it."""
        if event.is_directory:
            return

        file_path = os.path.normpath(event.src_path)

        # Debounce — avoid processing the same file multiple times
        with self._lock:
            now = time.time()
            if file_path in self._recently_handled:
                if now - self._recently_handled[file_path] < 2.0:
                    return
            self._recently_handled[file_path] = now

        # Don't re-protect decoy files we just created
        if self.file_protector.is_protected(file_path):
            return

        logger.info(f"New file detected in protected folder: {file_path}")

        # Protect the new file
        try:
            if self.file_protector.protect_file(file_path):
                # Also add to database
                file_name = os.path.basename(file_path)
                self.database.add_protected_file(file_path, file_name, "file")
                logger.info(f"Auto-protected new file: {file_path}")
        except Exception as e:
            logger.error(f"Error auto-protecting file: {e}")


class FileWatcher:
    """Watches protected folders for new files using watchdog."""

    def __init__(self, file_protector, database):
        self.file_protector = file_protector
        self.database = database
        self.observer = Observer()
        self._watched_paths: Dict[str, object] = {}
        self._lock = threading.Lock()
        self._running = False

    def start(self):
        """Start the file watcher."""
        if self._running:
            return

        self._running = True
        self.observer.start()
        logger.info("FileWatcher started")

        # Watch all protected folders from database
        self._sync_watched_folders()

    def stop(self):
        """Stop the file watcher."""
        self._running = False
        try:
            self.observer.stop()
            self.observer.join(timeout=5)
        except Exception:
            pass
        logger.info("FileWatcher stopped")

    def _sync_watched_folders(self):
        """Sync watched folders with database."""
        try:
            protected = self.database.get_protected_files(force_refresh=True)
            folders = [f for f in protected if f.get("file_type") == "folder" and f.get("is_active")]

            for folder in folders:
                self.watch_folder(folder["path"])
        except Exception as e:
            logger.error(f"Error syncing watched folders: {e}")

    def watch_folder(self, folder_path: str):
        """Start watching a specific folder for new files."""
        folder_path = os.path.normpath(folder_path)

        with self._lock:
            if folder_path in self._watched_paths:
                logger.info(f"Already watching: {folder_path}")
                return

            if not os.path.isdir(folder_path):
                logger.error(f"Not a valid directory: {folder_path}")
                return

            try:
                handler = ProtectedFolderHandler(self.file_protector, self.database)
                watch = self.observer.schedule(handler, folder_path, recursive=True)
                self._watched_paths[folder_path] = watch
                logger.info(f"Now watching folder: {folder_path}")
            except Exception as e:
                logger.error(f"Error watching folder {folder_path}: {e}")

    def unwatch_folder(self, folder_path: str):
        """Stop watching a specific folder."""
        folder_path = os.path.normpath(folder_path)

        with self._lock:
            watch = self._watched_paths.pop(folder_path, None)
            if watch:
                try:
                    self.observer.unschedule(watch)
                    logger.info(f"Stopped watching folder: {folder_path}")
                except Exception as e:
                    logger.error(f"Error unwatching folder: {e}")

    def refresh(self):
        """Refresh watched folders from database."""
        self._sync_watched_folders()

    def on_protected_files_changed(self, payload):
        """
        Callback for realtime subscription on protected_files.
        Adjusts watchers when files/folders are added or removed from phone.
        Handles both dict-style and object-style payloads (varies by supabase-py version).
        """
        try:
            # Handle both payload formats from different supabase-py versions
            if hasattr(payload, 'data'):
                # New-style: payload is an object with .data attribute
                data = payload.data
                event_type = getattr(data, 'type', '') or getattr(data, 'event_type', '')
                record = getattr(data, 'record', {}) or getattr(data, 'new', {}) or {}
                old_record = getattr(data, 'old_record', {}) or getattr(data, 'old', {}) or {}
            elif isinstance(payload, dict):
                # Old-style: payload is a plain dict
                event_type = payload.get("eventType", "") or payload.get("type", "")
                record = payload.get("new", {}) or payload.get("record", {})
                old_record = payload.get("old", {}) or payload.get("old_record", {})
            else:
                logger.warning(f"Unknown realtime payload format: {type(payload)}")
                return

            # Normalize event type
            event_type = event_type.upper()

            # Use old record as fallback for delete events
            if not record:
                record = old_record
            if not record:
                return

            file_type = record.get("file_type", "file")
            path = record.get("path", "")
            is_active = record.get("is_active", True)

            if file_type == "folder":
                if event_type in ("INSERT", "UPDATE") and is_active:
                    self.watch_folder(path)
                    # Also protect all existing files in the folder
                    self.file_protector.protect_folder(path)
                elif event_type == "UPDATE" and not is_active:
                    self.unwatch_folder(path)
            elif file_type == "file":
                if event_type in ("INSERT", "UPDATE") and is_active:
                    # Protect the individual file
                    if os.path.exists(path) and not self.file_protector.is_protected(path):
                        self.file_protector.protect_file(path)

        except Exception as e:
            logger.error(f"Error handling protected_files change: {e}", exc_info=True)
