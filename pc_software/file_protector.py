"""
SecureGuard PC Software — File Protector Module
Handles file encryption, vault management, decoy creation, and file restoration.
Per-user encryption key derived from password (Feature: per-user key).
"""

import os
import shutil
import logging
import base64
import hashlib
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet
from config import VAULT_DIR, USER_PASSWORD
from utils import md5_hash, get_file_name, get_file_extension, open_file

logger = logging.getLogger("SecureGuard.FileProtector")


class FileProtector:
    """Manages file protection — encryption, vault storage, decoy placement."""

    def __init__(self):
        self.vault_dir = VAULT_DIR
        self.fernet = self._create_fernet()
        self._ensure_vault()

    def _create_fernet(self) -> Fernet:
        """
        Create Fernet cipher from user's password.
        Per-user key: derives a 32-byte key from the user's password using PBKDF2.
        """
        # Derive a key from the user's password
        key = hashlib.pbkdf2_hmac(
            "sha256",
            USER_PASSWORD.encode("utf-8"),
            b"SecureGuard_Salt_v2",  # Fixed salt for deterministic key
            iterations=100_000
        )
        # Fernet requires url-safe base64-encoded 32-byte key
        fernet_key = base64.urlsafe_b64encode(key[:32])
        return Fernet(fernet_key)

    def _ensure_vault(self):
        """Ensure vault directory exists and is hidden."""
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        try:
            import ctypes
            ctypes.windll.kernel32.SetFileAttributesW(str(self.vault_dir), 0x02)
        except Exception:
            pass

    def _get_vault_path(self, original_path: str) -> Path:
        """
        Generate vault path for a file using MD5 hash of full path.
        This avoids name conflicts when protecting files with the same name.
        """
        path_hash = md5_hash(os.path.normpath(original_path))
        extension = get_file_extension(original_path)
        vault_name = f"{path_hash}.{extension}.enc" if extension else f"{path_hash}.enc"
        return self.vault_dir / vault_name

    def _get_metadata_path(self, original_path: str) -> Path:
        """Get path for the metadata file that stores original path info."""
        path_hash = md5_hash(os.path.normpath(original_path))
        return self.vault_dir / f"{path_hash}.meta"

    def protect_file(self, file_path: str) -> bool:
        """
        Protect a file:
        1. Encrypt the real file and move to vault
        2. Place a decoy file at the original location
        3. Save metadata for restoration
        """
        file_path = os.path.normpath(file_path)

        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return False

        if os.path.isdir(file_path):
            logger.error(f"Cannot protect directory directly: {file_path}")
            return False

        vault_path = self._get_vault_path(file_path)
        meta_path = self._get_metadata_path(file_path)

        # Skip if already protected (vault file exists)
        if vault_path.exists():
            logger.info(f"File already protected: {file_path}")
            return True

        try:
            # Step 1: Read the original file
            with open(file_path, "rb") as f:
                original_data = f.read()

            # Step 2: Encrypt the data
            encrypted_data = self.fernet.encrypt(original_data)

            # Step 3: Save encrypted data to vault
            with open(vault_path, "wb") as f:
                f.write(encrypted_data)

            # Step 4: Save metadata (original path, name, size)
            with open(meta_path, "w", encoding="utf-8") as f:
                f.write(f"{file_path}\n")
                f.write(f"{get_file_name(file_path)}\n")
                f.write(f"{len(original_data)}\n")

            # Step 5: Create decoy file at original location
            self._create_decoy(file_path)

            logger.info(f"File protected: {file_path} -> {vault_path}")
            return True

        except Exception as e:
            logger.error(f"Error protecting file {file_path}: {e}")
            # Cleanup on failure
            if vault_path.exists():
                vault_path.unlink()
            if meta_path.exists():
                meta_path.unlink()
            return False

    def _create_decoy(self, original_path: str):
        """
        Create a decoy file at the original location.
        The decoy looks like the real file but is empty/minimal.
        """
        try:
            # Remove original file
            if os.path.exists(original_path):
                os.remove(original_path)

            # Create decoy — empty file with same name
            extension = get_file_extension(original_path)

            if extension in ("txt", "csv", "json", "xml", "py", "js", "html", "css"):
                # Text-based decoys — write minimal content
                with open(original_path, "w", encoding="utf-8") as f:
                    f.write("")
            elif extension in ("pdf",):
                # Minimal PDF
                with open(original_path, "wb") as f:
                    f.write(b"%PDF-1.0\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF")
            elif extension in ("docx", "xlsx", "pptx"):
                # Empty Office XML — just a zero-byte file
                with open(original_path, "wb") as f:
                    f.write(b"")
            else:
                # Binary files — zero-byte decoy
                with open(original_path, "wb") as f:
                    f.write(b"")

            logger.info(f"Decoy created: {original_path}")
        except Exception as e:
            logger.error(f"Error creating decoy: {e}")

    def restore_file(self, file_path: str) -> bool:
        """
        Restore a protected file:
        1. Decrypt from vault
        2. Replace decoy with real file
        """
        file_path = os.path.normpath(file_path)
        vault_path = self._get_vault_path(file_path)

        if not vault_path.exists():
            logger.error(f"Vault file not found for: {file_path}")
            return False

        try:
            # Read encrypted data
            with open(vault_path, "rb") as f:
                encrypted_data = f.read()

            # Decrypt
            original_data = self.fernet.decrypt(encrypted_data)

            # Replace decoy with real file
            with open(file_path, "wb") as f:
                f.write(original_data)

            logger.info(f"File restored: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error restoring file {file_path}: {e}")
            return False

    def restore_and_open(self, file_path: str) -> bool:
        """Restore file and open it with default application."""
        if self.restore_file(file_path):
            return open_file(file_path)
        return False

    def re_protect_file(self, file_path: str) -> bool:
        """
        Re-protect a file after viewing.
        1. Re-encrypt the (possibly modified) file
        2. Place decoy back
        """
        file_path = os.path.normpath(file_path)
        vault_path = self._get_vault_path(file_path)
        meta_path = self._get_metadata_path(file_path)

        if not os.path.exists(file_path):
            logger.error(f"File not found for re-protection: {file_path}")
            return False

        try:
            # Read the current file (may have been modified by user)
            with open(file_path, "rb") as f:
                current_data = f.read()

            # Re-encrypt
            encrypted_data = self.fernet.encrypt(current_data)

            # Save to vault (overwrite)
            with open(vault_path, "wb") as f:
                f.write(encrypted_data)

            # Update metadata
            with open(meta_path, "w", encoding="utf-8") as f:
                f.write(f"{file_path}\n")
                f.write(f"{get_file_name(file_path)}\n")
                f.write(f"{len(current_data)}\n")

            # Create decoy
            self._create_decoy(file_path)

            logger.info(f"File re-protected: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error re-protecting file {file_path}: {e}")
            return False

    def is_protected(self, file_path: str) -> bool:
        """Check if a file is currently protected (has vault entry)."""
        file_path = os.path.normpath(file_path)
        vault_path = self._get_vault_path(file_path)
        return vault_path.exists()

    def remove_protection(self, file_path: str) -> bool:
        """
        Completely remove protection — restore file and delete vault entry.
        """
        file_path = os.path.normpath(file_path)

        # Restore first
        restored = self.restore_file(file_path)

        # Clean up vault files
        vault_path = self._get_vault_path(file_path)
        meta_path = self._get_metadata_path(file_path)

        try:
            if vault_path.exists():
                vault_path.unlink()
            if meta_path.exists():
                meta_path.unlink()
            logger.info(f"Protection removed: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error removing protection: {e}")
            return restored

    def get_all_vault_files(self) -> list:
        """List all files currently in the vault with their original paths."""
        files = []
        for meta_file in self.vault_dir.glob("*.meta"):
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    if lines:
                        original_path = lines[0].strip()
                        file_name = lines[1].strip() if len(lines) > 1 else get_file_name(original_path)
                        file_size = int(lines[2].strip()) if len(lines) > 2 else 0
                        files.append({
                            "original_path": original_path,
                            "file_name": file_name,
                            "file_size": file_size
                        })
            except Exception:
                continue
        return files

    def protect_folder(self, folder_path: str) -> int:
        """
        Protect all files in a folder.
        Returns the number of files successfully protected.
        """
        folder_path = os.path.normpath(folder_path)
        count = 0

        if not os.path.isdir(folder_path):
            logger.error(f"Not a directory: {folder_path}")
            return 0

        for root, dirs, files in os.walk(folder_path):
            for filename in files:
                file_path = os.path.join(root, filename)
                if self.protect_file(file_path):
                    count += 1

        logger.info(f"Protected {count} files in folder: {folder_path}")
        return count
