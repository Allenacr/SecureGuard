"""
SecureGuard PC Software — Decoy Monitor Module
Thread that checks decoy file access every 0.5 seconds.
When a decoy is accessed, triggers the full alert pipeline.

Stability features:
- Per-file cooldown prevents false re-triggers after alert cycle
- Full-path process matching avoids false positives from unrelated processes
- Robust exception handling prevents monitor crashes
- Processing guard stays active until cooldown expires
"""

import os
import time
import logging
import threading
from typing import Dict, Optional, Callable

from config import CHECK_INTERVAL, CACHE_INTERVAL

logger = logging.getLogger("SecureGuard.DecoyMonitor")

# Cooldown period (seconds) after an alert cycle completes for a file.
# During this window, no new alerts will trigger for the same file.
ALERT_COOLDOWN = 15


class DecoyMonitor:
    """
    Monitors decoy files for access.
    - Checks every 0.5 seconds (CHECK_INTERVAL)
    - Caches protection status every 5 seconds (CACHE_INTERVAL)
    - Triggers callback when decoy access is detected
    - Cooldown prevents false re-triggers after alert cycle
    """

    def __init__(self, file_protector, database, on_access_detected: Callable):
        self.file_protector = file_protector
        self.database = database
        self.on_access_detected = on_access_detected

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Track last access times for decoy files
        self._last_access_times: Dict[str, float] = {}

        # Cache for protected file list
        self._protected_files_cache = []
        self._cache_timestamp: float = 0

        # Track files currently being processed (avoid double alerts)
        self._processing: set = set()

        # Cooldown timestamps — file_path -> earliest time a new alert is allowed
        self._cooldown_until: Dict[str, float] = {}

    def start(self):
        """Start the decoy monitor thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True, name="DecoyMonitor")
        self._thread.start()
        logger.info("DecoyMonitor started")

    def stop(self):
        """Stop the decoy monitor thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("DecoyMonitor stopped")

    def _refresh_cache(self):
        """Refresh the protected files cache from database."""
        now = time.time()
        if now - self._cache_timestamp >= CACHE_INTERVAL:
            try:
                self._protected_files_cache = self.database.get_protected_files(force_refresh=True)
                self._cache_timestamp = now
            except Exception as e:
                logger.error(f"Error refreshing cache: {e}")

    def _get_monitored_files(self) -> list:
        """
        Get list of file paths to monitor.
        Includes individual files and all files in protected folders.
        """
        self._refresh_cache()
        files = []

        for item in self._protected_files_cache:
            if not item.get("is_active", True):
                continue
            if item.get("is_blocked", False):
                continue

            path = item["path"]
            file_type = item.get("file_type", "file")

            if file_type == "folder":
                # Get all files in the folder
                if os.path.isdir(path):
                    for root, dirs, filenames in os.walk(path):
                        for fn in filenames:
                            files.append(os.path.normpath(os.path.join(root, fn)))
            else:
                files.append(os.path.normpath(path))

        return files

    def _initialize_access_times(self, files: list):
        """Initialize access times for newly tracked files."""
        for file_path in files:
            if file_path not in self._last_access_times:
                try:
                    if os.path.exists(file_path):
                        self._last_access_times[file_path] = os.path.getatime(file_path)
                    else:
                        self._last_access_times[file_path] = 0
                except OSError:
                    self._last_access_times[file_path] = 0

    def _is_in_cooldown(self, file_path: str) -> bool:
        """Check if a file is currently in cooldown (no new alerts allowed)."""
        cooldown_end = self._cooldown_until.get(file_path, 0)
        return time.time() < cooldown_end

    def _check_access(self, file_path: str, running_cmdlines: list) -> bool:
        """Check if a decoy file has been accessed since last check using atime and psutil."""
        try:
            if not os.path.exists(file_path):
                return False

            accessed = False
            current_atime = os.path.getatime(file_path)
            last_atime = self._last_access_times.get(file_path, 0)

            if current_atime > last_atime and last_atime > 0:
                accessed = True

            self._last_access_times[file_path] = current_atime
            
            if accessed:
                return True
                
            # Method 2: Process checking (because Windows disables atime by default)
            # Use FULL NORMALIZED PATH to avoid false positives from unrelated files
            norm_path = os.path.normpath(file_path).lower()
            for cmd in running_cmdlines:
                if norm_path in cmd:
                    return True

            return False
        except OSError:
            return False

    def _monitor_loop(self):
        """Main monitoring loop — runs in background thread."""
        logger.info("DecoyMonitor loop started")
        import psutil

        # Collect our own process name to exclude from detection
        try:
            own_pid = os.getpid()
        except Exception:
            own_pid = -1

        while self._running:
            try:
                # Check if protection is enabled
                if not self.database.get_protection_enabled():
                    time.sleep(CHECK_INTERVAL)
                    continue

                # Get files to monitor
                files = self._get_monitored_files()
                self._initialize_access_times(files)

                # Get all command lines currently running to detect open files.
                # Exclude our own process and known safe processes.
                running_cmdlines = []
                whitelist = [
                    "explorer.exe", "cmd.exe", "powershell.exe", "searchapp.exe",
                    "svchost.exe", "code.exe", "python.exe", "pythonw.exe",
                    "searchprotocolhost.exe", "searchfilterhost.exe",
                ]
                try:
                     for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                         try:
                             pid = proc.info.get('pid', 0)
                             # Skip our own process
                             if pid == own_pid:
                                 continue
                             name = (proc.info.get('name') or "").lower()
                             if any(w == name for w in whitelist):
                                 continue
                             cmd = proc.info.get('cmdline')
                             if cmd and len(cmd) > 1:
                                 # Combine all arguments into one lowercase string
                                 running_cmdlines.append(" ".join(cmd[1:]).lower())
                         except (psutil.NoSuchProcess, psutil.AccessDenied):
                             continue
                except Exception:
                     pass

                # Check each decoy file
                for file_path in files:
                    if not self._running:
                        break

                    # Skip files currently being processed
                    with self._lock:
                        if file_path in self._processing:
                            continue

                    # Skip files in cooldown (recently handled)
                    if self._is_in_cooldown(file_path):
                        continue

                    # Check if decoy was accessed
                    if self._check_access(file_path, running_cmdlines):
                        logger.warning(f"Decoy access detected: {file_path}")

                        # Mark as processing
                        with self._lock:
                            self._processing.add(file_path)

                        # Trigger alert in a separate thread
                        threading.Thread(
                            target=self._handle_access,
                            args=(file_path,),
                            daemon=True,
                            name=f"AlertHandler-{os.path.basename(file_path)}"
                        ).start()

            except Exception as e:
                logger.error(f"DecoyMonitor error: {e}", exc_info=True)

            time.sleep(CHECK_INTERVAL)

    def _handle_access(self, file_path: str):
        """Handle detected decoy access — calls the alert callback."""
        try:
            self.on_access_detected(file_path)
        except Exception as e:
            logger.error(f"Error handling access for {file_path}: {e}", exc_info=True)
        # NOTE: We do NOT remove from _processing here.
        # The caller (mark_done / reset_file) is responsible for cleanup
        # AFTER the full alert cycle completes + cooldown is set.

    def mark_done(self, file_path: str):
        """
        Mark a file as done processing (called after alert cycle completes).
        Sets a cooldown to prevent false re-triggers.
        """
        file_path = os.path.normpath(file_path)

        # Set cooldown BEFORE removing from processing
        self._cooldown_until[file_path] = time.time() + ALERT_COOLDOWN

        with self._lock:
            self._processing.discard(file_path)

        # Snapshot the current atime so the next loop doesn't re-trigger
        try:
            if os.path.exists(file_path):
                self._last_access_times[file_path] = os.path.getatime(file_path)
        except OSError:
            pass

        logger.info(f"File marked done with {ALERT_COOLDOWN}s cooldown: {file_path}")

    def reset_file(self, file_path: str):
        """
        Reset tracking for a specific file (after re-protection).
        Sets a cooldown to prevent the new decoy from triggering immediately.
        """
        file_path = os.path.normpath(file_path)

        # Set cooldown BEFORE removing from processing
        self._cooldown_until[file_path] = time.time() + ALERT_COOLDOWN

        with self._lock:
            self._processing.discard(file_path)

        # Snapshot the current atime of the newly-created decoy
        try:
            if os.path.exists(file_path):
                self._last_access_times[file_path] = os.path.getatime(file_path)
        except OSError:
            self._last_access_times.pop(file_path, None)

        logger.info(f"File reset with {ALERT_COOLDOWN}s cooldown: {file_path}")
