"""
SecureGuard PC Software — Database Module
Supabase client initialization, CRUD operations, caching, realtime subscriptions.
"""

import time
import threading
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY, USER_EMAIL, USER_PASSWORD, PC_NAME, SOFTWARE_VERSION

logger = logging.getLogger("SecureGuard.Database")


class Database:
    """Manages all Supabase interactions for SecureGuard."""

    def __init__(self):
        self.client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.user_id: Optional[str] = None
        self._settings_cache: Optional[Dict] = None
        self._protected_files_cache: Optional[List[Dict]] = None
        self._settings_cache_timestamp: float = 0
        self._files_cache_timestamp: float = 0
        self._cache_lock = threading.Lock()
        self._authenticated = False

    # ============================================================
    # AUTHENTICATION
    # ============================================================

    def authenticate(self) -> bool:
        """Sign in with email/password and store user ID."""
        try:
            response = self.client.auth.sign_in_with_password({
                "email": USER_EMAIL,
                "password": USER_PASSWORD
            })
            self.user_id = response.user.id
            self._authenticated = True
            logger.info(f"Authenticated as {USER_EMAIL} (ID: {self.user_id})")

            # Ensure settings row exists
            self._ensure_settings()
            # Ensure heartbeat row exists
            self._ensure_heartbeat()

            return True
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False

    def _ensure_settings(self):
        """Create settings row if it doesn't exist."""
        try:
            result = self.client.table("settings").select("id").eq("user_id", self.user_id).execute()
            if not result.data:
                self.client.table("settings").insert({
                    "user_id": self.user_id,
                    "protection_enabled": True,
                    "secret_keyword": "opensecureguard",
                    "alert_timeout_seconds": 60,
                }).execute()
                logger.info("Created default settings row")
        except Exception as e:
            logger.error(f"Error ensuring settings: {e}")

    def _ensure_heartbeat(self):
        """Create heartbeat row if it doesn't exist."""
        try:
            result = self.client.table("heartbeat").select("id").eq("user_id", self.user_id).execute()
            if not result.data:
                self.client.table("heartbeat").insert({
                    "user_id": self.user_id,
                    "pc_name": PC_NAME,
                    "pc_os": "Windows",
                    "software_version": SOFTWARE_VERSION,
                    "protection_active": True
                }).execute()
                logger.info("Created heartbeat row")
        except Exception as e:
            logger.error(f"Error ensuring heartbeat: {e}")

    # ============================================================
    # SETTINGS
    # ============================================================

    def get_settings(self, force_refresh: bool = False) -> Dict:
        """Get user settings with caching."""
        with self._cache_lock:
            now = time.time()
            if not force_refresh and self._settings_cache and (now - self._settings_cache_timestamp) < 5.0:
                return self._settings_cache

        try:
            result = self.client.table("settings").select("*").eq("user_id", self.user_id).single().execute()
            with self._cache_lock:
                self._settings_cache = result.data
                self._settings_cache_timestamp = time.time()
            return result.data
        except Exception as e:
            logger.error(f"Error fetching settings: {e}")
            return self._settings_cache or {}

    def update_settings(self, updates: Dict) -> bool:
        """Update user settings."""
        try:
            self.client.table("settings").update(updates).eq("user_id", self.user_id).execute()
            with self._cache_lock:
                if self._settings_cache:
                    self._settings_cache.update(updates)
            logger.info(f"Settings updated: {list(updates.keys())}")
            return True
        except Exception as e:
            logger.error(f"Error updating settings: {e}")
            return False

    def get_protection_enabled(self) -> bool:
        """Check if protection is currently enabled."""
        settings = self.get_settings()
        return settings.get("protection_enabled", True)

    def get_alert_timeout(self) -> int:
        """Get the alert timeout in seconds."""
        settings = self.get_settings()
        return settings.get("alert_timeout_seconds", 60)

    def get_secret_keyword(self) -> str:
        """Get the current secret keyword."""
        settings = self.get_settings()
        return settings.get("secret_keyword", "opensecureguard")

    def get_security_questions(self) -> list:
        """Get security questions and answers."""
        settings = self.get_settings()
        return settings.get("questions", [])

    def get_max_attempts(self) -> int:
        """Get max wrong answer attempts."""
        settings = self.get_settings()
        return settings.get("max_attempts", 3)

    # ============================================================
    # PROTECTED FILES
    # ============================================================

    def get_protected_files(self, force_refresh: bool = False) -> List[Dict]:
        """Get all protected files with caching."""
        with self._cache_lock:
            now = time.time()
            if not force_refresh and self._protected_files_cache is not None and (now - self._files_cache_timestamp) < 5.0:
                return self._protected_files_cache

        try:
            result = (self.client.table("protected_files")
                      .select("*")
                      .eq("user_id", self.user_id)
                      .eq("is_active", True)
                      .execute())
            with self._cache_lock:
                self._protected_files_cache = result.data or []
                self._files_cache_timestamp = time.time()
            return self._protected_files_cache
        except Exception as e:
            logger.error(f"Error fetching protected files: {e}")
            return self._protected_files_cache or []

    def add_protected_file(self, path: str, file_name: str, file_type: str = "file") -> Optional[Dict]:
        """Add a file or folder to protection."""
        try:
            result = self.client.table("protected_files").insert({
                "user_id": self.user_id,
                "path": path,
                "file_name": file_name,
                "file_type": file_type,
                "is_blocked": False,
                "is_active": True,
                "attempts": 0
            }).execute()
            # Invalidate cache
            with self._cache_lock:
                self._protected_files_cache = None
            logger.info(f"Added protected {file_type}: {path}")
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error adding protected file: {e}")
            return None

    def remove_protected_file(self, path: str) -> bool:
        """Remove a file from protection (soft delete)."""
        try:
            self.client.table("protected_files").update({
                "is_active": False
            }).eq("user_id", self.user_id).eq("path", path).execute()
            with self._cache_lock:
                self._protected_files_cache = None
            logger.info(f"Removed protected file: {path}")
            return True
        except Exception as e:
            logger.error(f"Error removing protected file: {e}")
            return False

    def is_file_protected(self, path: str) -> bool:
        """Check if a specific file is protected."""
        files = self.get_protected_files()
        for f in files:
            if f["path"] == path and f["is_active"]:
                return True
            # Check if file is inside a protected folder
            if f["file_type"] == "folder" and path.startswith(f["path"]):
                return True
        return False

    def is_file_blocked(self, path: str) -> bool:
        """Check if a file is permanently blocked (including files in blocked folders)."""
        import os
        files = self.get_protected_files()
        norm_path = os.path.normpath(path)
        for f in files:
            if not f.get("is_blocked", False):
                continue
            f_path = os.path.normpath(f["path"])
            # Exact match
            if f_path == norm_path:
                return True
            # File inside a blocked folder
            if f.get("file_type") == "folder" and norm_path.startswith(f_path + os.sep):
                return True
        return False

    def block_file(self, path: str) -> bool:
        """Permanently block a file."""
        try:
            self.client.table("protected_files").update({
                "is_blocked": True,
                "blocked_at": datetime.now(timezone.utc).isoformat()
            }).eq("user_id", self.user_id).eq("path", path).execute()
            with self._cache_lock:
                self._protected_files_cache = None
            logger.info(f"File blocked permanently: {path}")
            return True
        except Exception as e:
            logger.error(f"Error blocking file: {e}")
            return False

    def unblock_file(self, path: str) -> bool:
        """Unblock a previously blocked file."""
        try:
            self.client.table("protected_files").update({
                "is_blocked": False,
                "blocked_at": None,
                "attempts": 0
            }).eq("user_id", self.user_id).eq("path", path).execute()
            with self._cache_lock:
                self._protected_files_cache = None
            logger.info(f"File unblocked: {path}")
            return True
        except Exception as e:
            logger.error(f"Error unblocking file: {e}")
            return False

    def update_attempt_count(self, path: str, attempts: int) -> bool:
        """Update the wrong answer attempt count for a file."""
        try:
            self.client.table("protected_files").update({
                "attempts": attempts
            }).eq("user_id", self.user_id).eq("path", path).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating attempt count: {e}")
            return False

    # ============================================================
    # INCIDENTS
    # ============================================================

    def create_incident(self, file_path: str, file_name: str) -> Optional[str]:
        """Create a new incident and return its ID."""
        try:
            result = self.client.table("incidents").insert({
                "user_id": self.user_id,
                "file_path": file_path,
                "file_name": file_name,
                "action": "PENDING",
                "owner_decision": None,
                "pc_name": PC_NAME,
            }).execute()
            incident_id = result.data[0]["id"] if result.data else None
            logger.info(f"Created incident: {incident_id} for {file_name}")
            return incident_id
        except Exception as e:
            logger.error(f"Error creating incident: {e}")
            return None

    def get_incident(self, incident_id: str) -> Optional[Dict]:
        """Get a single incident by ID."""
        try:
            result = (self.client.table("incidents")
                      .select("*")
                      .eq("id", incident_id)
                      .single()
                      .execute())
            return result.data
        except Exception as e:
            logger.error(f"Error fetching incident: {e}")
            return None

    def update_incident(self, incident_id: str, updates: Dict) -> bool:
        """Update an incident."""
        try:
            self.client.table("incidents").update(updates).eq("id", incident_id).execute()
            logger.info(f"Incident {incident_id} updated: {list(updates.keys())}")
            return True
        except Exception as e:
            logger.error(f"Error updating incident: {e}")
            return False

    def get_owner_decision(self, incident_id: str) -> Optional[str]:
        """Poll for owner's decision on an incident.
        Returns:
            - 'allow' / 'deny' if owner responded
            - None if no decision yet (still pending)
            - 'error' if the incident doesn't exist or DB error persists
        """
        try:
            result = (self.client.table("incidents")
                      .select("owner_decision")
                      .eq("id", incident_id)
                      .single()
                      .execute())
            return result.data.get("owner_decision") if result.data else None
        except Exception as e:
            error_str = str(e)
            # PGRST116 = 0 rows = incident deleted from DB
            if 'PGRST116' in error_str or '0 rows' in error_str:
                logger.warning(f"Incident {incident_id} no longer exists in DB — treating as denied")
                return 'deny'
            logger.error(f"Error polling owner decision: {e}")
            return None

    # ============================================================
    # NOTIFICATION HISTORY
    # ============================================================

    def log_notification(self, incident_id: str, title: str, body: str,
                         notification_type: str = "alert") -> bool:
        """Log a sent notification to history."""
        try:
            self.client.table("notification_history").insert({
                "user_id": self.user_id,
                "incident_id": incident_id,
                "title": title,
                "body": body,
                "notification_type": notification_type
            }).execute()
            return True
        except Exception as e:
            logger.error(f"Error logging notification: {e}")
            return False

    # ============================================================
    # HEARTBEAT
    # ============================================================

    def update_heartbeat(self) -> bool:
        """Update the heartbeat timestamp."""
        try:
            self.client.table("heartbeat").update({
                "last_ping": datetime.now(timezone.utc).isoformat(),
                "protection_active": self.get_protection_enabled()
            }).eq("user_id", self.user_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating heartbeat: {e}")
            return False

    # ============================================================
    # DEVICE TOKENS (for sending notifications)
    # ============================================================

    def get_all_device_tokens(self) -> List[str]:
        """
        Get all active FCM tokens for this user and any authorized members.
        Feature 16: Multiple Owner Accounts — each receives notifications independently.
        """
        tokens = []
        try:
            # Get own tokens
            result = (self.client.table("device_tokens")
                      .select("fcm_token")
                      .eq("user_id", self.user_id)
                      .eq("is_active", True)
                      .execute())
            for row in result.data or []:
                tokens.append(row["fcm_token"])

            # Get member tokens (Feature 16)
            members = (self.client.table("owner_accounts")
                       .select("member_user_id")
                       .eq("primary_user_id", self.user_id)
                       .eq("can_respond", True)
                       .execute())
            for member in members.data or []:
                member_tokens = (self.client.table("device_tokens")
                                 .select("fcm_token")
                                 .eq("user_id", member["member_user_id"])
                                 .eq("is_active", True)
                                 .execute())
                for row in member_tokens.data or []:
                    tokens.append(row["fcm_token"])

        except Exception as e:
            logger.error(f"Error fetching device tokens: {e}")

        return tokens

    # ============================================================
    # PHOTO UPLOAD
    # ============================================================

    def upload_photo(self, local_path: str, storage_path: str) -> Optional[str]:
        """Upload a photo to Supabase storage and return the public URL."""
        try:
            with open(local_path, "rb") as f:
                self.client.storage.from_("intruder-photos").upload(
                    path=storage_path,
                    file=f,
                    file_options={"content-type": "image/jpeg"}
                )
            # Get public URL
            url = self.client.storage.from_("intruder-photos").get_public_url(storage_path)
            logger.info(f"Photo uploaded: {storage_path}")
            return url
        except Exception as e:
            logger.error(f"Error uploading photo: {e}")
            return None

    # ============================================================
    # REALTIME SUBSCRIPTIONS
    # ============================================================

    def subscribe_to_settings(self, callback):
        """
        Subscribe to realtime changes on the settings table.
        Used to detect remote changes from phone app (Features 10, 11, 12).
        """
        try:
            channel = self.client.channel("settings_changes")
            channel.on_postgres_changes(
                event="UPDATE",
                schema="public",
                table="settings",
                filter=f"user_id=eq.{self.user_id}",
                callback=callback
            )
            channel.subscribe()
            logger.info("Subscribed to settings realtime changes")
            return channel
        except Exception as e:
            logger.error(f"Error subscribing to settings: {e}")
            return None

    def subscribe_to_protected_files(self, callback):
        """
        Subscribe to realtime changes on protected_files table.
        Used to detect files added from phone (Feature 5).
        """
        try:
            channel = self.client.channel("protected_files_changes")
            channel.on_postgres_changes(
                event="*",
                schema="public",
                table="protected_files",
                filter=f"user_id=eq.{self.user_id}",
                callback=callback
            )
            channel.subscribe()
            logger.info("Subscribed to protected_files realtime changes")
            return channel
        except Exception as e:
            logger.error(f"Error subscribing to protected files: {e}")
            return None

    def invalidate_cache(self):
        """Force cache invalidation."""
        with self._cache_lock:
            self._settings_cache = None
            self._protected_files_cache = None
            self._settings_cache_timestamp = 0
            self._files_cache_timestamp = 0
