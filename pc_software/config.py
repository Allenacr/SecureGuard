"""
SecureGuard PC Software — Configuration Module
Loads environment variables, validates config, provides constants.
"""

import os
import sys
import socket
import logging
from pathlib import Path
from dotenv import load_dotenv

# ============================================================
# LOAD ENVIRONMENT
# ============================================================

# Determine base directory (where the script lives)
BASE_DIR = Path(__file__).parent.resolve()
ENV_PATH = BASE_DIR / ".env"

if not ENV_PATH.exists():
    print("[ERROR] .env file not found! Copy .env.example to .env and fill in your values.")
    print(f"  Expected at: {ENV_PATH}")
    sys.exit(1)

load_dotenv(ENV_PATH)

# ============================================================
# REQUIRED CONFIGURATION
# ============================================================

def _require(key: str) -> str:
    """Get required env var or exit with clear error."""
    value = os.getenv(key, "").strip()
    if not value:
        print(f"[ERROR] Missing required config: {key}")
        print(f"  Please set {key} in your .env file")
        sys.exit(1)
    return value


# Supabase
SUPABASE_URL = _require("SUPABASE_URL")
SUPABASE_KEY = _require("SUPABASE_KEY")

# Firebase — uses service account JSON file
FIREBASE_SERVICE_ACCOUNT = os.getenv("FIREBASE_SERVICE_ACCOUNT", "firebase_service_account.json")
FIREBASE_SA_PATH = BASE_DIR / FIREBASE_SERVICE_ACCOUNT
if not FIREBASE_SA_PATH.exists():
    print(f"[WARNING] Firebase service account not found: {FIREBASE_SA_PATH}")
    print("  Notifications will not work until this file is provided.")
    FIREBASE_SA_PATH = None

# User credentials (for auto-login to Supabase)
USER_EMAIL = _require("USER_EMAIL")
USER_PASSWORD = _require("USER_PASSWORD")

# ============================================================
# OPTIONAL CONFIGURATION
# ============================================================

PC_NAME = os.getenv("PC_NAME", socket.gethostname())
SOFTWARE_VERSION = os.getenv("SOFTWARE_VERSION", "2.0.0")

# Vault directory — hidden folder for encrypted files
_vault_dir = os.getenv("VAULT_DIR", "").strip()
if _vault_dir:
    VAULT_DIR = Path(_vault_dir)
else:
    VAULT_DIR = Path(os.environ.get("APPDATA", BASE_DIR)) / ".secureguard_vault"

# SecureGuard data directory (for photos, logs, etc.)
DATA_DIR = Path(os.environ.get("APPDATA", BASE_DIR)) / "SecureGuard"

# ============================================================
# CONSTANTS
# ============================================================

# Detection
CHECK_INTERVAL = 0.5          # Decoy check interval in seconds
CACHE_INTERVAL = 5.0          # Protection status cache refresh in seconds

# Security
MAX_ATTEMPTS = 3              # Max wrong answers before permanent block
DEFAULT_TIMEOUT = 60          # Default auto-deny timeout in seconds

# Heartbeat
HEARTBEAT_INTERVAL = 30       # Seconds between heartbeat pings

# Notifications
NOTIFICATION_RETRY_COUNT = 1  # Number of retries on notification failure
NOTIFICATION_REPEAT_INTERVAL = 10  # Seconds between repeat notifications (Feature 3)

# UI
POPUP_DENY_DELAY = 500        # ms before popup closes on deny (0.5s)
POPUP_GRANT_DELAY = 1000      # ms before popup closes on grant (1s)
DONE_POPUP_WIDTH = 300
DONE_POPUP_HEIGHT = 100

# Firebase FCM v1 API
FIREBASE_PROJECT_ID = None
if FIREBASE_SA_PATH and FIREBASE_SA_PATH.exists():
    import json as _json
    with open(FIREBASE_SA_PATH) as _f:
        _sa_data = _json.load(_f)
        FIREBASE_PROJECT_ID = _sa_data.get("project_id", "")
FCM_V1_URL = f"https://fcm.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/messages:send" if FIREBASE_PROJECT_ID else None

# ============================================================
# LOGGING SETUP
# ============================================================

LOG_DIR = DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "secureguard.log", encoding="utf-8"),
        logging.StreamHandler()  # Also print to console (hidden in production)
    ]
)

logger = logging.getLogger("SecureGuard")

# ============================================================
# ENSURE DIRECTORIES EXIST
# ============================================================

VAULT_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
(DATA_DIR / "photos").mkdir(parents=True, exist_ok=True)

# Hide vault directory on Windows
import ctypes
try:
    ctypes.windll.kernel32.SetFileAttributesW(str(VAULT_DIR), 0x02)  # FILE_ATTRIBUTE_HIDDEN
except Exception:
    pass

# ============================================================
# CONFIG VALIDATION SUMMARY
# ============================================================

logger.info("=" * 60)
logger.info("SecureGuard Configuration Loaded")
logger.info(f"  Supabase URL : {SUPABASE_URL[:40]}...")
logger.info(f"  PC Name      : {PC_NAME}")
logger.info(f"  Vault Dir    : {VAULT_DIR}")
logger.info(f"  Data Dir     : {DATA_DIR}")
logger.info(f"  Version      : {SOFTWARE_VERSION}")
logger.info("=" * 60)
