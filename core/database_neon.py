"""
Neon PostgreSQL database adapter for Post Factory.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
import os

import psycopg2
from psycopg2.extras import RealDictCursor


class NeonDatabase:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL") or os.getenv("NEON_DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL (or NEON_DATABASE_URL) must be set for Neon")
        self.init_database()

    def _connect(self):
        return psycopg2.connect(self.database_url)

    def init_database(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
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

                    CREATE INDEX IF NOT EXISTS idx_posts_channel ON posts(channel);
                    CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);
                    CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at DESC);

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

                    CREATE TABLE IF NOT EXISTS channel_topics (
                        id SERIAL PRIMARY KEY,
                        channel VARCHAR(50) NOT NULL,
                        rank INTEGER NOT NULL,
                        topic_name VARCHAR(255) NOT NULL,
                        reasoning TEXT,
                        source VARCHAR(255),
                        source_title TEXT,
                        source_url TEXT,
                        trend_score NUMERIC,
                        strategic_score NUMERIC,
                        recency_score NUMERIC,
                        channel_fit_score NUMERIC,
                        momentum_score NUMERIC,
                        suggested_pillar VARCHAR(100),
                        suggested_format VARCHAR(100),
                        fetched_at TIMESTAMPTZ DEFAULT NOW(),
                        UNIQUE(channel, topic_name)
                    );

                    ALTER TABLE channel_topics ADD COLUMN IF NOT EXISTS source VARCHAR(255);
                    ALTER TABLE channel_topics ADD COLUMN IF NOT EXISTS source_title TEXT;
                    ALTER TABLE channel_topics ADD COLUMN IF NOT EXISTS source_url TEXT;
                    ALTER TABLE channel_topics ADD COLUMN IF NOT EXISTS trend_score NUMERIC;
                    ALTER TABLE channel_topics ADD COLUMN IF NOT EXISTS strategic_score NUMERIC;
                    ALTER TABLE channel_topics ADD COLUMN IF NOT EXISTS recency_score NUMERIC;
                    ALTER TABLE channel_topics ADD COLUMN IF NOT EXISTS channel_fit_score NUMERIC;
                    ALTER TABLE channel_topics ADD COLUMN IF NOT EXISTS momentum_score NUMERIC;

                    CREATE INDEX IF NOT EXISTS idx_channel_topics_channel_rank
                    ON channel_topics(channel, rank);

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
                    """
                )

    def save_post(self, post_data: Dict[str, Any]) -> str:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO posts
                    (id, channel, pillar, format, topic, text, image_path, hashtags, status, voice_score, length, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, NOW()))
                    ON CONFLICT (id) DO UPDATE SET
                        channel = EXCLUDED.channel,
                        pillar = EXCLUDED.pillar,
                        format = EXCLUDED.format,
                        topic = EXCLUDED.topic,
                        text = EXCLUDED.text,
                        image_path = EXCLUDED.image_path,
                        hashtags = EXCLUDED.hashtags,
                        status = EXCLUDED.status,
                        voice_score = EXCLUDED.voice_score,
                        length = EXCLUDED.length
                    """,
                    (
                        post_data["id"],
                        post_data.get("channel", "personal_career"),
                        post_data["pillar"],
                        post_data.get("format"),
                        post_data.get("topic"),
                        post_data["text"],
                        post_data.get("image_path"),
                        post_data.get("hashtags", ""),
                        post_data.get("status", "draft"),
                        post_data.get("voice_score"),
                        post_data.get("length"),
                        post_data.get("created_at"),
                    ),
                )
        return post_data["id"]

    def get_post(self, post_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM posts WHERE id = %s", (post_id,))
                row = cur.fetchone()
                return dict(row) if row else None

    def get_posts(self, limit: int = 20, status: Optional[str] = None, channel: Optional[str] = None) -> List[Dict[str, Any]]:
        clauses: List[str] = []
        params: List[Any] = []
        if status:
            clauses.append("status = %s")
            params.append(status)
        if channel:
            clauses.append("channel = %s")
            params.append(channel)

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT * FROM posts {where_sql} ORDER BY created_at DESC LIMIT %s"
        params.append(limit)

        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                return [dict(row) for row in cur.fetchall()]

    def update_post(self, post_id: str, **kwargs) -> bool:
        if not kwargs:
            return True

        fields = []
        params: List[Any] = []
        for key, value in kwargs.items():
            fields.append(f"{key} = %s")
            params.append(value)

        params.append(post_id)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(f"UPDATE posts SET {', '.join(fields)} WHERE id = %s", params)
                return cur.rowcount > 0

    def delete_post(self, post_id: str) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM posts WHERE id = %s", (post_id,))
                return cur.rowcount > 0

    def get_posts_by_pillar(self, pillar: str, limit: int = 10) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM posts WHERE pillar = %s ORDER BY created_at DESC LIMIT %s",
                    (pillar, limit),
                )
                return [dict(row) for row in cur.fetchall()]

    def get_posts_by_date_range(self, start_date: str, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        params: List[Any] = [start_date]
        sql = "SELECT * FROM posts WHERE created_at >= %s"
        if end_date:
            sql += " AND created_at <= %s"
            params.append(end_date)
        sql += " ORDER BY created_at DESC"

        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                return [dict(row) for row in cur.fetchall()]

    def save_engagement(
        self,
        post_id: str,
        views: int = 0,
        likes: int = 0,
        comments: int = 0,
        shares: int = 0,
    ) -> bool:
        engagement_rate = (likes + comments + shares) / views if views > 0 else 0
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO engagement (post_id, views, likes, comments, shares, engagement_rate, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """,
                    (post_id, views, likes, comments, shares, engagement_rate),
                )
                return True

    def get_engagement(self, post_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT * FROM engagement
                    WHERE post_id = %s
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    (post_id,),
                )
                row = cur.fetchone()
                return dict(row) if row else None

    def replace_channel_topics(self, channel: str, topics: List[Dict[str, Any]]) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM channel_topics WHERE channel = %s", (channel,))
                for idx, topic in enumerate(topics, start=1):
                    cur.execute(
                        """
                        INSERT INTO channel_topics
                        (
                            channel,
                            rank,
                            topic_name,
                            reasoning,
                            source,
                            source_title,
                            source_url,
                            trend_score,
                            strategic_score,
                            recency_score,
                            channel_fit_score,
                            momentum_score,
                            suggested_pillar,
                            suggested_format,
                            fetched_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        """,
                        (
                            channel,
                            int(topic.get("rank", idx)),
                            topic.get("topic_name") or topic.get("topic") or "",
                            topic.get("reasoning"),
                            topic.get("source"),
                            topic.get("source_title") or topic.get("topic_name") or topic.get("topic"),
                            topic.get("source_url"),
                            topic.get("trend_score"),
                            topic.get("strategic_score"),
                            topic.get("recency_score"),
                            topic.get("channel_fit_score"),
                            topic.get("momentum_score"),
                            topic.get("suggested_pillar") or topic.get("pillar"),
                            topic.get("suggested_format") or topic.get("format"),
                        ),
                    )

    def get_channel_topics(self, channel: str, limit: int = 7) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        channel,
                        rank,
                        topic_name,
                        reasoning,
                        source,
                        source_title,
                        source_url,
                        trend_score,
                        strategic_score,
                        recency_score,
                        channel_fit_score,
                        momentum_score,
                        suggested_pillar,
                        suggested_format,
                        fetched_at
                    FROM channel_topics
                    WHERE channel = %s
                    ORDER BY rank ASC, fetched_at DESC
                    LIMIT %s
                    """,
                    (channel, limit),
                )
                return [dict(row) for row in cur.fetchall()]

    def get_channel_cadence(self, channel: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM channel_cadence WHERE channel = %s", (channel,))
                row = cur.fetchone()
                return dict(row) if row else None

    def touch_channel_last_post(self, channel: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO channel_cadence(channel, target_posts_per_week, last_post_at)
                    VALUES (%s, 1, NOW())
                    ON CONFLICT (channel)
                    DO UPDATE SET last_post_at = NOW()
                    """,
                    (channel,),
                )
