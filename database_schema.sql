-- LinkedIn Post Factory - Supabase Database Schema
-- Run this in Supabase SQL Editor: https://app.supabase.com/project/nelzfeoznjuewtnibelt/sql

-- Posts table
CREATE TABLE IF NOT EXISTS posts (
    id TEXT PRIMARY KEY,
    pillar TEXT NOT NULL,
    format TEXT,
    topic TEXT,
    text TEXT NOT NULL,
    image_path TEXT,
    hashtags TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    status TEXT DEFAULT 'draft',
    voice_score NUMERIC,
    length INTEGER
);

-- Engagement tracking table
CREATE TABLE IF NOT EXISTS engagement (
    id SERIAL PRIMARY KEY,
    post_id TEXT REFERENCES posts(id) ON DELETE CASCADE,
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    engagement_rate NUMERIC,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_posts_pillar ON posts(pillar);
CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);
CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_voice_score ON posts(voice_score);
CREATE INDEX IF NOT EXISTS idx_engagement_post_id ON engagement(post_id);

-- Enable Row Level Security (RLS)
ALTER TABLE posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE engagement ENABLE ROW LEVEL SECURITY;

-- Policies (allow all operations for now - tighten in production)
CREATE POLICY "Enable all operations for posts" ON posts
    FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Enable all operations for engagement" ON engagement
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Sample data (optional - remove if not needed)
INSERT INTO posts (id, pillar, format, topic, text, hashtags, voice_score, length, status)
VALUES 
    ('sample-1', 'technology', 'insight', 'AI in mining', 'Last week I ran the numbers on our new AI system at the Toquepala mine. Board demanded 15% uptime improvement. Delivered 23%.', '#Mining,#AI,#Operations', 92.5, 147, 'published')
ON CONFLICT (id) DO NOTHING;

-- Verify tables created
SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public' 
AND table_name IN ('posts', 'engagement');
