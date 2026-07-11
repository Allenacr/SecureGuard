# SecureGuard v2.0

A two-tier file security system with PC software and mobile app.

## 🛡️ Overview

SecureGuard silently monitors protected files on your PC. When someone tries to open them, it alerts the owner's phone. The owner can **Allow** or **Deny** access remotely from anywhere. If denied, a secret photo of the intruder is taken and saved.

## 📁 Project Structure

```
SecureGuard2/
├── pc_software/          # Python PC monitoring software
│   ├── main.py           # Entry point
│   ├── config.py         # Configuration
│   ├── database.py       # Supabase client
│   ├── file_protector.py # File encryption & vault
│   ├── file_watcher.py   # Folder monitoring (watchdog)
│   ├── decoy_monitor.py  # Decoy access detection
│   ├── notification_sender.py # FCM notifications
│   ├── security_popup.py # Security questions popup
│   ├── done_popup.py     # Done viewing popup
│   ├── photo_capture.py  # Webcam photo capture
│   ├── attempt_tracker.py # Wrong answer tracking
│   ├── keyboard_listener.py # Secret keyword detection
│   ├── settings_panel.py # Settings GUI
│   ├── heartbeat.py      # PC status heartbeat
│   ├── startup.py        # Windows startup
│   └── utils.py          # Utilities
│
├── mobile_app/secureguard/ # Flutter mobile app
│   └── lib/
│       ├── config/       # Theme, routes, Supabase config
│       ├── models/       # Data models
│       ├── providers/    # State management
│       ├── services/     # Auth, database, notifications
│       ├── screens/      # All app screens
│       └── widgets/      # Reusable UI components
│
└── supabase/migrations/  # Database schema
```

## 🚀 Setup

### 1. Database Setup
1. Create a Supabase project at https://supabase.com
2. Run the SQL in `supabase/migrations/001_initial_schema.sql`
3. Create a storage bucket called `intruder-photos`
4. Enable realtime for tables: incidents, settings, protected_files, heartbeat

### 2. PC Software Setup
```bash
cd pc_software
cp .env.example .env
# Edit .env with your Supabase & Firebase credentials
pip install -r requirements.txt
python main.py
```

### 3. Mobile App Setup
```bash
cd mobile_app/secureguard
# Edit lib/config/supabase_config.dart with your credentials
# Add google-services.json to android/app/
flutter pub get
flutter run
```

## 🔑 Required Credentials

| Key | Where to get it |
|-----|----------------|
| SUPABASE_URL | Supabase Dashboard > Settings > API |
| SUPABASE_KEY | Supabase Dashboard > Settings > API (anon key) |
| FCM_SERVER_KEY | Firebase Console > Project Settings > Cloud Messaging |
| google-services.json | Firebase Console > Project Settings > General |

## 📊 Features (69 Total)

### PC Software (46 features)
- ✅ File protection with AES encryption
- ✅ Decoy file placement
- ✅ Folder monitoring & auto-protection
- ✅ Security questions popup
- ✅ Real-time owner decision handling
- ✅ Webcam photo capture on deny
- ✅ Settings panel with secret keyword
- ✅ Windows startup registration
- ✅ Heartbeat monitoring
- ✅ Repeat notifications

### Mobile App (23 features)
- ✅ Login with biometrics (Feature 13)
- ✅ Wrong password lockout (Feature 14)
- ✅ Home with shield status & PC online
- ✅ Alert screen with countdown timer
- ✅ History with intruder photos
- ✅ Notification history (Feature 1)
- ✅ Statistics dashboard (Feature 7)
- ✅ Timeline visualization (Feature 9)
- ✅ Protected files management (Features 4, 5, 6)
- ✅ Remote settings (Features 10, 11, 12)
- ✅ Panic button (Feature 15)
- ✅ Multiple owner accounts (Feature 16)
- ✅ Dark mode (Feature 18)
- ✅ Notification sound customization (Feature 20)

## 🔒 Security

- Files encrypted with AES (Fernet) using per-user key derived from password
- All API keys stored in .env (gitignored)
- Row Level Security (RLS) on all Supabase tables
- Biometric authentication support
- Login attempt lockout protection
