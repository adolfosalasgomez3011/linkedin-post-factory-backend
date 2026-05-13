"""
News and Trending Topics Service
Fetches trending news articles and live channel topics for LinkedIn post generation.
"""
import json
import os
import re
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from urllib.parse import quote_plus
from xml.etree import ElementTree as ET

import google.generativeai as genai
import requests
try:
    from core.vertex_wrapper import VertexWrapper
except ImportError:
    VertexWrapper = None

class NewsService:
    """Fetch trending news and topics for LinkedIn posts"""

    CHANNEL_QUERY_MAP = {
        "personal_career": [
            "latin america mining operations leadership",
            "coo mining decision making latin america",
            "peru mining operational transformation strategy",
            "hatch advisory principal mining transformation latam",
            "asset management reliability mining leadership",
            "mining fleet visibility operational control",
            "copper price trend americas mining market",
            "lithium market trend south america mining",
            "north america mining productivity maintenance strategy",
            "south africa australia mining operations trend",
        ],
        "goalpraxis_company": [
            "minepulse asset visibility mining operations",
            "mining fleet utilization shift productivity",
            "mine geofence safety alerts operational control",
            "LoRaWAN mining IoT asset tracking copper mine",
            "predictive maintenance mining equipment uptime",
            "copper market movement mine productivity costs",
        ],
        "other": [
            "industrial AI operations americas",
            "digital transformation heavy industry market trends",
            "operations technology adoption",
            "industrial data strategy",
            "asset performance management",
        ],
    }

    CHANNEL_DEFAULTS = {
        "personal_career": {
            "pillar": "COO Readiness & Decision Systems",
            "format": "Insight",
        },
        "goalpraxis_company": {
            "pillar": "Asset Tracking Business Case",
            "format": "Insight",
        },
        "other": {
            "pillar": "Technology Signals",
            "format": "Insight",
        },
    }

    CHANNEL_STRATEGIC_KEYWORDS = {
        "personal_career": {
            "coo": 1.0,
            "general manager": 1.0,
            "advisory principal": 0.9,
            "hatch": 0.9,
            "ferreyros": 0.9,
            "chinalco": 0.8,
            "southern copper": 0.8,
            "operations": 0.9,
            "leadership": 0.9,
            "asset management": 1.0,
            "maintenance": 0.8,
            "reliability": 0.8,
            "latam": 0.8,
            "market": 0.8,
            "price": 0.8,
            "trend": 0.7,
            "copper": 0.8,
            "lithium": 0.8,
            "contract renewal": 0.8,
            "business transformation": 0.8,
            "mining": 0.7,
        },
        "goalpraxis_company": {
            "asset tracking": 1.0,
            "fleet": 1.0,
            "visibility": 0.9,
            "lorawan": 1.0,
            "iot": 1.0,
            "dispatch": 0.8,
            "downtime": 0.9,
            "predictive maintenance": 0.9,
            "utilization": 0.9,
            "productivity": 0.9,
            "roi": 1.0,
            "mining": 0.7,
        },
        "other": {
            "industrial ai": 0.9,
            "digital transformation": 0.9,
            "operations": 0.8,
            "technology": 0.7,
            "data": 0.8,
            "automation": 0.8,
            "strategy": 0.8,
        },
    }

    MOMENTUM_TERMS = [
        "new",
        "launch",
        "announces",
        "record",
        "growth",
        "breakthrough",
        "investment",
        "adoption",
        "deploy",
        "expands",
        "partnership",
    ]

    LATAM_TERMS = ["latin america", "latam", "chile", "peru", "argentina", "mexico", "brazil", "south america", "andes"]
    NORTH_AMERICA_TERMS = ["canada", "usa", "united states", "north america", "americas"]
    SOUTH_AFRICA_AUSTRALIA_TERMS = ["south africa", "australia", "queensland", "western australia"]
    
    def __init__(self):
        # Initialize Vertex AI (Enterprise)
        if VertexWrapper:
            self.vertex = VertexWrapper()
        else:
            self.vertex = None

        # Initialize Standard Gemini (Consumer)
        google_key = os.getenv("GOOGLE_API_KEY")
        if google_key:
            try:
                # Force REST transport to avoid gRPC geo-blocking issues on cloud servers
                genai.configure(api_key=google_key, transport='rest')
                self.model = genai.GenerativeModel('gemini-2.0-flash')
            except Exception as e:
                print(f"Warning: Gemini standard init failed: {e}")
                self.model = None
        else:
            self.model = None
    
    def get_trending_articles(
        self,
        category: str = "technology",
        count: int = 10
    ) -> List[Dict]:
        """
        Get trending articles for a category using AI to generate realistic trending topics
        
        Args:
            category: Content category (technology, ai, business, leadership, etc.)
            count: Number of articles to return
            
        Returns:
            List of article dictionaries with title, summary, url, source
        """
        if not self.model:
            return self._get_fallback_articles(category, count)
        
        try:
            # Get current month and year
            current_date = datetime.now().strftime("%B %Y")
            
            # Use Gemini to generate current trending topics
            prompt = f"""Generate {count} realistic trending news headlines and summaries for {category} 
            that would be relevant for LinkedIn content creators in {current_date}.
            
            For each article provide:
            - title: catchy headline
            - summary: 2-3 sentence summary
            - source: realistic news source name
            - topic: main topic tag
            
            Format as JSON array. Make them relevant, timely, and professional.
            Focus on AI, innovation, business, technology, and leadership topics.
            """
            
            text_response = None
            
            # 1. Try Standard Gemini
            try:
                if self.model:
                    response = self.model.generate_content(prompt)
                    text_response = response.text
            except Exception as e:
                print(f"Standard Gemini News failed: {e}")
            
            # 2. Try Vertex AI Fallback
            if not text_response and self.vertex and self.vertex.credentials:
                print("Using Vertex AI for News...")
                text_response = self.vertex.generate_content(prompt)
            
            if not text_response:
                raise Exception("All AI providers failed to generate news")

            # Parse the response and structure it
            # For now, return structured data based on the AI response
            articles = self._parse_ai_articles(text_response, category, count)
            return articles
            
        except Exception as e:
            print(f"Error fetching trending articles: {e}")
            articles = self._get_fallback_articles(category, count)
            # Inject error info into the first article title for visibility in frontend
            articles[0]["title"] = f"ERROR: {str(e)[:100]}"
            articles[0]["summary"] = "The AI generation failed. This is the fallback content."
            return articles
    
    def _parse_ai_articles(self, ai_response: str, category: str, count: int) -> List[Dict]:
        """Parse AI-generated articles into structured format"""
        import json
        import re
        
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\[.*\]', ai_response, re.DOTALL)
            if json_match:
                articles = json.loads(json_match.group(0))
                return articles[:count]
        except:
            pass
        
        # Fallback to parsing text format
        return self._get_fallback_articles(category, count)
    
    def _get_fallback_articles(self, category: str, count: int) -> List[Dict]:
        """Fallback articles when API is unavailable"""
        
        fallback_articles = {
            "technology": [
                {
                    "id": "tech1",
                    "title": "AI Models Achieve 99% Accuracy in Medical Diagnosis",
                    "summary": "New research shows AI systems can now diagnose diseases with unprecedented accuracy, potentially transforming healthcare delivery worldwide.",
                    "source": "Tech Innovation Weekly",
                    "topic": "AI in Healthcare",
                    "url": "#"
                },
                {
                    "id": "tech2",
                    "title": "Quantum Computing Breakthrough: 1000-Qubit Processor Unveiled",
                    "summary": "Scientists announce a major milestone in quantum computing with a processor capable of solving complex problems in minutes.",
                    "source": "Science Daily",
                    "topic": "Quantum Computing",
                    "url": "#"
                },
                {
                    "id": "tech3",
                    "title": "Sustainable Data Centers: Tech Giants Commit to 100% Renewable Energy",
                    "summary": "Major technology companies pledge to power all data centers with renewable energy by 2027, reducing carbon emissions significantly.",
                    "source": "Green Tech News",
                    "topic": "Sustainability",
                    "url": "#"
                }
            ],
            "ai": [
                {
                    "id": "ai1",
                    "title": "GPT-5 Launch: New Capabilities Exceed Expectations",
                    "summary": "OpenAI's latest model demonstrates reasoning abilities that approach human-level performance across multiple domains.",
                    "source": "AI Insider",
                    "topic": "Large Language Models",
                    "url": "#"
                },
                {
                    "id": "ai2",
                    "title": "AI Regulations: European Union Passes Comprehensive AI Act",
                    "summary": "New legislation sets global standards for AI safety, transparency, and ethical use in commercial applications.",
                    "source": "Policy Review",
                    "topic": "AI Regulation",
                    "url": "#"
                },
                {
                    "id": "ai3",
                    "title": "Autonomous Vehicles: First Fully Self-Driving Fleet Launches",
                    "summary": "Major automotive company deploys 1000 autonomous vehicles in three cities, marking a turning point in transportation.",
                    "source": "Auto Tech Today",
                    "topic": "Autonomous Vehicles",
                    "url": "#"
                }
            ],
            "business": [
                {
                    "id": "biz1",
                    "title": "Remote Work Revolution: 70% of Companies Adopt Hybrid Model",
                    "summary": "New survey reveals permanent shift in workplace culture as employees demand flexibility and companies see productivity gains.",
                    "source": "Business Insights",
                    "topic": "Future of Work",
                    "url": "#"
                },
                {
                    "id": "biz2",
                    "title": "Startup Funding Rebounds: Tech Investments Hit Record Highs",
                    "summary": "Venture capital returns to pre-2022 levels as AI and climate tech startups attract major investments.",
                    "source": "Venture Beat",
                    "topic": "Startup Funding",
                    "url": "#"
                },
                {
                    "id": "biz3",
                    "title": "Leadership Crisis: Study Shows 60% of Managers Unprepared for AI Era",
                    "summary": "Research highlights urgent need for leadership development as AI transforms management roles.",
                    "source": "Harvard Business Review",
                    "topic": "Leadership",
                    "url": "#"
                }
            ]
        }
        
        # Get articles for category or default to technology
        articles = fallback_articles.get(category.lower(), fallback_articles["technology"])
        
        # Return requested count
        return articles[:count]

    def get_live_channel_topics(self, channel: str, count: int = 8) -> List[Dict]:
        """Get live hottest topics for a channel using current news/web signals."""
        articles = self._get_live_articles_for_channel(channel, per_query=6)
        if not articles:
            return self._fallback_live_topics(channel, count)

        ranked_topics = self._rank_topics_from_articles(channel, articles, count)
        return ranked_topics[:count]

    def _get_live_articles_for_channel(self, channel: str, per_query: int = 6) -> List[Dict]:
        queries = self.CHANNEL_QUERY_MAP.get(channel, self.CHANNEL_QUERY_MAP["other"])
        articles: List[Dict] = []
        seen_links = set()

        for query in queries:
            for article in self._fetch_google_news_rss(query, limit=per_query):
                link = article.get("url")
                if not link or link in seen_links:
                    continue
                seen_links.add(link)
                articles.append(article)

        return articles

    def _fetch_google_news_rss(self, query: str, limit: int = 6) -> List[Dict]:
        rss_url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
        try:
            response = requests.get(rss_url, timeout=15)
            response.raise_for_status()
            root = ET.fromstring(response.text)
            items = root.findall(".//item")
            results = []
            for item in items[:limit]:
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                pub_date = (item.findtext("pubDate") or "").strip()
                source = "Google News"

                if " - " in title:
                    title_parts = title.rsplit(" - ", 1)
                    if len(title_parts) == 2:
                        title, source = title_parts[0].strip(), title_parts[1].strip()

                results.append(
                    {
                        "title": title,
                        "url": link,
                        "source": source,
                        "published_at": pub_date,
                        "query": query,
                    }
                )
            return results
        except Exception as e:
            print(f"Warning: RSS fetch failed for query '{query}': {e}")
            return []

    def _rank_topics_from_articles(self, channel: str, articles: List[Dict], count: int) -> List[Dict]:
        scored = self._score_articles(channel, articles)
        scored_sorted = sorted(scored, key=lambda x: x.get("trend_score", 0), reverse=True)

        if self.model or (self.vertex and self.vertex.credentials):
            ai_ranked = self._rank_topics_with_ai(channel, scored_sorted, count)
            if ai_ranked:
                return ai_ranked

        return self._fallback_rank_from_articles(channel, scored_sorted, count)

    def _score_articles(self, channel: str, articles: List[Dict]) -> List[Dict]:
        scored_articles: List[Dict] = []
        keywords = self.CHANNEL_STRATEGIC_KEYWORDS.get(channel, self.CHANNEL_STRATEGIC_KEYWORDS["other"])

        for article in articles:
            title = (article.get("title") or "").strip()
            normalized = title.lower()

            recency_score = self._compute_recency_score(article.get("published_at"))
            momentum_score = self._compute_momentum_score(normalized)
            channel_fit_score = self._compute_channel_fit_score(normalized, channel)
            strategic_score = self._compute_strategic_score(normalized, keywords)
            regional_priority_score = self._compute_regional_priority_score(normalized)
            personal_profile_score = self._compute_personal_profile_score(normalized, channel)

            # LinkedIn-style topic score: recency + momentum + channel fit + strategic relevance.
            trend_score = round(
                recency_score * 0.2
                + momentum_score * 0.16
                + channel_fit_score * 0.2
                + strategic_score * 0.2
                + regional_priority_score * 0.16
                + (personal_profile_score * 0.08 if channel == "personal_career" else 0),
                1,
            )

            scored_articles.append(
                {
                    **article,
                    "recency_score": recency_score,
                    "momentum_score": momentum_score,
                    "channel_fit_score": channel_fit_score,
                    "strategic_score": strategic_score,
                    "regional_priority_score": regional_priority_score,
                    "personal_profile_score": personal_profile_score,
                    "trend_score": trend_score,
                }
            )

        return scored_articles

    def _compute_recency_score(self, published_at: Optional[str]) -> float:
        if not published_at:
            return 50.0
        try:
            pub = datetime.strptime(published_at, "%a, %d %b %Y %H:%M:%S %Z")
            delta_hours = max((datetime.utcnow() - pub).total_seconds() / 3600.0, 0)
            if delta_hours <= 24:
                return 100.0
            if delta_hours <= 72:
                return 90.0
            if delta_hours <= 168:
                return 75.0
            if delta_hours <= 336:
                return 60.0
            return 45.0
        except Exception:
            return 50.0

    def _compute_momentum_score(self, normalized_title: str) -> float:
        hits = sum(1 for term in self.MOMENTUM_TERMS if term in normalized_title)
        return min(40.0 + hits * 12.0, 100.0)

    def _compute_channel_fit_score(self, normalized_title: str, channel: str) -> float:
        fit_terms = self.CHANNEL_QUERY_MAP.get(channel, [])
        hits = 0
        for query in fit_terms:
            query_tokens = [t for t in query.lower().split() if len(t) > 3]
            if any(token in normalized_title for token in query_tokens):
                hits += 1
        return min(40.0 + hits * 12.0, 100.0)

    def _compute_strategic_score(self, normalized_title: str, weighted_keywords: Dict[str, float]) -> float:
        score = 35.0
        for key, weight in weighted_keywords.items():
            if key in normalized_title:
                score += 18.0 * weight
        return min(score, 100.0)

    def _compute_regional_priority_score(self, normalized_title: str) -> float:
        latam_hits = sum(1 for term in self.LATAM_TERMS if term in normalized_title)
        north_america_hits = sum(1 for term in self.NORTH_AMERICA_TERMS if term in normalized_title)
        south_africa_aus_hits = sum(1 for term in self.SOUTH_AFRICA_AUSTRALIA_TERMS if term in normalized_title)

        if latam_hits > 0:
            score = 95.0
        elif north_america_hits > 0:
            score = 82.0
        elif south_africa_aus_hits > 0:
            score = 68.0
        else:
            score = 54.0

        return max(0.0, min(score, 100.0))

    def _compute_personal_profile_score(self, normalized_title: str, channel: str) -> float:
        if channel != "personal_career":
            return 50.0

        profile_terms = [
            "general manager",
            "coo",
            "advisory principal",
            "hatch",
            "ferreyros",
            "chinalco",
            "southern copper",
            "asset management",
            "maintenance",
            "reliability",
            "contract renewal",
            "business transformation",
        ]
        hits = sum(1 for term in profile_terms if term in normalized_title)
        return max(40.0, min(100.0, 45.0 + hits * 11.0))

    def _rank_topics_with_ai(self, channel: str, articles: List[Dict], count: int) -> List[Dict]:
        default = self.CHANNEL_DEFAULTS.get(channel, self.CHANNEL_DEFAULTS["other"])
        article_lines = []
        for idx, article in enumerate(articles[:20], start=1):
            article_lines.append(
                f"{idx}. {article.get('title')} | source={article.get('source')} | date={article.get('published_at')} | query={article.get('query')} | trend_score={article.get('trend_score')}"
            )

        prompt = f"""You are ranking live web topics for LinkedIn content.
Channel: {channel}
Date: {datetime.now().strftime('%Y-%m-%d')}

Based only on these current headlines, produce the {count} hottest LinkedIn-worthy topics for this channel.
Return valid JSON array only.

Each object must have:
- rank
- topic_name
- reasoning
- source
- source_title
- source_url
- trend_score
- strategic_score
- recency_score
- channel_fit_score
- momentum_score
- suggested_pillar
- suggested_format

Requirements:
- topics must be derived from the live headlines
- topics must feel current, social, and discussion-worthy
- no generic filler
- no duplicate angles

Articles:
{chr(10).join(article_lines)}

If the channel is personal_career, optimize for GM/COO/asset-management executive relevance.
If the channel is goalpraxis_company, optimize for mining asset tracking, visibility, IoT, fleet control, maintenance execution, and ROI.
If unsure, default pillar to {default['pillar']} and format to {default['format']}.
"""

        text_response = None
        try:
            if self.model:
                response = self.model.generate_content(prompt)
                text_response = response.text
        except Exception as e:
            print(f"AI topic ranking failed in Gemini: {e}")

        if not text_response and self.vertex and self.vertex.credentials:
            try:
                text_response = self.vertex.generate_content(prompt)
            except Exception as e:
                print(f"AI topic ranking failed in Vertex: {e}")

        if not text_response:
            return []

        try:
            match = re.search(r"\[.*\]", text_response, re.DOTALL)
            payload = json.loads(match.group(0) if match else text_response)
            source_index = { (a.get("title") or "").lower(): a for a in articles }
            ranked_topics = []
            for idx, item in enumerate(payload[:count], start=1):
                source_title = (item.get("source_title") or item.get("topic_name") or "").strip()
                matched = source_index.get(source_title.lower())
                matched_url = (matched or {}).get("url")
                raw_url = item.get("source_url") or matched_url
                source_url = raw_url if isinstance(raw_url, str) and raw_url.startswith("http") else matched_url

                strategic_score = self._normalize_ai_score(item.get("strategic_score"), (matched or {}).get("strategic_score"))
                recency_score = self._normalize_ai_score(item.get("recency_score"), (matched or {}).get("recency_score"))
                channel_fit_score = self._normalize_ai_score(item.get("channel_fit_score"), (matched or {}).get("channel_fit_score"))
                momentum_score = self._normalize_ai_score(item.get("momentum_score"), (matched or {}).get("momentum_score"))

                trend_score_raw = item.get("trend_score")
                if trend_score_raw is None:
                    trend_score = round(
                        recency_score * 0.25
                        + momentum_score * 0.20
                        + channel_fit_score * 0.25
                        + strategic_score * 0.30,
                        1,
                    )
                else:
                    trend_score = self._normalize_ai_score(trend_score_raw, (matched or {}).get("trend_score"))

                ranked_topics.append(
                    {
                        "rank": int(item.get("rank", idx)),
                        "topic_name": item.get("topic_name", "").strip(),
                        "reasoning": item.get("reasoning", ""),
                        "source": item.get("source") or (matched or {}).get("source"),
                        "source_title": source_title,
                        "source_url": source_url,
                        "trend_score": trend_score,
                        "strategic_score": strategic_score,
                        "recency_score": recency_score,
                        "channel_fit_score": channel_fit_score,
                        "momentum_score": momentum_score,
                        "suggested_pillar": item.get("suggested_pillar") or default["pillar"],
                        "suggested_format": item.get("suggested_format") or default["format"],
                    }
                )
            return ranked_topics
        except Exception as e:
            print(f"AI topic parsing failed: {e}")
            return []

    def _normalize_ai_score(self, value: Optional[float], fallback: Optional[float]) -> float:
        candidate = value if value is not None else fallback
        if candidate is None:
            return 50.0
        try:
            numeric = float(candidate)
        except Exception:
            return 50.0

        if numeric <= 10.0:
            numeric *= 10.0
        return max(0.0, min(100.0, round(numeric, 1)))

    def _fallback_rank_from_articles(self, channel: str, articles: List[Dict], count: int) -> List[Dict]:
        default = self.CHANNEL_DEFAULTS.get(channel, self.CHANNEL_DEFAULTS["other"])
        ranked_topics: List[Dict] = []
        seen_titles = set()

        for idx, article in enumerate(articles, start=1):
            title = (article.get("title") or "").strip()
            if not title or title.lower() in seen_titles:
                continue
            seen_titles.add(title.lower())

            ranked_topics.append(
                {
                    "rank": len(ranked_topics) + 1,
                    "topic_name": title,
                    "reasoning": f"Quick summary: {article.get('source', 'Current source')} reports this live signal from query '{article.get('query', '')}', prioritized for channel relevance and Americas market context.",
                    "source": article.get("source"),
                    "source_title": title,
                    "source_url": article.get("url"),
                    "trend_score": float(article.get("trend_score", 0)),
                    "strategic_score": float(article.get("strategic_score", 0)),
                    "recency_score": float(article.get("recency_score", 0)),
                    "channel_fit_score": float(article.get("channel_fit_score", 0)),
                    "momentum_score": float(article.get("momentum_score", 0)),
                    "suggested_pillar": default["pillar"],
                    "suggested_format": default["format"],
                }
            )
            if len(ranked_topics) >= count:
                break

        if len(ranked_topics) < count:
            ranked_topics.extend(self._fallback_live_topics(channel, count - len(ranked_topics), start_rank=len(ranked_topics) + 1))

        return ranked_topics[:count]

    def _fallback_live_topics(self, channel: str, count: int, start_rank: int = 1) -> List[Dict]:
        defaults = self.CHANNEL_DEFAULTS.get(channel, self.CHANNEL_DEFAULTS["other"])
        topic_names = {
            "personal_career": [
                "Operating model changes shaping mining leadership conversations this week",
                "What current mine-maintenance headlines say about decision quality",
                "Why asset performance is back in executive discussions",
                "What live industry signals say about COO readiness in mining",
            ],
            "goalpraxis_company": [
                "Live market signals around mining asset visibility and control",
                "Why current mining headlines are increasing interest in field asset tracking",
                "How today’s mining tech stories are reframing fleet visibility ROI",
                "What current mining IoT coverage says about deployment timing",
            ],
            "other": [
                "Current industrial AI headlines worth turning into LinkedIn discussion",
                "What the latest heavy-industry digital stories reveal about adoption",
                "Why today’s operational technology coverage matters to leaders",
                "Live signals shaping industrial transformation conversations",
            ],
        }.get(channel, [])

        results = []
        for idx, name in enumerate(topic_names[:count], start=start_rank):
            results.append(
                {
                    "rank": idx,
                    "topic_name": name,
                    "reasoning": "Fallback topic derived from current channel themes when live ranking cannot complete.",
                    "source": "Fallback",
                    "source_title": name,
                    "source_url": None,
                    "trend_score": 50.0,
                    "strategic_score": 50.0,
                    "recency_score": 50.0,
                    "channel_fit_score": 50.0,
                    "momentum_score": 50.0,
                    "suggested_pillar": defaults["pillar"],
                    "suggested_format": defaults["format"],
                }
            )
        return results
