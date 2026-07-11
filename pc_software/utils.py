"""
SecureGuard PC Software — Utility Functions
MD5 hashing, file type detection, process utilities, timestamp formatting.
"""

import os
import hashlib
import subprocess
import datetime
import psutil
from pathlib import Path
from typing import Optional


def md5_hash(text: str) -> str:
    """Generate MD5 hash of text — used for vault file naming to avoid conflicts."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def get_file_extension(file_path: str) -> str:
    """Get file extension in lowercase without the dot."""
    return Path(file_path).suffix.lstrip(".").lower()


def get_file_name(file_path: str) -> str:
    """Get just the file name from a full path."""
    return Path(file_path).name


def file_exists(file_path: str) -> bool:
    """Check if a file or directory exists."""
    return Path(file_path).exists()


def is_directory(file_path: str) -> bool:
    """Check if path is a directory."""
    return Path(file_path).is_dir()


def get_file_size(file_path: str) -> int:
    """Get file size in bytes."""
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0


def get_last_access_time(file_path: str) -> float:
    """Get the last access time of a file as a timestamp."""
    try:
        return os.path.getatime(file_path)
    except OSError:
        return 0.0


def format_timestamp(dt: Optional[datetime.datetime] = None) -> str:
    """Format datetime to readable IST string."""
    if dt is None:
        dt = datetime.datetime.now()
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def timestamp_filename() -> str:
    """Generate a timestamp-based filename (for photos etc.)."""
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def open_file(file_path: str) -> bool:
    """Open a file with the default system application."""
    try:
        os.startfile(file_path)
        return True
    except Exception:
        try:
            subprocess.Popen(["start", "", file_path], shell=True)
            return True
        except Exception:
            return False


def close_file_process(file_path: str) -> bool:
    """
    Close any process that has the specified file open.
    Returns True if a process was found and terminated.
    
    Uses two methods:
    1. Fast cmdline scan (synchronous) — catches most cases
    2. Thorough open_files scan (background) — catches edge cases
    """
    file_path = file_path.lower()
    closed = False
    
    whitelist = [
        "explorer.exe", "cmd.exe", "powershell.exe", "searchapp.exe",
        "svchost.exe", "code.exe", "python.exe", "pythonw.exe",
        "searchprotocolhost.exe", "searchfilterhost.exe",
    ]
    
    # Method 1: Fast cmdline-based scan (synchronous)
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            name = (proc.info.get("name") or "").lower()
            if any(w == name for w in whitelist):
                continue
                
            cmdline = proc.info.get("cmdline") or []
            cmdline_str = " ".join(cmdline).lower()
            
            # Explicit constraint: Absolute path must precisely match inside command line
            if file_path in cmdline_str:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except psutil.TimeoutExpired:
                    proc.kill()
                closed = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    
    # Method 2: Thorough open_files scan (background thread — slow but catches edge cases)
    import threading
    def _scan_open_files():
        try:
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    name = (proc.info.get("name") or "").lower()
                    if any(w == name for w in whitelist):
                        continue
                    open_files = proc.open_files()
                    for f in open_files:
                        if os.path.normpath(f.path).lower() == os.path.normpath(file_path).lower():
                            proc.terminate()
                            try:
                                proc.wait(timeout=3)
                            except psutil.TimeoutExpired:
                                proc.kill()
                            break
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception:
            pass
    
    threading.Thread(target=_scan_open_files, daemon=True, name="CloseFileProc").start()
    
    return closed


def get_all_files_in_folder(folder_path: str) -> list:
    """Get all files in a folder recursively."""
    files = []
    try:
        for root, dirs, filenames in os.walk(folder_path):
            for filename in filenames:
                files.append(os.path.join(root, filename))
    except Exception:
        pass
    return files


def get_supported_extensions() -> set:
    """Return set of commonly protected file extensions."""
    return {
        "txt", "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
        "jpg", "jpeg", "png", "gif", "bmp", "tiff", "webp",
        "mp4", "avi", "mkv", "mov", "wmv", "flv",
        "mp3", "wav", "flac", "aac",
        "zip", "rar", "7z",
        "py", "js", "html", "css", "json", "xml", "csv",
        "exe", "msi", "bat", "ps1",
    }


def bytes_to_readable(size_bytes: int) -> str:
    """Convert bytes to human-readable size string."""
    if size_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    return f"{size:.1f} {units[i]}"
