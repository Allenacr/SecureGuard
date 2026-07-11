"""
SecureGuard PC Software — Notification Sender Module
Sends FCM push notifications using Firebase Admin SDK (v1 API).
Features: retry on failure, repeat notifications, notification history logging.
"""

import time
import json
import logging
import threading
from typing import Optional, List

import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request

from config import (
    FCM_V1_URL, FIREBASE_SA_PATH,
    NOTIFICATION_RETRY_COUNT, NOTIFICATION_REPEAT_INTERVAL
)

logger = logging.getLogger("SecureGuard.NotificationSender")

# FCM v1 API scope
SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]


class NotificationSender:
    """Manages sending FCM push notifications to owner devices via v1 API."""

    def __init__(self, database):
        self.database = database
        self._repeat_threads = {}  # incident_id -> thread
        self._stop_repeats = {}    # incident_id -> bool
        self._credentials = None
        self._init_credentials()

    def _init_credentials(self):
        """Initialize Google OAuth2 credentials from service account."""
        if FIREBASE_SA_PATH and FIREBASE_SA_PATH.exists():
            try:
                self._credentials = service_account.Credentials.from_service_account_file(
                    str(FIREBASE_SA_PATH), scopes=SCOPES
                )
                logger.info("Firebase service account credentials loaded")
            except Exception as e:
                logger.error(f"Failed to load Firebase credentials: {e}")
                self._credentials = None
        else:
            logger.warning("Firebase service account not found — notifications disabled")

    def _get_access_token(self) -> Optional[str]:
        """Get a valid OAuth2 access token, refreshing if needed."""
        if not self._credentials:
            return None
        try:
            self._credentials.refresh(Request())
            return self._credentials.token
        except Exception as e:
            logger.error(f"Failed to refresh access token: {e}")
            return None

    def send_alert(self, incident_id: str, file_name: str, file_path: str) -> bool:
        """
        Send an alert notification to all owner devices.
        Returns True if at least one notification was sent successfully.
        """
        tokens = self.database.get_all_device_tokens()

        if not tokens:
            logger.warning("No device tokens found — notification not sent")
            return False

        if not FCM_V1_URL:
            logger.error("FCM URL not configured — cannot send notifications")
            return False

        title = "🚨 SecureGuard Alert"
        body = f"Someone is trying to access: {file_name}"

        success = False
        for token in tokens:
            if self._send_to_token(token, title, body, incident_id, file_path):
                success = True

        # Log notification to history (Feature 1)
        self.database.log_notification(incident_id, title, body, "alert")

        # Start repeat notifications (Feature 3) - DISABLED per user request
        # self._start_repeat(incident_id, file_name, file_path, tokens)

        return success

    def _send_to_token(self, token: str, title: str, body: str,
                       incident_id: str, file_path: str) -> bool:
        """Send a notification to a single FCM token using v1 API with retry."""
        # FCM v1 API payload format
        payload = {
            "message": {
                "token": token,
                "android": {
                    "priority": "high",
                },
                "data": {
                    "incident_id": incident_id,
                    "file_path": file_path,
                    "type": "access_alert",
                    "title": title,
                    "body": body,
                    "timestamp": str(int(time.time()))
                }
            }
        }

        # Try sending with retries
        for attempt in range(1 + NOTIFICATION_RETRY_COUNT):
            access_token = self._get_access_token()
            if not access_token:
                logger.error("No access token available — cannot send notification")
                return False

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; UTF-8"
            }

            try:
                response = requests.post(
                    FCM_V1_URL,
                    headers=headers,
                    data=json.dumps(payload),
                    timeout=10
                )

                if response.status_code == 200:
                    logger.info(f"Notification sent successfully (attempt {attempt + 1})")
                    return True
                else:
                    logger.warning(f"FCM v1 HTTP {response.status_code}: {response.text}")

            except requests.exceptions.RequestException as e:
                logger.error(f"Notification send error (attempt {attempt + 1}): {e}")

            if attempt < NOTIFICATION_RETRY_COUNT:
                time.sleep(1)  # Wait before retry

        logger.error(f"Failed to send notification after {1 + NOTIFICATION_RETRY_COUNT} attempts")
        return False

    def _start_repeat(self, incident_id: str, file_name: str, file_path: str, tokens: List[str]):
        """
        Feature 3: Repeat notification every 10 seconds if owner doesn't respond.
        Runs in a background thread.
        """
        self._stop_repeats[incident_id] = False

        def repeat_loop():
            repeat_count = 0
            max_repeats = 30  # Safety cap: stop after 5 minutes (30 * 10s)

            while not self._stop_repeats.get(incident_id, True):
                time.sleep(NOTIFICATION_REPEAT_INTERVAL)

                try:
                    # Check if owner has already responded
                    decision = self.database.get_owner_decision(incident_id)
                    if decision is not None:
                        logger.info(f"Owner responded — stopping repeat notifications for {incident_id}")
                        break
                except Exception as e:
                    logger.error(f"Error checking decision in repeat loop: {e}")
                    break  # Stop repeating on DB errors

                if self._stop_repeats.get(incident_id, True):
                    break

                repeat_count += 1
                if repeat_count >= max_repeats:
                    logger.warning(f"Max repeat notifications reached ({max_repeats}) for {incident_id}")
                    break

                title = f"🔔 SecureGuard Alert (Reminder #{repeat_count})"
                body = f"Someone is still accessing: {file_name}"

                for token in tokens:
                    self._send_to_token(token, title, body, incident_id, file_path)

                # Log repeat notification
                self.database.log_notification(incident_id, title, body, "repeat")

                logger.info(f"Repeat notification #{repeat_count} sent for {incident_id}")

            # Cleanup
            self._stop_repeats.pop(incident_id, None)
            self._repeat_threads.pop(incident_id, None)

        thread = threading.Thread(target=repeat_loop, daemon=True, name=f"RepeatNotif-{incident_id[:8]}")
        thread.start()
        self._repeat_threads[incident_id] = thread

    def stop_repeat(self, incident_id: str):
        """Stop repeat notifications for a specific incident."""
        self._stop_repeats[incident_id] = True
        logger.info(f"Repeat notifications stopped for {incident_id}")

    def stop_all_repeats(self):
        """Stop all repeat notification threads."""
        for incident_id in list(self._stop_repeats.keys()):
            self._stop_repeats[incident_id] = True
        logger.info("All repeat notifications stopped")
