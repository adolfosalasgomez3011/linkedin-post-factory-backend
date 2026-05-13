-- LinkedIn Post Factory - Neon PostgreSQL Schema
-- Run this script in your Neon SQL editor.

-- Posts table
CREATE TABLE IF NOT EXISTS posts (
    id TEXT PRIMARY KEY,
    channel VARCHAR(50) NOT NULL DEFAULT 'personal_career',
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
CREATE INDEX IF NOT EXISTS idx_posts_channel ON posts(channel);
CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);
CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_voice_score ON posts(voice_score);
CREATE INDEX IF NOT EXISTS idx_engagement_post_id ON engagement(post_id);

-- Channel topic queue (7-impact-topic list per channel)
CREATE TABLE IF NOT EXISTS channel_topics (
    id SERIAL PRIMARY KEY,
    channel VARCHAR(50) NOT NULL,
    rank INTEGER NOT NULL,
    topic_name VARCHAR(255) NOT NULL,
    reasoning TEXT,
    suggested_pillar VARCHAR(100),
    suggested_format VARCHAR(100),
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(channel, topic_name)
);

CREATE INDEX IF NOT EXISTS idx_channel_topics_channel_rank
ON channel_topics(channel, rank);

-- Cadence targets per channel
CREATE TABLE IF NOT EXISTS channel_cadence (
    channel VARCHAR(50) PRIMARY KEY,
    target_posts_per_week INTEGER NOT NULL,
    last_post_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO channel_cadence (channel, target_posts_per_week)
VALUES ('personal_career', 3)
ON CONFLICT (channel) DO NOTHING;

INSERT INTO channel_cadence (channel, target_posts_per_week)
VALUES ('goalpraxis_company', 2)
ON CONFLICT (channel) DO NOTHING;

INSERT INTO channel_cadence (channel, target_posts_per_week)
VALUES ('other', 1)
ON CONFLICT (channel) DO NOTHING;

-- Sample data (optional - remove if not needed)
INSERT INTO posts (id, channel, pillar, format, topic, text, hashtags, voice_score, length, status)
VALUES 
    ('sample-1', 'personal_career', 'technology', 'insight', 'AI in mining', 'Last week I ran the numbers on our new AI system at the Toquepala mine. Board demanded 15% uptime improvement. Delivered 23%.', '#Mining,#AI,#Operations', 92.5, 147, 'published')
ON CONFLICT (id) DO NOTHING;

-- Verify tables created
SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public' 
AND table_name IN ('posts', 'engagement');
