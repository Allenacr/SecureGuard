-- ============================================================
-- SecureGuard — Supabase Database Schema
-- Complete schema for all 69 features
-- ============================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- USERS TABLE (extends Supabase auth.users)
-- ============================================================
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    display_name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own profile" ON public.profiles
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON public.profiles
    FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile" ON public.profiles
    FOR INSERT WITH CHECK (auth.uid() = id);

-- ============================================================
-- DEVICE TOKENS TABLE (FCM tokens for push notifications)
-- Supports Feature 16: Multiple Owner Accounts
-- ============================================================
CREATE TABLE IF NOT EXISTS public.device_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    fcm_token TEXT NOT NULL,
    device_type TEXT DEFAULT 'android',
    device_name TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, fcm_token)
);

ALTER TABLE public.device_tokens ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own device tokens" ON public.device_tokens
    FOR ALL USING (auth.uid() = user_id);

-- ============================================================
-- SETTINGS TABLE (per-user configuration)
-- Supports Features 10, 11, 12, 20
-- ============================================================
CREATE TABLE IF NOT EXISTS public.settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
    protection_enabled BOOLEAN DEFAULT TRUE,
    secret_keyword TEXT DEFAULT 'opensecureguard',
    alert_timeout_seconds INTEGER DEFAULT 60,
    max_attempts INTEGER DEFAULT 3,
    questions JSONB DEFAULT '[
        {"question": "What is your mother maiden name?", "answer": ""},
        {"question": "What is the name of your first pet?", "answer": ""},
        {"question": "What city were you born in?", "answer": ""},
        {"question": "What is your favorite movie?", "answer": ""},
        {"question": "What was the name of your first school?", "answer": ""}
    ]'::jsonb,
    notification_sound TEXT DEFAULT 'default',
    dark_mode BOOLEAN DEFAULT FALSE,
    encryption_key_hash TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.settings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own settings" ON public.settings
    FOR ALL USING (auth.uid() = user_id);

-- ============================================================
-- PROTECTED FILES TABLE
-- Supports Features 4, 5, 6
-- ============================================================
CREATE TABLE IF NOT EXISTS public.protected_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_type TEXT DEFAULT 'file',  -- 'file' or 'folder'
    is_blocked BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    blocked_at TIMESTAMPTZ,
    attempts INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, path)
);

ALTER TABLE public.protected_files ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own protected files" ON public.protected_files
    FOR ALL USING (auth.uid() = user_id);

-- ============================================================
-- INCIDENTS TABLE (access attempts log)
-- ============================================================
CREATE TABLE IF NOT EXISTS public.incidents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    action TEXT DEFAULT 'PENDING',  -- PENDING, ALLOWED, DENIED, AUTO_DENIED, BLOCKED
    owner_decision TEXT,  -- allow, deny, null (pending)
    photo_url TEXT,
    photo_path TEXT,
    ip_address TEXT,
    pc_name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    responded_at TIMESTAMPTZ,
    auto_denied BOOLEAN DEFAULT FALSE,
    answers_correct BOOLEAN
);

ALTER TABLE public.incidents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own incidents" ON public.incidents
    FOR ALL USING (auth.uid() = user_id);

-- ============================================================
-- NOTIFICATION HISTORY TABLE
-- Feature 1: Notification History
-- ============================================================
CREATE TABLE IF NOT EXISTS public.notification_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    incident_id UUID REFERENCES public.incidents(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    read BOOLEAN DEFAULT FALSE,
    notification_type TEXT DEFAULT 'alert'  -- alert, repeat, system
);

ALTER TABLE public.notification_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own notification history" ON public.notification_history
    FOR ALL USING (auth.uid() = user_id);

-- ============================================================
-- HEARTBEAT TABLE
-- Feature 8: Live PC Status
-- ============================================================
CREATE TABLE IF NOT EXISTS public.heartbeat (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
    last_ping TIMESTAMPTZ DEFAULT NOW(),
    pc_name TEXT,
    pc_os TEXT,
    protection_active BOOLEAN DEFAULT TRUE,
    software_version TEXT DEFAULT '2.0.0'
);

ALTER TABLE public.heartbeat ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own heartbeat" ON public.heartbeat
    FOR ALL USING (auth.uid() = user_id);

-- ============================================================
-- OWNER ACCOUNTS TABLE
-- Feature 16: Multiple Owner Accounts
-- ============================================================
CREATE TABLE IF NOT EXISTS public.owner_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    primary_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    member_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT DEFAULT 'member',  -- primary, member
    can_respond BOOLEAN DEFAULT TRUE,
    can_manage_files BOOLEAN DEFAULT FALSE,
    can_manage_settings BOOLEAN DEFAULT FALSE,
    invited_at TIMESTAMPTZ DEFAULT NOW(),
    accepted_at TIMESTAMPTZ,
    UNIQUE(primary_user_id, member_user_id)
);

ALTER TABLE public.owner_accounts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Primary owners can manage accounts" ON public.owner_accounts
    FOR ALL USING (auth.uid() = primary_user_id OR auth.uid() = member_user_id);

-- ============================================================
-- LOGIN ATTEMPTS TABLE
-- Feature 14: Wrong Password Lockout
-- ============================================================
CREATE TABLE IF NOT EXISTS public.login_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT NOT NULL,
    attempt_count INTEGER DEFAULT 0,
    locked_until TIMESTAMPTZ,
    last_attempt TIMESTAMPTZ DEFAULT NOW()
);

-- No RLS needed — managed server-side

-- ============================================================
-- ENABLE REALTIME for key tables
-- ============================================================
ALTER PUBLICATION supabase_realtime ADD TABLE public.incidents;
ALTER PUBLICATION supabase_realtime ADD TABLE public.settings;
ALTER PUBLICATION supabase_realtime ADD TABLE public.protected_files;
ALTER PUBLICATION supabase_realtime ADD TABLE public.heartbeat;
ALTER PUBLICATION supabase_realtime ADD TABLE public.notification_history;

-- ============================================================
-- INDEXES for performance
-- ============================================================
CREATE INDEX idx_incidents_user_id ON public.incidents(user_id);
CREATE INDEX idx_incidents_created_at ON public.incidents(created_at DESC);
CREATE INDEX idx_incidents_action ON public.incidents(action);
CREATE INDEX idx_protected_files_user_id ON public.protected_files(user_id);
CREATE INDEX idx_protected_files_path ON public.protected_files(path);
CREATE INDEX idx_notification_history_user_id ON public.notification_history(user_id);
CREATE INDEX idx_device_tokens_user_id ON public.device_tokens(user_id);
CREATE INDEX idx_heartbeat_user_id ON public.heartbeat(user_id);

-- ============================================================
-- FUNCTIONS
-- ============================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers
CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON public.profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_settings_updated_at BEFORE UPDATE ON public.settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_protected_files_updated_at BEFORE UPDATE ON public.protected_files
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_device_tokens_updated_at BEFORE UPDATE ON public.device_tokens
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- STORAGE BUCKET for intruder photos
-- ============================================================
-- Run in Supabase Dashboard > Storage:
-- Create bucket: 'intruder-photos' (public read, authenticated write)
-- Or via API:
-- INSERT INTO storage.buckets (id, name, public) VALUES ('intruder-photos', 'intruder-photos', true);

-- Storage policies
-- CREATE POLICY "Authenticated users can upload photos"
--     ON storage.objects FOR INSERT
--     WITH CHECK (bucket_id = 'intruder-photos' AND auth.role() = 'authenticated');

-- CREATE POLICY "Anyone can view photos"
--     ON storage.objects FOR SELECT
--     USING (bucket_id = 'intruder-photos');

-- CREATE POLICY "Users can delete own photos"
--     ON storage.objects FOR DELETE
--     USING (bucket_id = 'intruder-photos' AND auth.uid()::text = (storage.foldername(name))[1]);
