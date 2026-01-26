"""
Supabase Database - Cloud PostgreSQL storage via Supabase REST API
"""
from typing import Dict, List, Optional, Any
import httpx
from datetime import datetime
import os

class SupabaseDatabase:
    def __init__(self):
        self.url = "https://nelzfeoznjuewtnibelt.supabase.co"
        self.key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5lbHpmZW96bmp1ZXd0bmliZWx0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM3MTA4OTIsImV4cCI6MjA3OTI4Njg5Mn0.jrPqbCZDJDESs-8YeX1Pp9H6fmEB2IMa7r1NtCmnYFg"
        
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        
        self.base_url = f"{self.url}/rest/v1"
    
    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Any:
        """Make HTTP request to Supabase"""
        url = f"{self.base_url}/{endpoint}"
        
        with httpx.Client() as client:
            if method == "GET":
                response = client.get(url, headers=self.headers, params=params)
            elif method == "POST":
                response = client.post(url, headers=self.headers, json=data)
            elif method == "PATCH":
                response = client.patch(url, headers=self.headers, json=data, params=params)
            elif method == "DELETE":
                response = client.delete(url, headers=self.headers, params=params)
            
            response.raise_for_status()
            return response.json() if response.text else None
    
    def init_database(self):
        """
        Initialize Supabase tables (run SQL in Supabase dashboard)
        
        Go to: SQL Editor in Supabase dashboard and run:
        
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
        
        CREATE INDEX IF NOT EXISTS idx_posts_pillar ON posts(pillar);
        CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);
        CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at);
        """
        print("⚠️  Run the SQL above in Supabase SQL Editor to create tables")
    
    def save_post(self, post_data: Dict) -> str:
        """Save a post to Supabase"""
        # Convert hashtags list to comma-separated string
        if isinstance(post_data.get('hashtags'), list):
            post_data['hashtags'] = ','.join(post_data['hashtags'])
        
        # Ensure created_at is set
        if 'created_at' not in post_data:
            post_data['created_at'] = datetime.now().isoformat()
        
        result = self._request("POST", "posts", data=post_data)
        return result[0]['id'] if result else post_data['id']
    
    def get_post(self, post_id: str) -> Optional[Dict]:
        """Get a post by ID"""
        try:
            result = self._request("GET", "posts", params={"id": f"eq.{post_id}", "select": "*"})
            return result[0] if result else None
        except:
            return None
    
    def get_posts(self, limit: int = 20, status: Optional[str] = None) -> List[Dict]:
        """Get all posts with optional filters"""
        params = {
            "select": "*",
            "order": "created_at.desc",
            "limit": limit
        }
        
        if status:
            params["status"] = f"eq.{status}"
        
        result = self._request("GET", "posts", params=params)
        return result or []
    
    def update_post(self, post_id: str, **kwargs) -> bool:
        """Update a post"""
        try:
            # Convert hashtags list to string if needed
            if 'hashtags' in kwargs and isinstance(kwargs['hashtags'], list):
                kwargs['hashtags'] = ','.join(kwargs['hashtags'])
            
            self._request("PATCH", "posts", data=kwargs, params={"id": f"eq.{post_id}"})
            return True
        except:
            return False
    
    def delete_post(self, post_id: str) -> bool:
        """Delete a post"""
        try:
            self._request("DELETE", "posts", params={"id": f"eq.{post_id}"})
            return True
        except:
            return False
    
    def get_posts_by_pillar(self, pillar: str, limit: int = 10) -> List[Dict]:
        """Get posts by content pillar"""
        params = {
            "select": "*",
            "pillar": f"eq.{pillar}",
            "order": "created_at.desc",
            "limit": limit
        }
        
        result = self._request("GET", "posts", params=params)
        return result or []
    
    def get_posts_by_date_range(self, start_date: str, end_date: Optional[str] = None) -> List[Dict]:
        """Get posts within date range"""
        params = {
            "select": "*",
            "created_at": f"gte.{start_date}",
            "order": "created_at.desc"
        }
        
        if end_date:
            params["created_at"] = f"gte.{start_date}&created_at=lte.{end_date}"
        
        result = self._request("GET", "posts", params=params)
        return result or []
    
    def save_engagement(self, post_id: str, views: int = 0, likes: int = 0, 
                       comments: int = 0, shares: int = 0) -> bool:
        """Save engagement metrics"""
        try:
            engagement_rate = (likes + comments + shares) / views if views > 0 else 0
            
            data = {
                "post_id": post_id,
                "views": views,
                "likes": likes,
                "comments": comments,
                "shares": shares,
                "engagement_rate": engagement_rate,
                "updated_at": datetime.now().isoformat()
            }
            
            self._request("POST", "engagement", data=data)
            return True
        except:
            return False
    
    def get_engagement(self, post_id: str) -> Optional[Dict]:
        """Get engagement metrics for a post"""
        try:
            params = {
                "select": "*",
                "post_id": f"eq.{post_id}",
                "order": "updated_at.desc",
                "limit": 1
            }
            
            result = self._request("GET", "engagement", params=params)
            return result[0] if result else None
        except:
            return None


if __name__ == "__main__":
    # Test connection
    db = SupabaseDatabase()
    
    print("Testing Supabase connection...")
    print(f"URL: {db.url}")
    
    print("\n⚠️  IMPORTANT: Run this SQL in Supabase SQL Editor first:")
    print("="*60)
    db.init_database()
    print("="*60)
    
    print("\nThen test with:")
    print("db.save_post({'id': 'test-1', 'pillar': 'technology', 'text': 'Test post'})")
