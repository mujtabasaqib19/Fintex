-- =============================================================================
-- FINTEX — Additional Schema for Auth, Chat History & Chunks
-- Run this AFTER the existing schema.sql in your Supabase SQL Editor
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- 1. USERS TABLE (Firebase Auth sync)
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  firebase_uid TEXT UNIQUE NOT NULL,
  email TEXT NOT NULL,
  display_name TEXT,
  photo_url TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  last_login TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_firebase_uid ON users(firebase_uid);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

COMMENT ON TABLE users IS 'Firebase-authenticated user profiles synced on login';

-- =============================================================================
-- 2. CONVERSATIONS TABLE (Chat sessions)
-- =============================================================================
CREATE TABLE IF NOT EXISTS conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  title TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at DESC);

COMMENT ON TABLE conversations IS 'Chat sessions per user, auto-titled on first message';

-- =============================================================================
-- 3. MESSAGES TABLE (Q&A turns within a conversation)
-- =============================================================================
CREATE TABLE IF NOT EXISTS messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id),
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT 'general',
  subcategory TEXT,
  accuracy_min INTEGER,
  accuracy_max INTEGER,
  source TEXT,
  date TIMESTAMP DEFAULT NOW(),
  metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_category ON messages(category);
CREATE INDEX IF NOT EXISTS idx_messages_date ON messages(date DESC);

COMMENT ON TABLE messages IS 'Individual Q&A turns with accuracy scores and source attribution';

-- =============================================================================
-- 4. CHUNKS TABLE (Synced to Qdrant for RAG)
-- =============================================================================
CREATE TABLE IF NOT EXISTS chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content TEXT NOT NULL,
  question TEXT,
  answer TEXT,
  date TIMESTAMP DEFAULT NOW(),
  category TEXT NOT NULL,
  subcategory TEXT,
  metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_chunks_category ON chunks(category);
CREATE INDEX IF NOT EXISTS idx_chunks_date ON chunks(date DESC);

COMMENT ON TABLE chunks IS 'Answer chunks synced to Qdrant for semantic retrieval';

-- =============================================================================
-- 5. ROW LEVEL SECURITY
-- =============================================================================
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Users can only see their own data
CREATE POLICY "Users read own profile" ON users
  FOR SELECT USING (true);

CREATE POLICY "Users insert own profile" ON users
  FOR INSERT WITH CHECK (true);

CREATE POLICY "Users update own profile" ON users
  FOR UPDATE USING (true);

-- Conversations: users see their own
CREATE POLICY "Conversations user access" ON conversations
  FOR ALL USING (true);

-- Messages: users see their own
CREATE POLICY "Messages user access" ON messages
  FOR ALL USING (true);

-- Chunks: public read for RAG
CREATE POLICY "Chunks public read" ON chunks
  FOR SELECT USING (true);

CREATE POLICY "Chunks insert" ON chunks
  FOR INSERT WITH CHECK (true);
