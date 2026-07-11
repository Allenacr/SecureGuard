"""
SecureGuard PC Software — Photo Capture Module
Silently captures webcam photo when access is denied.
Uploads to Supabase storage and links to incident record.
"""

import os
import time
import logging
from typing import Optional

import cv2

from config import DATA_DIR
from utils import timestamp_filename

logger = logging.getLogger("SecureGuard.PhotoCapture")


class PhotoCapture:
    """Captures intruder photos via webcam and uploads to Supabase storage."""

    def __init__(self, database):
        self.database = database
        self.photos_dir = DATA_DIR / "photos"
        self.photos_dir.mkdir(parents=True, exist_ok=True)

    def capture_and_upload(self, incident_id: str) -> Optional[str]:
        """
        Capture a webcam photo, save locally, upload to Supabase, and return the URL.
        Local photo is only deleted after successful upload.
        """
        logger.info(f"Starting photo capture for incident {incident_id}")
        # Step 1: Capture photo
        local_path = self._capture_photo()
        logger.info(f"Capture photo returned: {local_path}")
        if not local_path:
            logger.warning("Failed to capture photo — no webcam available?")
            return None

        # Step 2: Upload to Supabase storage
        storage_path = f"{self.database.user_id}/{os.path.basename(local_path)}"
        photo_url = self.database.upload_photo(local_path, storage_path)

        if photo_url:
            # Step 3: Update incident with photo URL
            self.database.update_incident(incident_id, {
                "photo_url": photo_url,
                "photo_path": storage_path
            })

            # Step 4: Delete local file only after successful upload
            try:
                os.remove(local_path)
                logger.info(f"Local photo deleted after upload: {local_path}")
            except Exception as e:
                logger.warning(f"Could not delete local photo: {e}")

            return photo_url
        else:
            logger.warning(f"Photo upload failed — keeping local copy at {local_path}")
            return None

    def _capture_photo(self) -> Optional[str]:
        """
        Capture a single frame from the webcam silently.
        No preview window — completely silent capture.
        Returns the local file path or None on failure.
        """
        cap = None
        try:
            # Initialize webcam
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # DirectShow for Windows

            if not cap.isOpened():
                # Try without CAP_DSHOW
                cap = cv2.VideoCapture(0)

            if not cap.isOpened():
                logger.error("Could not open webcam")
                return None

            # Set resolution
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            # Wait briefly for camera to warm up
            time.sleep(0.5)

            # Capture multiple frames, use the last one (first frames may be dark)
            frame = None
            for _ in range(5):
                ret, frame = cap.read()
                if not ret:
                    continue
                time.sleep(0.1)

            if frame is None:
                logger.error("Failed to capture frame from webcam")
                return None

            # Save photo with timestamp
            filename = f"intruder_{timestamp_filename()}.jpg"
            local_path = str(self.photos_dir / filename)

            cv2.imwrite(local_path, frame)
            logger.info(f"Photo captured: {local_path}")

            return local_path

        except Exception as e:
            logger.error(f"Error capturing photo: {e}")
            return None

        finally:
            if cap is not None:
                cap.release()

    def retry_upload(self, incident_id: str) -> bool:
        """
        Retry uploading any local photos that failed to upload previously.
        Scans the photos directory for files not yet uploaded.
        """
        uploaded_count = 0

        for filename in os.listdir(self.photos_dir):
            if not filename.endswith(".jpg"):
                continue

            local_path = str(self.photos_dir / filename)
            storage_path = f"{self.database.user_id}/{filename}"

            photo_url = self.database.upload_photo(local_path, storage_path)
            if photo_url:
                try:
                    os.remove(local_path)
                    uploaded_count += 1
                except Exception:
                    pass

        if uploaded_count > 0:
            logger.info(f"Uploaded {uploaded_count} pending photos")

        return uploaded_count > 0
