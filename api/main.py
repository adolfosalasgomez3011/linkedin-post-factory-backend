"""
FastAPI Backend for LinkedIn Post Factory
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import sys
import uuid
import base64
from pathlib import Path

# Helper for data URIs
def to_data_uri(data: bytes, mime_type: str) -> str:
    b64 = base64.b64encode(data).decode('utf-8')
    return f"data:{mime_type};base64,{b64}"

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from core.post_generator import PostGenerator
from core.voice_checker import VoiceChecker
from core.content_tracker import ContentTracker
from core.database_supabase import SupabaseDatabase
from api.services.news_service import NewsService

# Try to import media generator (may not exist on all deployments)
try:
    from api.services.media_generator import media_generator
    from api.services.storage_service import StorageService
    MEDIA_ENABLED = True
except ImportError:
    print("Warning: Media generation services not available")
    media_generator = None
    StorageService = None
    MEDIA_ENABLED = False

app = FastAPI(
    title="LinkedIn Post Factory API",
    description="AI-powered LinkedIn content generation with voice consistency",
    version="1.0.0"
)

# Health check endpoint for deployment platforms
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
generator = PostGenerator()
checker = VoiceChecker()
tracker = ContentTracker()
db = SupabaseDatabase()
news_service = NewsService()

# Initialize storage service if available
storage_service = None
if MEDIA_ENABLED and StorageService:
    try:
        storage_service = StorageService(db.supabase if db and hasattr(db, 'supabase') else None)
    except Exception as e:
        print(f"Warning: Could not initialize storage service: {e}")

# ========================================
# REQUEST/RESPONSE MODELS
# ========================================

class GeneratePostRequest(BaseModel):
    pillar: str = Field(..., description="Content pillar (asset_management, technology, etc.)")
    format_type: str = Field(..., description="Post format (insight, story, data, question, contrarian)")
    topic: Optional[str] = Field(None, description="Specific topic for the post")
    language: Optional[str] = Field("english", description="Language (english, spanish, both)")
    provider: str = Field("gemini", description="AI provider (gemini, gpt4)")

class BatchGenerateRequest(BaseModel):
    count: int = Field(10, ge=1, le=50, description="Number of posts to generate")
    pillar_distribution: Optional[Dict[str, float]] = Field(None, description="Custom pillar distribution")
    provider: Optional[str] = Field(None, description="Force specific provider (or randomize)")

class CheckVoiceRequest(BaseModel):
    text: str = Field(..., description="Post text to check")

class UpdatePostRequest(BaseModel):
    text: str = Field(..., description="Updated post text")
    hashtags: Optional[List[str]] = Field(None, description="Updated hashtags")

class PostResponse(BaseModel):
    id: Optional[str] = None  # Changed to str for UUID
    pillar: str
    format: str
    topic: Optional[str]
    text: str
    hashtags: List[str]  # List of hashtag strings
    voice_score: Optional[float] = None
    length: int
    created_at: Optional[str] = None
    status: str = "draft"

class VoiceCheckResponse(BaseModel):
    score: float
    grade: str
    issues: List[str]
    components: Dict[str, bool]
    length: int
    length_status: str
    recommendation: str

class DashboardResponse(BaseModel):
    overall_health: float
    health_grade: str
    summary: Dict
    pillar_balance: Dict
    posting_cadence: Dict
    next_recommended_pillar: str

# ========================================
# ENDPOINTS
# ========================================

@app.get("/")
async def root():
    """API health check"""
    return {
        "status": "online",
        "service": "LinkedIn Post Factory API",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "post_generator": "ready",
            "voice_checker": "ready",
            "content_tracker": "ready",
            "database": "ready"
        }
    }

@app.post("/posts/generate", response_model=PostResponse)
async def generate_post(request: GeneratePostRequest):
    """
    Generate a single LinkedIn post
    
    - **pillar**: Content pillar (asset_management, technology, consulting, entrepreneurship, thought_leadership)
    - **format_type**: Post format (insight, story, data, question, contrarian)
    - **topic**: Optional specific topic
    - **provider**: AI provider (claude, gpt4, gemini)
    """
    try:
        # Generate post
        post = generator.generate_post(
            pillar=request.pillar,
            format_type=request.format_type,
            topic=request.topic,
            language=request.language or "english",
            provider=request.provider
        )
        
        # Check voice
        score, issues = checker.check_post(post["text"])
        
        # Save to database
        post_id = str(uuid.uuid4())
        
        # Prepare hashtags - convert string to comma-separated for Supabase
        hashtags_str = post["hashtags"] if isinstance(post["hashtags"], str) else " ".join(post["hashtags"])
        
        db.save_post({
            "id": post_id,
            "pillar": post["pillar"],
            "format": post["format"],
            "topic": post.get("topic", ""),
            "text": post["text"],
            "hashtags": hashtags_str,
            "voice_score": float(score),
            "length": int(len(post["text"])),
            "status": "draft"
        })
        
        # Prepare hashtags for response - split string into list
        hashtags_list = hashtags_str.split() if hashtags_str else []
        
        return PostResponse(
            id=post_id,
            pillar=post["pillar"],
            format=post["format"],
            topic=post.get("topic", ""),
            text=post["text"],
            hashtags=hashtags_list,
            voice_score=score,
            length=len(post["text"]),
            created_at=datetime.now().isoformat(),
            status="draft"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@app.post("/posts/batch")
async def batch_generate(request: BatchGenerateRequest, background_tasks: BackgroundTasks):
    """
    Generate multiple posts in batch
    
    - **count**: Number of posts to generate (1-50)
    - **pillar_distribution**: Optional custom distribution
    - **provider**: Optional forced provider
    """
    try:
        posts = generator.batch_generate(
            count=request.count,
            pillar_distribution=request.pillar_distribution
        )
        
        results = []
        for post in posts:
            # Check voice
            score, _ = checker.check_post(post["text"])
            
            # Save to database
            post_id = str(uuid.uuid4())
            db.save_post({
                "id": post_id,
                "pillar": post["pillar"],
                "format": post["format"],
                "topic": post.get("topic"),
                "text": post["text"],
                "hashtags": post["hashtags"],
                "voice_score": score,
                "length": len(post["text"]),
                "status": "draft"
            })
            
            results.append({
                "id": post_id,
                "pillar": post["pillar"],
                "format": post["format"],
                "voice_score": score,
                "length": len(post["text"]),
                "status": "draft"
            })
        
        return {
            "generated": len(results),
            "posts": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch generation failed: {str(e)}")

@app.post("/posts/check-voice", response_model=VoiceCheckResponse)
async def check_voice(request: CheckVoiceRequest):
    """
    Check voice authenticity of post text
    
    Returns score (0-100), grade (A-F), issues, and recommendations
    """
    try:
        report = checker.get_detailed_report(request.text)
        
        return VoiceCheckResponse(**report)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice check failed: {str(e)}")

@app.get("/posts", response_model=List[PostResponse])
async def list_posts(
    limit: int = 20,
    status: Optional[str] = None,
    pillar: Optional[str] = None,
    min_score: Optional[float] = None
):
    """
    List all posts with optional filters
    
    - **limit**: Max posts to return
    - **status**: Filter by status (draft, scheduled, published)
    - **pillar**: Filter by content pillar
    - **min_score**: Filter by minimum voice score
    """
    try:
        posts = db.get_posts(limit=limit, status=status)
        
        results = []
        for post in posts:
            # Apply filters
            if pillar and post.get('pillar') != pillar:
                continue
            if min_score and (post.get('voice_score') is None or post.get('voice_score') < min_score):
                continue
            
            # Parse hashtags
            hashtags = post.get('hashtags', '').split(',') if post.get('hashtags') else []
            
            results.append(PostResponse(
                id=post.get('id'),
                pillar=post.get('pillar'),
                format=post.get('format'),
                topic=post.get('topic'),
                text=post.get('text'),
                hashtags=hashtags,
                voice_score=post.get('voice_score'),
                length=post.get('length'),
                created_at=post.get('created_at'),
                status=post.get('status', 'draft')
            ))
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list posts: {str(e)}")

@app.get("/posts/{post_id}", response_model=PostResponse)
async def get_post(post_id: str):
    """Get specific post by ID"""
    try:
        post = db.get_post(post_id)
        
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        hashtags = post.get('hashtags', '').split(',') if post.get('hashtags') else []
        
        return PostResponse(
            id=post.get('id'),
            pillar=post.get('pillar'),
            format=post.get('format'),
            topic=post.get('topic'),
            text=post.get('text'),
            hashtags=hashtags,
            voice_score=post.get('voice_score'),
            length=post.get('length'),
            created_at=post.get('created_at'),
            status=post.get('status', 'draft')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get post: {str(e)}")

@app.put("/posts/{post_id}", response_model=PostResponse)
async def update_post(post_id: str, request: UpdatePostRequest):
    """Update post text and/or hashtags"""
    try:
        # Get existing post
        post = db.get_post(post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        # Check new voice score
        score, _ = checker.check_post(request.text)
        
        # Update post
        update_data = {
            "text": request.text,
            "voice_score": score,
            "length": len(request.text)
        }
        
        if request.hashtags:
            update_data["hashtags"] = ",".join(request.hashtags)
        
        db.update_post(post_id, **update_data)
        
        hashtags = request.hashtags or post.get('hashtags', '').split(',')
        
        return PostResponse(
            id=post_id,
            pillar=post.get('pillar'),
            format=post.get('format'),
            topic=post.get('topic'),
            text=request.text,
            hashtags=hashtags,
            voice_score=score,
            length=len(request.text),
            created_at=post.get('created_at'),
            status=post.get('status', 'draft')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update post: {str(e)}")

@app.delete("/posts/{post_id}")
async def delete_post(post_id: str):
    """Delete post by ID"""
    try:
        db.delete_post(post_id)
        return {"message": f"Post {post_id} deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete post: {str(e)}")

@app.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard():
    """
    Get content health dashboard
    
    Returns overall health score, pillar balance, posting cadence, and recommendations
    """
    try:
        dashboard = tracker.get_dashboard()
        
        return DashboardResponse(**dashboard)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard: {str(e)}")

@app.get("/recommendations/next-pillar")
async def get_next_pillar():
    """Get recommended pillar for next post"""
    try:
        next_pillar = tracker.get_next_pillar_needed()
        
        return {
            "recommended_pillar": next_pillar,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recommendation: {str(e)}")

@app.get("/stats")
async def get_stats():
    """Get overall statistics"""
    try:
        dashboard = tracker.get_dashboard()
        posts = db.get_posts(limit=1000)
        
        # Calculate stats
        total_posts = len(posts)
        avg_score = sum(p.get('voice_score', 0) for p in posts if p.get('voice_score')) / total_posts if total_posts > 0 else 0
        published = sum(1 for p in posts if p.get('status') == "published")
        drafts = sum(1 for p in posts if p.get('status') == "draft")
        
        return {
            "total_posts": total_posts,
            "published": published,
            "drafts": drafts,
            "avg_voice_score": round(avg_score, 1),
            "health": {
                "score": dashboard["overall_health"],
                "grade": dashboard["health_grade"]
            },
            "posting": {
                "posts_per_week": dashboard["posting_cadence"]["posts_per_week"],
                "consistency": dashboard["posting_cadence"]["consistency"]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


# ============================================
# MEDIA GENERATION REQUEST MODELS
# ============================================

class CodeImageRequest(BaseModel):
    code: str
    language: str = "python"
    theme: str = "monokai"
    title: Optional[str] = None
    post_id: Optional[str] = None
    save_to_storage: bool = True

class ChartRequest(BaseModel):
    chart_type: str  # bar, line, pie, scatter, area, funnel
    data: Dict
    title: str
    theme: str = "plotly_dark"
    post_id: Optional[str] = None
    save_to_storage: bool = True

class InfographicRequest(BaseModel):
    title: str
    stats: List[Dict[str, str]]
    brand_color: str = "#4a9eff"
    post_id: Optional[str] = None
    save_to_storage: bool = True

class QRCodeRequest(BaseModel):
    url: str
    logo_path: Optional[str] = None
    post_id: Optional[str] = None
    save_to_storage: bool = True

class CarouselRequest(BaseModel):
    slides: List[Dict[str, str]]
    title: str
    style: str = "professional"  # professional, relaxed, corporate, creative, minimal
    post_id: Optional[str] = None
    save_to_storage: bool = True
    content_pillar: Optional[str] = None
    post_type: Optional[str] = None
    format: Optional[str] = None
    topic: Optional[str] = None

class AIImageRequest(BaseModel):
    prompt: str
    style: str = "professional"
    post_id: Optional[str] = None
    save_to_storage: bool = True

class InteractiveRequest(BaseModel):
    prompt: str
    title: str
    post_id: Optional[str] = None
    save_to_storage: bool = True


# ============================================
# MEDIA GENERATION ENDPOINTS
# ============================================

@app.post("/media/generate-interactive")
async def generate_interactive(request: InteractiveRequest):
    """Generate interactive HTML demo"""
    if not MEDIA_ENABLED:
        raise HTTPException(status_code=501, detail="Media generation not available")
    try:
        html_bytes = await media_generator.generate_interactive_html(
            prompt=request.prompt,
            title=request.title
        )
        
        url = None
        if request.save_to_storage and storage_service and request.post_id:
            try:
                url = storage_service.upload_media(
                    html_bytes,
                    request.post_id,
                    "interactive",
                    "html"
                )
            except Exception as e:
                print(f"Storage upload failed: {e}")
        
        if not url:
            url = to_data_uri(html_bytes, "text/html")

        return {"success": True, "url": url, "type": "interactive"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating interactive demo: {str(e)}")

@app.post("/media/generate-code-image")
async def generate_code_image(request: CodeImageRequest):
    """Generate beautiful code snippet image"""
    if not MEDIA_ENABLED:
        raise HTTPException(status_code=501, detail="Media generation not available")
    try:
        img_bytes = media_generator.generate_code_image(
            code=request.code,
            language=request.language,
            theme=request.theme,
            title=request.title
        )
        
        url = None
        if request.save_to_storage and storage_service and request.post_id:
            try:
                url = storage_service.upload_media(
                    img_bytes,
                    request.post_id,
                    "code",
                    "png"
                )
            except Exception as e:
                print(f"Storage upload failed: {e}")
        
        if not url:
            url = to_data_uri(img_bytes, "image/png")

        return {"success": True, "url": url, "type": "code"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating code image: {str(e)}")


@app.post("/media/generate-chart")
async def generate_chart(request: ChartRequest):
    """Generate interactive-style chart"""
    if not MEDIA_ENABLED:
        raise HTTPException(status_code=501, detail="Media generation not available")
    try:
        img_bytes = media_generator.generate_chart(
            chart_type=request.chart_type,
            data=request.data,
            title=request.title,
            theme=request.theme
        )
        
        url = None
        if request.save_to_storage and storage_service and request.post_id:
            try:
                url = storage_service.upload_media(
                    img_bytes,
                    request.post_id,
                    "chart",
                    "png"
                )
            except Exception as e:
                print(f"Storage upload failed: {e}")
        
        if not url:
            url = to_data_uri(img_bytes, "image/png")

        return {"success": True, "url": url, "type": "chart"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating chart: {str(e)}")


@app.post("/media/generate-infographic")
async def generate_infographic(request: InfographicRequest):
    """Generate infographic with statistics"""
    if not MEDIA_ENABLED:
        raise HTTPException(status_code=501, detail="Media generation not available")
    try:
        img_bytes = media_generator.generate_infographic(
            title=request.title,
            stats=request.stats,
            brand_color=request.brand_color
        )
        
        url = None
        if request.save_to_storage and storage_service and request.post_id:
            try:
                url = storage_service.upload_media(
                    img_bytes,
                    request.post_id,
                    "infographic",
                    "png"
                )
            except Exception as e:
                print(f"Storage upload failed: {e}")
        
        if not url:
            url = to_data_uri(img_bytes, "image/png")

        return {"success": True, "url": url, "type": "infographic"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating infographic: {str(e)}")


@app.post("/media/generate-qrcode")
async def generate_qrcode(request: QRCodeRequest):
    """Generate QR code"""
    if not MEDIA_ENABLED:
        raise HTTPException(status_code=501, detail="Media generation not available")
    try:
        img_bytes = media_generator.generate_qr_code(
            url=request.url,
            logo_path=request.logo_path
        )
        
        url = None
        if request.save_to_storage and storage_service and request.post_id:
            try:
                url = storage_service.upload_media(
                    img_bytes,
                    request.post_id,
                    "qrcode",
                    "png"
                )
            except Exception as e:
                print(f"Storage upload failed: {e}")
        
        if not url:
            url = to_data_uri(img_bytes, "image/png")

        return {"success": True, "url": url, "type": "qrcode"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating QR code: {str(e)}")


@app.post("/media/generate-carousel")
async def generate_carousel(request: CarouselRequest):
    """Generate PDF carousel"""
    if not MEDIA_ENABLED:
        raise HTTPException(status_code=501, detail="Media generation not available")
    try:
        # DEBUG: Print what we received
        print("\n========== CAROUSEL REQUEST DEBUG ==========")
        print(f"Title: {request.title}")
        print(f"Content Pillar: {request.content_pillar}")
        print(f"Post Type: {request.post_type}")
        print(f"Format: {request.format}")
        print(f"Topic: {request.topic}")
        print(f"Style: {request.style}")
        print("============================================\n")
        
        pdf_bytes = media_generator.generate_carousel_pdf(
            slides=request.slides,
            title=request.title,
            style=request.style
        )
        
        # Save to local filesystem
        local_path = None
        try:
            from datetime import datetime
            import os
            import re
            
            # Create folder if doesn't exist
            base_folder = r"C:\Users\USER\OneDrive\LinkedIn_PersonalBrand\LinkedInAIPosts"
            os.makedirs(base_folder, exist_ok=True)
            print(f"DEBUG: Base folder: {base_folder}")
            
            # Get current date
            now = datetime.now()
            month = now.strftime("%b")  # Jan, Feb, Mar, etc.
            year = now.strftime("%y")   # 26 for 2026
            
            # Clean fields for filename
            content_pillar = re.sub(r'[^\w\s-]', '', request.content_pillar or "General").replace(" ", "")
            post_type = re.sub(r'[^\w\s-]', '', request.post_type or "Standard").replace(" ", "")
            format_type = re.sub(r'[^\w\s-]', '', request.format or "Text").replace(" ", "")
            topic = re.sub(r'[^\w\s-]', '', request.topic or request.title or "Post").replace(" ", "")[:30]
            
            print(f"DEBUG: Cleaned - pillar={content_pillar}, type={post_type}, format={format_type}, topic={topic}")
            
            # Find next correlative number
            base_name = f"{month}_{year}_{content_pillar}_{post_type}_{format_type}_{topic}"
            print(f"DEBUG: Base name: {base_name}")
            
            correlative = 1
            while True:
                filename = f"{base_name}_{correlative:02d}.pdf"
                filepath = os.path.join(base_folder, filename)
                if not os.path.exists(filepath):
                    break
                correlative += 1
            
            print(f"DEBUG: Final filepath: {filepath}")
            
            # Save file
            with open(filepath, 'wb') as f:
                f.write(pdf_bytes)
            
            local_path = filepath
            print(f"✓ Carousel would save to: {filepath}")
        except Exception as e:
            print(f"✗ Path generation failed: {e}")
            import traceback
            traceback.print_exc()
            # Set defaults if path generation failed
            month = "Jan"
            year = "26"
            content_pillar = "General"
            post_type = "Standard"
            format_type = "Text"
            topic = "Post"
            correlative = 1
        
        # Generate filename for download
        filename = f"{month}_{year}_{content_pillar}_{post_type}_{format_type}_{topic}_{correlative:02d}.pdf"
        print(f"DEBUG: Download filename: {filename}")
        
        # Return PDF as downloadable file
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": "application/pdf"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating carousel: {str(e)}")


@app.post("/media/generate-ai-image")
async def generate_ai_image(request: AIImageRequest):
    """Generate AI-powered image"""
    if not MEDIA_ENABLED:
        raise HTTPException(status_code=501, detail="Media generation not available")
    try:
        img_bytes = await media_generator.generate_ai_image(
            prompt=request.prompt,
            style=request.style
        )
        
        url = None
        if request.save_to_storage and storage_service and request.post_id:
            try:
                url = storage_service.upload_media(
                    img_bytes,
                    request.post_id,
                    "ai-image",
                    "png"
                )
            except Exception as e:
                print(f"Storage upload failed: {e}")
        
        if not url:
            url = to_data_uri(img_bytes, "image/png")

        return {"success": True, "url": url, "type": "ai-image"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating AI image: {str(e)}")


@app.get("/media/list/{post_id}")
async def list_post_media(post_id: str):
    """List all media assets for a post"""
    if not MEDIA_ENABLED:
        return {"media": []}
    try:
        if not storage_service:
            return {"media": []}
        
        files = storage_service.list_post_media(post_id)
        return {"post_id": post_id, "media": files}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing media: {str(e)}")


# ============================================
# NEWS & TRENDING ENDPOINTS
# ============================================

@app.get("/news/trending")
async def get_trending_news(category: str = "technology", count: int = 15):
    """
    Get trending news articles for content generation
    
    - **category**: News category (technology, ai, business, leadership)
    - **count**: Number of articles to return (default: 15)
    """
    try:
        articles = news_service.get_trending_articles(category=category, count=count)
        return {
            "articles": articles,
            "count": len(articles),
            "category": category
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch trending news: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
