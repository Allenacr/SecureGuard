"""
SecureGuard PC Software — Windows Startup Module
Adds/removes SecureGuard from Windows startup via Registry.
Uses pythonw.exe to run without a console window.
"""

import os
import sys
import logging

logger = logging.getLogger("SecureGuard.Startup")

REGISTRY_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "SecureGuard"


def add_to_startup() -> bool:
    """Add SecureGuard to Windows startup."""
    try:
        import winreg

        # Get the path to run at startup
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "main.py"))

        # Use pythonw.exe for no console window
        python_path = sys.executable
        if python_path.endswith("python.exe"):
            pythonw_path = python_path.replace("python.exe", "pythonw.exe")
            if os.path.exists(pythonw_path):
                python_path = pythonw_path

        command = f'"{python_path}" "{script_path}"'

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REGISTRY_KEY,
            0,
            winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
        winreg.CloseKey(key)

        logger.info(f"Added to Windows startup: {command}")
        return True

    except Exception as e:
        logger.error(f"Failed to add to startup: {e}")
        return False


def remove_from_startup() -> bool:
    """Remove SecureGuard from Windows startup."""
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REGISTRY_KEY,
            0,
            winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)

        logger.info("Removed from Windows startup")
        return True

    except FileNotFoundError:
        logger.info("Not in startup — nothing to remove")
        return True
    except Exception as e:
        logger.error(f"Failed to remove from startup: {e}")
        return False


def is_in_startup() -> bool:
    """Check if SecureGuard is in Windows startup."""
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REGISTRY_KEY,
            0,
            winreg.KEY_READ
        )
        try:
            winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
    except Exception:
        return False


def ensure_startup():
    """Ensure SecureGuard is registered for Windows startup."""
    if not is_in_startup():
        add_to_startup()
