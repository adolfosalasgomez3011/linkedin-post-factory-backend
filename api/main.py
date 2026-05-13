"""
FastAPI Backend for LinkedIn Post Factory
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Response, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import sys
import uuid
import io
import base64
import os
import re
import requests as _requests
import asyncio
import google.generativeai as genai
from pathlib import Path
from dotenv import load_dotenv

# Helper for data URIs
def to_data_uri(data: bytes, mime_type: str) -> str:
    b64 = base64.b64encode(data).decode('utf-8')
    return f"data:{mime_type};base64,{b64}"

# Ensure the project root is importable regardless of current working directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Always load environment variables from Post_Factory/.env.
load_dotenv(PROJECT_ROOT / ".env")

from core.post_generator import PostGenerator
from core.voice_checker import VoiceChecker
from core.content_tracker import ContentTracker
from core.database_neon import NeonDatabase
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

# ---------------------------------------------------------------------------
# Article fetch + stat extraction helpers (used at generation time)
# ---------------------------------------------------------------------------

# Signals that indicate the page is a paywall/subscription gate rather than real article content.
_PAYWALL_SIGNALS = [
    'subscribe for access',
    'subscriber exclusive',
    'subscriber-only',
    'your first complimentary story',
    'claim offer',
    'sign in to read',
    'subscribe to read',
    'this is a subscriber',
    'get access to',
    'unlimited access',
    'digital subscription',
    'subscribe now',
    'create a free account',
    'register to read',
    'metered paywall',
    'already a subscriber',
]

# Minimum characters of substantive article body needed to treat fetched content as real text.
_MIN_ARTICLE_BODY_CHARS = 600

def _is_paywall_content(text: str) -> bool:
    """Return True if the fetched text looks like a paywall gate rather than the actual article."""
    lower = text.lower()
    hits = sum(1 for sig in _PAYWALL_SIGNALS if sig in lower)
    if hits < 2:
        return False
    # Strip likely-paywall sentences to estimate remaining substantive content
    lines = [ln.strip() for ln in text.splitlines() if len(ln.strip()) > 30]
    paywall_lines = [ln for ln in lines if any(sig in ln.lower() for sig in _PAYWALL_SIGNALS)]
    non_paywall_lines = [ln for ln in lines if ln not in paywall_lines]
    substantive_chars = sum(len(ln) for ln in non_paywall_lines)
    return substantive_chars < _MIN_ARTICLE_BODY_CHARS

_STAT_PATTERNS = [
    re.compile(r'[^.!?]*\d+(?:\.\d+)?%[^.!?]*[.!?]'),
    re.compile(r'[^.!?]*\d+(?:\.\d+)?\s*(?:times|x)[^.!?]*[.!?]', re.IGNORECASE),
    re.compile(r'[^.!?]*(?:doubled|tripled|halved|quadrupled)[^.!?]*[.!?]', re.IGNORECASE),
    re.compile(r'[^.!?]*(?:decreased|increased|grew|declined|fell|rose)\s+by\s+\d+[^.!?]*[.!?]', re.IGNORECASE),
    re.compile(r'[^.!?]*from \d{4} to \d{4}[^.!?]*[.!?]', re.IGNORECASE),
    re.compile(r'[^.!?]*\$\d+[bmk]?[^.!?]*[.!?]', re.IGNORECASE),
    re.compile(r'[^.!?]*(?:productivity|output|efficiency)[^.!?]*(?:decrease|increase|double|half)[^.!?]*[.!?]', re.IGNORECASE),
    re.compile(r'[^.!?]*(?:OECD|McKinsey|World Bank|IMF|IEA|Deloitte|PwC|Accenture)[^.!?]*\d+[^.!?]*[.!?]', re.IGNORECASE),
]

def _extract_stat_sentences(text: str, source_name: str) -> list:
    """Extract stat-bearing sentences from plain text using regex patterns."""
    findings: list = []
    seen: set = set()
    for pattern in _STAT_PATTERNS:
        for m in pattern.finditer(text):
            sentence = m.group(0).strip()
            if len(sentence) >= 40 and sentence not in seen:
                seen.add(sentence)
                findings.append({"finding": sentence, "source_attribution": source_name})
            if len(findings) >= 5:
                return findings
    return findings

async def fetch_findings_for_url(url: str, source_name: str) -> tuple:
    """
    Fetch article via Jina AI (handles Google News redirect chains) then extract stat findings.
    Returns (findings: list, article_text: str, error_reason: str).
    article_text is empty string if fetch failed; error_reason explains why.
    Called at generation time when key_findings were not pre-extracted by the Vercel endpoint.
    """
    if not url or not url.startswith('http'):
        return [], "", "No valid article URL was provided with this topic."

    resolved_url_holder = [url]

    def _sync_fetch() -> str:
        resolved_url = url
        # Resolve Google News RSS redirect URLs to the actual article URL
        if 'news.google.com' in url:
            try:
                r = _requests.get(
                    url, timeout=10, allow_redirects=True,
                    headers={'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1)'}
                )
                if r.url and 'news.google.com' not in r.url:
                    resolved_url = r.url
                else:
                    resolved_url = r.url
            except Exception:
                pass

        resolved_url_holder[0] = resolved_url
        jina_url = f"https://r.jina.ai/{resolved_url}"
        resp = _requests.get(
            jina_url,
            headers={"Accept": "text/plain", "X-Return-Format": "text"},
            timeout=25,
            allow_redirects=True,
        )
        return resp.text if resp.status_code == 200 else ""

    try:
        raw = await asyncio.get_event_loop().run_in_executor(None, _sync_fetch)
        if not raw or len(raw.strip()) < 100:
            domain = resolved_url_holder[0].split('/')[2] if '/' in resolved_url_holder[0] else url
            return [], "", (
                f"Could not retrieve article content from '{domain}'. "
                f"The page may be paywalled, geo-blocked, or the URL may have expired. "
                f"Please open the article and paste its text into 'Paste article text directly', then retry."
            )

        # Clean Jina markdown formatting before paywall check and extraction
        text = re.sub(r'!\[.*?\]\(.*?\)', '', raw)
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

        # Detect paywall pages — these look like real content but contain no article body
        if _is_paywall_content(text):
            domain = resolved_url_holder[0].split('/')[2] if '/' in resolved_url_holder[0] else url
            return [], "", (
                f"The article at '{domain}' is behind a paywall — only the subscription gate was retrieved, not the article content. "
                f"To generate a post grounded in the real article, please open it in your browser, "
                f"copy the full text, and paste it into 'Paste article text directly', then retry."
            )

        findings = _extract_stat_sentences(text[:8000], source_name)
        return findings, text[:4000], ""
    except Exception as exc:
        return [], "", f"Failed to fetch article content: {str(exc)}"

app = FastAPI(
    description="AI-powered LinkedIn content generation with voice consistency",
    version="1.0.0"
)

service_init_errors: Dict[str, str] = {}

# Health check endpoint for deployment platforms
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    status = "healthy" if not service_init_errors else "degraded"
    return {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "service_init_errors": service_init_errors,
    }

@app.get("/debug/diagnose")
async def diagnose_environment():
    """Diagnostic endpoint to check environment and available models"""
    
    # 1. Check System Time
    system_time = datetime.now()
    
    # 2. Check API Key presence
    api_key = os.getenv("GOOGLE_API_KEY")
    vertex_creds = os.getenv("GCP_CREDENTIALS_JSON_B64")
    
    api_key_status = "Not Set"
    vertex_status = "Not Configured"
    
    if api_key:
        masked_key = f"{api_key[:4]}...{api_key[-4:]}"
        api_key_status = f"Present ({masked_key})"
        try:
            # Force REST transport for diagnostics
            genai.configure(api_key=api_key, transport='rest')
        except Exception as e:
            api_key_status = f"Error configuring: {str(e)}"
            
    if vertex_creds:
        vertex_status = "Configured (Ready for Bypass)"
    
    # 3. List Available Models
    available_models = []
    error_message = None
    
    try:
        # Check if OpenAI is available as fallback
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
             available_models.append({"name": "gpt-4o", "display_name": "OpenAI GPT-4o (Fallback Available)"})

        if api_key:
            models = genai.list_models()
            # Filter to relevant models and convert to list of dicts
            for m in models:
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append({
                        "name": m.name,
                        "display_name": m.display_name
                    })
    except Exception as e:
        error_message = str(e)

    # 4. Check Environment Variables
    env_vars = {
        "RENDER": os.getenv("RENDER"),
        "RENDER_SERVICE_ID": os.getenv("RENDER_SERVICE_ID"),
        "REGION": os.getenv("RENDER_REGION"), # Render specific
    }

    return {
        "system_time": system_time.isoformat(),
        "api_key_status": api_key_status,
        "vertex_ai_status": vertex_status,
        "environment": env_vars,
        "available_models": available_models,
        "genai_error": error_message,
        "genai_lib_version": genai.__version__
    }

@app.get("/debug/test-vertex")
async def test_vertex_generation():
    """Test Vertex AI generation directly"""
    results = {"steps": []}
    try:
        from core.vertex_wrapper import VertexWrapper
        results["steps"].append("1. VertexWrapper imported OK")
        
        wrapper = VertexWrapper()
        results["steps"].append(f"2. Wrapper created. project_id={wrapper.project_id}, has_creds={wrapper.credentials is not None}, model={wrapper.model_name}")
        
        if not wrapper.credentials:
            results["error"] = "No credentials loaded"
            return results
        
        results["steps"].append("3. Refreshing token...")
        from google.auth.transport.requests import Request as AuthReq
        if not wrapper.credentials.valid:
            wrapper.credentials.refresh(AuthReq())
        results["steps"].append(f"4. Token valid={wrapper.credentials.valid}")
        
        results["steps"].append("5. Calling generate_content...")
        response = wrapper.generate_content("Reply with exactly: VERTEX_OK")
        results["steps"].append(f"6. Response received: {str(response)[:200] if response else 'None'}")
        results["success"] = response is not None
        results["response_preview"] = str(response)[:500] if response else None
        
    except Exception as e:
        results["error"] = f"{type(e).__name__}: {str(e)}"
    
    return results

@app.get("/debug/test-generate")
async def test_generate_flow():
    """Test the exact post generation flow step by step"""
    steps = []
    try:
        steps.append("1. Starting generate_post flow...")
        steps.append(f"2. generator.vertex exists={generator.vertex is not None}")
        steps.append(f"3. generator.vertex.credentials={generator.vertex.credentials is not None if generator.vertex else 'N/A'}")
        steps.append(f"4. generator.vertex.project_id={generator.vertex.project_id if generator.vertex else 'N/A'}")
        steps.append(f"5. generator.vertex.model_name={generator.vertex.model_name if generator.vertex else 'N/A'}")
        steps.append(f"6. generator.gemini={generator.gemini is not None}")
        steps.append(f"7. RENDER env={os.getenv('RENDER')}")
        
        steps.append("8. Building prompt...")
        prompt = "Generate a short LinkedIn post about AI. Keep it under 200 words."
        
        steps.append("9. Calling _generate_gemini...")
        text = generator._generate_gemini(prompt)
        steps.append(f"10. Got response: {str(text)[:300]}")
        
        return {"success": True, "steps": steps, "preview": str(text)[:500]}
    except Exception as e:
        import traceback
        return {"success": False, "steps": steps, "error": f"{type(e).__name__}: {str(e)}", "traceback": traceback.format_exc()}

@app.get("/debug/test-imagen")
async def test_imagen():
    """Test Imagen 3 image generation on Render"""
    steps = []
    try:
        import json as jsonlib
        from google.oauth2 import service_account as sa
        from google.auth.transport.requests import Request as AuthReq
        import requests
        
        steps.append(f"1. MEDIA_ENABLED={MEDIA_ENABLED}")
        
        # Manually test Imagen API to capture exact error
        PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'linkedin-post-factory')
        LOCATION = 'us-central1'
        MODEL_NAME = 'imagen-3.0-generate-001'
        
        creds_b64 = os.getenv('GCP_CREDENTIALS_JSON_B64')
        if not creds_b64:
            return {"success": False, "steps": steps, "error": "No GCP_CREDENTIALS_JSON_B64"}
        
        creds_data = jsonlib.loads(base64.b64decode(creds_b64))
        steps.append(f"2. Project: {creds_data.get('project_id')}, SA: {creds_data.get('client_email')}")
        
        credentials = sa.Credentials.from_service_account_info(
            creds_data, scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        credentials.refresh(AuthReq())
        steps.append(f"3. Token obtained: {bool(credentials.token)}")
        
        url = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{creds_data.get('project_id')}/locations/{LOCATION}/publishers/google/models/{MODEL_NAME}:predict"
        steps.append(f"4. URL: {url}")
        
        data = {
            "instances": [{"prompt": "A simple blue gradient"}],
            "parameters": {"sampleCount": 1, "aspectRatio": "16:9"}
        }
        
        resp = requests.post(url, headers={
            'Authorization': f'Bearer {credentials.token}',
            'Content-Type': 'application/json'
        }, json=data, timeout=30)
        
        steps.append(f"5. Response status: {resp.status_code}")
        
        if resp.status_code == 200:
            result = resp.json()
            preds = result.get('predictions', [])
            if preds and preds[0].get('bytesBase64Encoded'):
                img_size = len(base64.b64decode(preds[0]['bytesBase64Encoded']))
                steps.append(f"6. SUCCESS! Image: {img_size} bytes")
                return {"success": True, "steps": steps, "image_bytes": img_size}
            else:
                steps.append(f"6. No predictions in response: {str(result)[:300]}")
        else:
            steps.append(f"6. ERROR: {resp.text[:500]}")
        
        return {"success": False, "steps": steps}
    except Exception as e:
        import traceback
        return {"success": False, "steps": steps, "error": f"{type(e).__name__}: {str(e)}", "traceback": traceback.format_exc()}

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# Initialize services
generator = None
try:
    generator = PostGenerator()
except Exception as exc:
    service_init_errors["generator"] = str(exc)
    print(f"Warning: Could not initialize post generator: {exc}")

checker = None
try:
    checker = VoiceChecker()
except Exception as exc:
    service_init_errors["checker"] = str(exc)
    print(f"Warning: Could not initialize voice checker: {exc}")

db = None
try:
    db = NeonDatabase()
except Exception as exc:
    service_init_errors["database"] = str(exc)
    print(f"Warning: Could not initialize database: {exc}")

tracker = None
if db is not None:
    try:
        tracker = ContentTracker(db_client=db)
    except Exception as exc:
        service_init_errors["tracker"] = str(exc)
        print(f"Warning: Could not initialize content tracker: {exc}")

news_service = None
try:
    news_service = NewsService()
except Exception as exc:
    service_init_errors["news_service"] = str(exc)
    print(f"Warning: Could not initialize news service: {exc}")

# Initialize storage service if available
storage_service = None
supabase_client = getattr(db, 'supabase', None) if db is not None else None
if MEDIA_ENABLED and StorageService and supabase_client is not None:
    try:
        storage_service = StorageService(supabase_client)
    except Exception as e:
        service_init_errors["storage_service"] = str(e)
        print(f"Warning: Could not initialize storage service: {e}")


def _load_seed_topics(channel: str) -> List[Dict[str, Any]]:
    cfg = generator.config or {}
    topics_cfg = cfg.get("channel_topics", {})
    return topics_cfg.get(channel, [])


def _ensure_topics_seeded(channel: str) -> None:
    existing = db.get_channel_topics(channel=channel, limit=8)
    if existing:
        return
    seeds = news_service.get_live_channel_topics(channel=channel, count=8)
    if not seeds:
        seeds = _load_seed_topics(channel)
    if seeds:
        db.replace_channel_topics(channel, seeds)

# ========================================
# REQUEST/RESPONSE MODELS
# ========================================

class GeneratePostRequest(BaseModel):
    channel: str = Field("personal_career", description="Content channel (personal_career, goalpraxis_company)")
    pillar: str = Field(..., description="Content pillar (asset_management, technology, etc.)")
    format_type: str = Field(..., description="Post format (insight, story, data, question, contrarian)")
    topic: Optional[str] = Field(None, description="Specific topic for the post")
    source_name: Optional[str] = Field(None, description="Source publisher name for grounding")
    source_title: Optional[str] = Field(None, description="Source article title for grounding")
    source_url: Optional[str] = Field(None, description="Source article URL for grounding")
    source_summary: Optional[str] = Field(None, description="Source summary/reasoning for grounding")
    key_findings: Optional[list] = Field(None, description="Extracted key findings with source attribution")
    article_text: Optional[str] = Field(None, description="Manually uploaded article text (overrides URL fetch)")
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
    status: Optional[str] = Field(None, description="Updated post status")

class PostResponse(BaseModel):
    id: Optional[str] = None  # Changed to str for UUID
    channel: Optional[str] = "personal_career"
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


class TopicSuggestion(BaseModel):
    rank: int
    topic_name: str
    reasoning: Optional[str] = None
    source: Optional[str] = None
    source_title: Optional[str] = None
    source_url: Optional[str] = None
    trend_score: Optional[float] = None
    strategic_score: Optional[float] = None
    recency_score: Optional[float] = None
    channel_fit_score: Optional[float] = None
    momentum_score: Optional[float] = None
    suggested_pillar: Optional[str] = None
    suggested_format: Optional[str] = None


class TopicsResponse(BaseModel):
    channel: str
    topics: List[TopicSuggestion]
    updated_at: str


def _serialize_created_at(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)

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

@app.post("/articles/extract")
async def extract_article(file: Optional[UploadFile] = File(None), text: Optional[str] = Form(None)):
    """
    Extract plain text from an uploaded article file (PDF, DOCX, TXT, HTML, MD)
    or from pasted text. Returns the cleaned text and auto-extracted stat findings.
    """
    raw_text = ""

    if text and text.strip():
        raw_text = text.strip()
    elif file and file.filename:
        content = await file.read()
        filename = (file.filename or "").lower()
        try:
            if filename.endswith(".pdf"):
                import pdfplumber
                with pdfplumber.open(io.BytesIO(content)) as pdf:
                    raw_text = "\n".join(
                        page.extract_text() or "" for page in pdf.pages
                    )
            elif filename.endswith(".docx"):
                from docx import Document as DocxDocument
                doc = DocxDocument(io.BytesIO(content))
                raw_text = "\n".join(para.text for para in doc.paragraphs)
            elif filename.endswith((".html", ".htm")):
                from html.parser import HTMLParser
                class _TextExtractor(HTMLParser):
                    def __init__(self):
                        super().__init__()
                        self._parts: list = []
                        self._skip = False
                    def handle_starttag(self, tag, attrs):
                        if tag in ("script", "style"):
                            self._skip = True
                    def handle_endtag(self, tag):
                        if tag in ("script", "style"):
                            self._skip = False
                    def handle_data(self, data):
                        if not self._skip:
                            self._parts.append(data)
                extractor = _TextExtractor()
                extractor.feed(content.decode("utf-8", errors="ignore"))
                raw_text = " ".join(extractor._parts)
            else:
                # TXT / MD or anything else — decode as UTF-8
                raw_text = content.decode("utf-8", errors="ignore")
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Could not extract text from file: {str(exc)}")
    else:
        raise HTTPException(status_code=400, detail="Provide either a file upload or pasted text.")

    raw_text = re.sub(r'\s{3,}', '\n\n', raw_text).strip()
    if len(raw_text) < 50:
        raise HTTPException(status_code=422, detail="Extracted text is too short to be useful (less than 50 characters).")

    findings = _extract_stat_sentences(raw_text[:8000], "uploaded article")
    return {
        "text": raw_text[:6000],
        "char_count": len(raw_text),
        "findings_count": len(findings),
        "findings": findings,
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
        if not generator or not checker or not db:
            raise HTTPException(
                status_code=503,
                detail={
                    "message": "Post generation is temporarily unavailable because core services did not initialize.",
                    "services": service_init_errors,
                },
            )

        # Strict grounding policy:
        # - We must have full article text (manual upload/paste OR successful URL fetch)
        # - We do NOT generate from summary-only or key-findings-only evidence
        key_findings = request.key_findings
        article_text = (request.article_text or "").strip()

        if not article_text:
            if not request.source_url or not str(request.source_url).startswith("http"):
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "No valid article URL was available for this topic. "
                        "Please open the article and paste it into 'Paste article text directly' "
                        "or upload the article file before generating."
                    )
                )

            key_findings, article_text, fetch_error = await fetch_findings_for_url(
                request.source_url, request.source_name or request.source_title or "source"
            )
            if not article_text:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        (fetch_error + " ") if fetch_error else ""
                    ) + (
                        "To keep source accuracy, generation is blocked without full article text. "
                        "Please paste the article into 'Paste article text directly' or upload it, then retry."
                    )
                )
        elif not key_findings:
            # Manual upload/paste path: derive findings from provided article text
            key_findings = _extract_stat_sentences(
                article_text[:8000],
                request.source_name or request.source_title or "uploaded article"
            )

        # Generate post
        post = generator.generate_post(
            pillar=request.pillar,
            format_type=request.format_type,
            topic=request.topic,
            channel=request.channel,
            language=request.language or "english",
            provider=request.provider,
            source_context={
                "source_name": request.source_name,
                "source_title": request.source_title,
                "source_url": request.source_url,
                "source_summary": request.source_summary,
                "key_findings": key_findings,
                "article_text": article_text,
            }
        )
        
        # Check voice
        score, issues = checker.check_post(post["text"])
        
        # Save to database
        post_id = str(uuid.uuid4())
        
        # Store hashtags as comma-separated text for DB portability.
        hashtags_list = post["hashtags"] if isinstance(post["hashtags"], list) else post["hashtags"].split()
        hashtags_str = ",".join(hashtags_list)
        
        db.save_post({
            "id": post_id,
            "channel": request.channel,
            "pillar": post["pillar"],
            "format": post["format"],
            "topic": post.get("topic", ""),
            "text": post["text"],
            "hashtags": hashtags_str,
            "voice_score": float(score),
            "length": int(len(post["text"])),
            "status": "draft"
        })
        db.touch_channel_last_post(request.channel)
        
        return PostResponse(
            id=post_id,
            channel=post.get("channel", request.channel),
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
    channel: Optional[str] = None,
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
        posts = db.get_posts(limit=limit, status=status, channel=channel)
        
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
                channel=post.get('channel', 'personal_career'),
                pillar=post.get('pillar'),
                format=post.get('format'),
                topic=post.get('topic'),
                text=post.get('text'),
                hashtags=hashtags,
                voice_score=post.get('voice_score'),
                length=post.get('length'),
                created_at=_serialize_created_at(post.get('created_at')),
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
            channel=post.get('channel', 'personal_career'),
            pillar=post.get('pillar'),
            format=post.get('format'),
            topic=post.get('topic'),
            text=post.get('text'),
            hashtags=hashtags,
            voice_score=post.get('voice_score'),
            length=post.get('length'),
            created_at=_serialize_created_at(post.get('created_at')),
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
        if request.status:
            update_data["status"] = request.status
        
        db.update_post(post_id, **update_data)
        
        hashtags = request.hashtags or post.get('hashtags', '').split(',')
        
        return PostResponse(
            id=post_id,
            channel=post.get('channel', 'personal_career'),
            pillar=post.get('pillar'),
            format=post.get('format'),
            topic=post.get('topic'),
            text=request.text,
            hashtags=hashtags,
            voice_score=score,
            length=len(request.text),
            created_at=_serialize_created_at(post.get('created_at')),
            status=request.status or post.get('status', 'draft')
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
    content_pillar: Optional[str] = None
    post_id: Optional[str] = None
    save_to_storage: bool = True

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
    """Generate PDF carousel - returns raw PDF bytes"""
    if not MEDIA_ENABLED:
        raise HTTPException(status_code=501, detail="Media generation not available")
    try:
        pdf_bytes = media_generator.generate_carousel_pdf(
            slides=request.slides,
            title=request.title,
            style=request.style
        )
        
        # Also upload to storage if configured
        if request.save_to_storage and storage_service and request.post_id:
            try:
                storage_service.upload_media(
                    pdf_bytes,
                    request.post_id,
                    "carousel",
                    "pdf"
                )
            except Exception as e:
                print(f"Storage upload failed: {e}")

        # Build filename with convention: IndepthCarousel_{Pillar}_{MonthDay}.pdf
        from datetime import datetime as dt
        now = dt.now()
        month_day = now.strftime("%b%d")  # e.g. Feb12
        
        # Extract pillar name from content_pillar field
        pillar = request.content_pillar or 'General'
        # Clean pillar: remove '&', spaces, special chars -> CamelCase
        pillar_clean = pillar.replace('&', '').replace(' ', '')
        # Map common pillar names
        pillar_map = {
            'AIInnovation': 'AIInnovation',
            'TechLeadership': 'TechLeadership',
            'CareerGrowth': 'CareerGrowth',
            'IndustryInsights': 'IndustryInsights',
            'PersonalBrand': 'PersonalBrand',
        }
        pillar_label = pillar_map.get(pillar_clean, pillar_clean)
        
        filename = f"IndepthCarousel_{pillar_label}_{month_day}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
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


@app.get("/topics/trending", response_model=TopicsResponse)
async def get_trending_topics(channel: str = "personal_career", refresh: bool = False):
    """
    Get top topic suggestions for a channel.

    - **channel**: personal_career | goalpraxis_company | other
    - **refresh**: when true, fetch live topics from current web/news signals and store in Neon
    """
    try:
        if refresh:
            seeds = news_service.get_live_channel_topics(channel=channel, count=8)
            if not seeds:
                seeds = _load_seed_topics(channel)
            if not seeds:
                raise HTTPException(status_code=404, detail=f"No topic seeds found for channel '{channel}'")
            db.replace_channel_topics(channel, seeds)
        else:
            _ensure_topics_seeded(channel)

        topics = db.get_channel_topics(channel=channel, limit=8)
        return TopicsResponse(
            channel=channel,
            topics=[
                TopicSuggestion(
                    rank=int(item.get("rank", idx + 1)),
                    topic_name=item.get("topic_name", ""),
                    reasoning=item.get("reasoning"),
                    source=item.get("source"),
                    source_title=item.get("source_title"),
                    source_url=item.get("source_url"),
                    trend_score=float(item.get("trend_score")) if item.get("trend_score") is not None else None,
                    strategic_score=float(item.get("strategic_score")) if item.get("strategic_score") is not None else None,
                    recency_score=float(item.get("recency_score")) if item.get("recency_score") is not None else None,
                    channel_fit_score=float(item.get("channel_fit_score")) if item.get("channel_fit_score") is not None else None,
                    momentum_score=float(item.get("momentum_score")) if item.get("momentum_score") is not None else None,
                    suggested_pillar=item.get("suggested_pillar"),
                    suggested_format=item.get("suggested_format"),
                )
                for idx, item in enumerate(topics)
            ],
            updated_at=datetime.now().isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch channel topics: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
