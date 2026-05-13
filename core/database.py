"""
Database management for LinkedIn Post Factory
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path

class PostDatabase:
    def __init__(self, db_path="data/posts.db"):
        self.db_path = Path(__file__).parent.parent / db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Posts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id TEXT PRIMARY KEY,
                pillar TEXT NOT NULL,
                format TEXT,
                topic TEXT,
                text TEXT NOT NULL,
                image_path TEXT,
                hashtags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'draft',
                voice_score REAL,
                length INTEGER
            )
        ''')
        
        # Engagement table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS engagement (
                post_id TEXT PRIMARY KEY,
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                engagement_rate REAL DEFAULT 0.0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES posts (id)
            )
        ''')
        
        # Content balance tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS content_balance (
                period TEXT PRIMARY KEY,
                pillar_data TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_post(self, post_data):
        """Save a generated post to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO posts 
            (id, pillar, format, topic, text, image_path, hashtags, status, voice_score, length)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            post_data['id'],
            post_data['pillar'],
            post_data.get('format'),
            post_data.get('topic'),
            post_data['text'],
            post_data.get('image_path'),
            json.dumps(post_data.get('hashtags', [])),
            post_data.get('status', 'draft'),
            post_data.get('voice_score'),
            len(post_data['text'])
        ))
        
        conn.commit()
        conn.close()
        return post_data['id']
    
    def get_post(self, post_id):
        """Retrieve a post by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = cursor.cursor()
        
        cursor.execute('SELECT * FROM posts WHERE id = ?', (post_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_post(row)
        return None
    
    def get_all_posts(self, status=None):
        """Get all posts, optionally filtered by status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if status:
            cursor.execute('SELECT * FROM posts WHERE status = ? ORDER BY created_at DESC', (status,))
        else:
            cursor.execute('SELECT * FROM posts ORDER BY created_at DESC')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_post(row) for row in rows]
    
    def update_engagement(self, post_id, views=0, likes=0, comments=0, shares=0):
        """Update engagement metrics for a post"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Calculate engagement rate
        engagement_rate = 0
        if views > 0:
            engagement_rate = ((likes + comments * 2 + shares * 3) / views) * 100
        
        cursor.execute('''
            INSERT OR REPLACE INTO engagement 
            (post_id, views, likes, comments, shares, engagement_rate, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (post_id, views, likes, comments, shares, engagement_rate))
        
        conn.commit()
        conn.close()
    
    def get_engagement(self, post_id):
        """Get engagement data for a post"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM engagement WHERE post_id = ?', (post_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'post_id': row[0],
                'views': row[1],
                'likes': row[2],
                'comments': row[3],
                'shares': row[4],
                'engagement_rate': row[5],
                'updated_at': row[6]
            }
        return None
    
    def update_content_balance(self, period, pillar_data):
        """Update content balance for a period"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO content_balance 
            (period, pillar_data, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (period, json.dumps(pillar_data)))
        
        conn.commit()
        conn.close()
    
    def get_content_balance(self, period):
        """Get content balance for a period"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT pillar_data FROM content_balance WHERE period = ?', (period,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return json.loads(row[0])
        return None
    
    def _row_to_post(self, row):
        """Convert database row to post dictionary"""
        return {
            'id': row[0],
            'pillar': row[1],
            'format': row[2],
            'topic': row[3],
            'text': row[4],
            'image_path': row[5],
            'hashtags': json.loads(row[6]) if row[6] else [],
            'created_at': row[7],
            'status': row[8],
            'voice_score': row[9],
            'length': row[10]
        }
