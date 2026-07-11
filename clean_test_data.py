import os
import sys
from supabase import create_client, Client

# Add pc_software to path to use config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/pc_software")
from config import SUPABASE_URL, SUPABASE_KEY, USER_EMAIL, USER_PASSWORD
from file_protector import FileProtector

print("SecureGuard Absolute Clean-Up Utility")
print("=====================================")

# Initialize Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Authenticate
print(f"Logging in as {USER_EMAIL}...")
res = supabase.auth.sign_in_with_password({
    "email": USER_EMAIL,
    "password": USER_PASSWORD
})
user_id = res.user.id
print(f"Authenticated successfully! User ID: {user_id}\n")

print("\nRestoring all decoy files back to original...")
protector = FileProtector()
vault_files = protector.get_all_vault_files()

restored_count = 0
for file_info in vault_files:
    original_path = file_info["original_path"]
    if protector.remove_protection(original_path):
        restored_count += 1
        print(f"  -> Restored: {original_path}")
print(f"Successfully restored {restored_count} out of {len(vault_files)} encrypted files.")

print("\nWiping all test data from Supabase...")

# Delete all incidents
incidents = supabase.table("incidents").delete().eq("user_id", user_id).execute()
print(f"Cleared {len(incidents.data)} incidents.")

# Delete all protected files
files = supabase.table("protected_files").delete().eq("user_id", user_id).execute()
print(f"Cleared {len(files.data)} protected files.")

# Delete all notification history
notifs = supabase.table("notification_history").delete().eq("user_id", user_id).execute()
print(f"Cleared {len(notifs.data)} notification histories.")

# Clear attempt trackers
attempts = supabase.table("login_attempts").delete().eq("email", USER_EMAIL).execute()
if attempts.data is not None:
    print(f"Cleared {len(attempts.data)} lockout attempts.")

# Reset settings to default
supabase.table("settings").update({
    "protection_enabled": True,
    "secret_keyword": "Allen2006",
    "alert_timeout_seconds": 60,
    "max_attempts": 3
}).eq("user_id", user_id).execute()
print("Restored default settings (Keyword: Allen2006).")

print("\nCleanup Complete! Your environment is perfectly clean for a fresh test.")
