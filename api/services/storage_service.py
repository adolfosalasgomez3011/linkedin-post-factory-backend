"""
Supabase Storage Service
Handles media upload/download to Supabase Storage
"""
from supabase import Client
from typing import Optional
import os
import uuid
from datetime import datetime


class StorageService:
    """Manage media assets in Supabase Storage"""
    
    def __init__(self, supabase_client: Client):
        self.client = supabase_client
        self.bucket_name = "post-media"
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist"""
        try:
            # Try to get bucket info
            self.client.storage.get_bucket(self.bucket_name)
        except:
            # Create bucket if it doesn't exist
            try:
                self.client.storage.create_bucket(
                    self.bucket_name,
                    options={"public": True}
                )
            except Exception as e:
                print(f"Bucket creation info: {e}")
    
    def upload_media(
        self,
        file_bytes: bytes,
        post_id: str,
        media_type: str,
        file_extension: str = "png"
    ) -> str:
        """
        Upload media file to Supabase Storage
        
        Args:
            file_bytes: File content as bytes
            post_id: Associated post ID
            media_type: Type of media (code, chart, infographic, etc.)
            file_extension: File extension (png, pdf, jpg)
            
        Returns:
            Public URL of uploaded file
        """
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{post_id}/{media_type}_{timestamp}_{unique_id}.{file_extension}"
        
        # Upload file
        try:
            self.client.storage.from_(self.bucket_name).upload(
                filename,
                file_bytes,
                {"content-type": self._get_content_type(file_extension)}
            )
            
            # Get public URL
            public_url = self.client.storage.from_(self.bucket_name).get_public_url(filename)
            return public_url
            
        except Exception as e:
            print(f"Upload error: {e}")
            raise Exception(f"Failed to upload media: {str(e)}")
    
    def delete_media(self, file_path: str) -> bool:
        """
        Delete media file from storage
        
        Args:
            file_path: Path to file in bucket
            
        Returns:
            Success status
        """
        try:
            self.client.storage.from_(self.bucket_name).remove([file_path])
            return True
        except Exception as e:
            print(f"Delete error: {e}")
            return False
    
    def list_post_media(self, post_id: str) -> list:
        """
        List all media files for a post
        
        Args:
            post_id: Post ID
            
        Returns:
            List of file objects
        """
        try:
            files = self.client.storage.from_(self.bucket_name).list(post_id)
            return files
        except:
            return []
    
    def _get_content_type(self, extension: str) -> str:
        """Get MIME type for file extension"""
        mime_types = {
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'gif': 'image/gif',
            'pdf': 'application/pdf',
            'svg': 'image/svg+xml',
            'html': 'text/html',
        }
        return mime_types.get(extension.lower(), 'application/octet-stream')
