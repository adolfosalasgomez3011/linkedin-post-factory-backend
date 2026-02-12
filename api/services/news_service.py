"""
News and Trending Topics Service
Fetches trending news articles for LinkedIn post generation
"""
import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import google.generativeai as genai

class NewsService:
    """Fetch trending news and topics for LinkedIn posts"""
    
    def __init__(self):
        google_key = os.getenv("GOOGLE_API_KEY")
        if google_key:
            genai.configure(api_key=google_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
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
            
            response = self.model.generate_content(prompt)
            
            # Parse the response and structure it
            # For now, return structured data based on the AI response
            articles = self._parse_ai_articles(response.text, category, count)
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
