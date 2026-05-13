# LinkedIn Post Factory API

FastAPI backend for AI-powered LinkedIn content generation with voice consistency.

## Quick Start

### 1. Start the API server

```bash
# Windows
start_api.bat

# Or manually
python -m uvicorn api.main:app --reload --port 8000
```

The API will be available at:
- **Main API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 2. Test the API

```bash
# In another terminal
python test_api.py
```

## API Endpoints

### Core Generation

#### `POST /posts/generate`
Generate a single LinkedIn post

**Request:**
```json
{
  "pillar": "technology",
  "format_type": "insight",
  "topic": "AI in predictive maintenance",
  "provider": "claude"
}
```

**Response:**
```json
{
  "id": 1,
  "pillar": "technology",
  "format": "insight",
  "topic": "AI in predictive maintenance",
  "text": "Last week I ran the numbers on our new AI system...",
  "hashtags": ["#PredictiveMaintenance", "#AI", "#Mining"],
  "voice_score": 87.5,
  "length": 1243,
  "created_at": "2026-01-12T10:30:00",
  "status": "draft"
}
```

#### `POST /posts/batch`
Generate multiple posts

**Request:**
```json
{
  "count": 10,
  "pillar_distribution": {
    "asset_management": 0.25,
    "technology": 0.30,
    "consulting": 0.10,
    "entrepreneurship": 0.25,
    "thought_leadership": 0.10
  }
}
```

**Response:**
```json
{
  "generated": 10,
  "posts": [
    {
      "id": 1,
      "pillar": "technology",
      "format": "insight",
      "voice_score": 87.5,
      "length": 1243,
      "status": "draft"
    }
  ]
}
```

### Voice & Quality

#### `POST /posts/check-voice`
Check voice authenticity of text

**Request:**
```json
{
  "text": "Last week I ran the numbers on AI reliability..."
}
```

**Response:**
```json
{
  "score": 87.5,
  "grade": "B",
  "issues": ["✓ No forbidden phrases", "⚠️ Could use more data"],
  "components": {
    "hook": true,
    "data": false,
    "cta": true,
    "forbidden": true
  },
  "length": 1243,
  "length_status": "optimal",
  "recommendation": "Good post with minor tweaks needed"
}
```

### Post Management

#### `GET /posts`
List all posts with optional filters

**Query params:**
- `limit`: Max posts to return (default: 20)
- `status`: Filter by status (draft, scheduled, published)
- `pillar`: Filter by content pillar
- `min_score`: Minimum voice score

**Example:**
```
GET /posts?limit=5&status=draft&min_score=85
```

#### `GET /posts/{post_id}`
Get specific post by ID

#### `PUT /posts/{post_id}`
Update post text and hashtags

**Request:**
```json
{
  "text": "Updated post text...",
  "hashtags": ["#NewTag1", "#NewTag2"]
}
```

#### `DELETE /posts/{post_id}`
Delete post by ID

### Analytics & Recommendations

#### `GET /dashboard`
Get content health dashboard

**Response:**
```json
{
  "overall_health": 82.5,
  "health_grade": "B",
  "summary": {
    "total_posts_30d": 15,
    "posts_per_week": 3.5,
    "consistency": "Good",
    "balance_status": "Good"
  },
  "pillar_balance": {
    "total_posts": 15,
    "balance": {
      "asset_management": {
        "current": 26.7,
        "target": 25.0,
        "diff": 1.7,
        "status": "✓"
      }
    },
    "recommendations": ["✓ Content pillars are well balanced"]
  },
  "posting_cadence": {
    "posts_per_week": 3.5,
    "consistency": "Good",
    "recommendations": ["✓ Good posting frequency"]
  },
  "next_recommended_pillar": "entrepreneurship"
}
```

#### `GET /recommendations/next-pillar`
Get recommended pillar for next post

**Response:**
```json
{
  "recommended_pillar": "entrepreneurship",
  "timestamp": "2026-01-12T10:30:00"
}
```

#### `GET /stats`
Get overall statistics

**Response:**
```json
{
  "total_posts": 42,
  "published": 28,
  "drafts": 14,
  "avg_voice_score": 86.3,
  "health": {
    "score": 82.5,
    "grade": "B"
  },
  "posting": {
    "posts_per_week": 3.5,
    "consistency": "Good"
  }
}
```

## Configuration

### Content Pillars
Edit `config.json` to customize:
- Voice guidelines (forbidden phrases, required language, tone)
- Content pillars (topics, percentages)

### AI Providers
Configured in `core/post_generator.py`:
- **Claude**: Anthropic API (primary)
- **GPT-4**: OpenAI API
- **Gemini**: Google AI API

## Voice Scoring

Posts are scored 0-100 based on:
- **Forbidden phrases** (-15 each): "I quit my job", "expert", "guru", etc.
- **Authenticity markers**:
  - ✓ Specific numbers (%, $, years)
  - ✓ Operator language ("ran numbers", "board demanded")
  - ✓ Real examples ("at Southern Copper")
  - ✗ Marketing speak ("excited to announce", "game-changer")
  - ✗ Vague claims ("world-class", "best-in-class")
- **Length**: Optimal 1,200-1,500 chars
- **Structure**: 3-5 paragraphs, short hook

**Grades:**
- **A (90+)**: Ready to publish
- **B (80-89)**: Minor tweaks needed
- **C (70-79)**: Needs revision
- **D/F (<70)**: Regenerate

## Development

### Project Structure
```
Post_Factory/
├── api/
│   └── main.py          # FastAPI application
├── core/
│   ├── post_generator.py  # AI post generation
│   ├── voice_checker.py   # Authenticity validation
│   ├── content_tracker.py # Pillar balance tracking
│   └── database.py        # SQLite storage
├── data/
│   └── posts.db          # SQLite database
├── config.json           # Voice & pillar config
├── start_api.bat         # API startup script
└── test_api.py           # API test suite
```

### Adding Custom Endpoints

```python
from api.main import app

@app.get("/custom-endpoint")
async def custom_endpoint():
    return {"message": "Custom response"}
```

### Error Handling

All endpoints return standard HTTP status codes:
- `200`: Success
- `404`: Not found
- `500`: Server error

Error response format:
```json
{
  "detail": "Error message"
}
```

## Next Steps

1. **Frontend**: Build React/Vue frontend that consumes this API
2. **Authentication**: Add user auth for multi-user support
3. **Scheduling**: Integrate with LinkedIn API for auto-posting
4. **Image Generation**: Add DALL-E integration for visuals
5. **Analytics**: Enhanced tracking and reporting

## Testing

Interactive API docs at http://localhost:8000/docs allow you to:
- Test all endpoints directly in browser
- See request/response schemas
- Generate example payloads
- View API documentation

---

**Built with:** FastAPI, SQLite, Claude, GPT-4, Gemini
