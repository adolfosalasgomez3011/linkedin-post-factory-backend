"""
LinkedIn Post Generator - Core Engine
Generates posts using multiple AI providers with voice consistency checks
"""
import os
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import anthropic
import openai
from google import generativeai as genai

class PostGenerator:
    def __init__(self, config_path="config.json"):
        self.config_path = Path(__file__).parent.parent / config_path
        self.config = self._load_config()
        self._init_ai_clients()
        
    def _load_config(self) -> Dict:
        """Load configuration from config.json"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _init_ai_clients(self):
        """Initialize AI provider clients"""
        # Gemini (Google) - Primary provider (2.5 Pro - latest)
        google_key = os.getenv("GOOGLE_API_KEY")
        if google_key:
            genai.configure(api_key=google_key)
            self.gemini = genai.GenerativeModel('gemini-2.5-pro')
        else:
            self.gemini = None
        
        # GPT-4o (OpenAI) - Secondary provider
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            openai.api_key = openai_key
            self.openai_client = openai.OpenAI()
        else:
            self.openai_client = None
        
        # Claude - Optional
        claude_key = os.getenv("ANTHROPIC_API_KEY")
        if claude_key:
            self.claude = anthropic.Anthropic(api_key=claude_key)
        else:
            self.claude = None
    
    def generate_post(self, 
                     pillar: str,
                     format_type: str = "insight",
                     topic: Optional[str] = None,
                     language: str = "english",
                     provider: str = "gemini") -> Dict:
        """
        Generate a LinkedIn post
        
        Args:
            pillar: Content pillar (asset_management, technology, consulting, entrepreneurship, thought_leadership)
            format_type: Post format (insight, story, data, question, contrarian)
            topic: Optional specific topic
            language: Language (english, spanish, both)
            provider: AI provider (claude, gpt4, gemini)
            
        Returns:
            Dict with post text, metadata, and voice score
        """
        # Build prompt
        prompt = self._build_prompt(pillar, format_type, topic, language)
        
        # Generate with selected provider
        if provider == "gemini":
            text = self._generate_gemini(prompt)
        elif provider == "gpt4":
            text = self._generate_gpt4(prompt)
        elif provider == "claude":
            if self.claude is None:
                raise ValueError("Claude API not configured. Use 'gemini' or 'gpt4' instead.")
            text = self._generate_claude(prompt)
        else:
            raise ValueError(f"Unknown provider: {provider}. Use 'gemini' or 'gpt4'.")
        
        # Extract components
        post_data = self._parse_response(text)
        
        # Add metadata
        post_data.update({
            "pillar": pillar,
            "format": format_type,
            "topic": topic or "general",
            "provider": provider,
            "generated_at": datetime.now().isoformat(),
            "length": len(post_data["text"])
        })
        
        return post_data
    
    def _build_prompt(self, pillar: str, format_type: str, topic: Optional[str], language: str = "english") -> str:
        """Build generation prompt with voice guidelines"""
        
        # Get pillar details
        pillar_config = self.config["content_pillars"].get(pillar, {})
        topics = pillar_config.get("topics", [])
        
        # Select topic if not provided
        if not topic:
            topic = random.choice(topics) if topics else "general industry insight"
        
        # Get voice guidelines
        voice = self.config["voice_guidelines"]
        forbidden = voice["forbidden_phrases"]
        required = voice["required_language"]
        tone = voice["tone"]
        
        # Language instructions
        if language == "both":
            language_instruction = """⚠️ MANDATORY BILINGUAL REQUIREMENT - READ CAREFULLY:

You MUST create TWO SEPARATE, COMPLETE posts. This is NON-NEGOTIABLE.

OUTPUT FORMAT (copy this structure exactly):

### Post Text

[Write the COMPLETE English post here. Full length: 1,200-1,500 characters. Include hook, body, evidence, and call to action.]

---

### Versión en Español

[Write the COMPLETE Spanish post here. Full length: 1,200-1,500 characters. Include hook, body, evidence, and call to action.]

CRITICAL RULES - DO NOT SKIP:
1. Generate BOTH English AND Spanish versions
2. Each version must be 1,200-1,500 characters (FULL LENGTH)
3. Spanish version is NOT a translation - write it as a native Spanish business post
4. Both versions must follow all voice guidelines below
5. Both versions need the same structure and hook power
6. If you only generate one language, you have FAILED this task

VERIFICATION: Count to make sure you wrote TWO complete posts separated by ---"""
        elif language == "spanish":
            language_instruction = "IDIOMA: Genera el post COMPLETAMENTE en español. Usa español de negocios natural y profesional."
        else:
            language_instruction = "LANGUAGE: Generate the post in English only."
        
        # Build prompt
        prompt = f"""Generate a LinkedIn post with these specifications:

CONTENT PILLAR: {pillar}
POST FORMAT: {format_type}
TOPIC: {topic}

{language_instruction}

VOICE GUIDELINES:
Style: {tone['style']}
Perspective: {tone['perspective']}
Technical Depth: {tone['technical_depth']}

POSITIONING (must reinforce):
- Operations & Technology Leader
- COO-track positioning
- $500M+ portfolios experience
- 24 years in mining (16 years client-side operator + 9 years supplier)
- 360° view: operator + supplier + consultant + entrepreneur

CAREER FRAMING (when relevant):
- "Portfolio career model" (NOT "I quit my job")
- "Building ventures while exploring strategic opportunities"
- GoalPraxis: "Co-founding with partners who bring deep technology expertise"
- Focus on value creation, not lifestyle choice

FORBIDDEN PHRASES (never use):
{chr(10).join('- ' + p for p in forbidden)}

REQUIRED ELEMENTS:
1. Hook (first line must stop scroll)
2. Insight/story (specific, not generic)
3. Evidence (data, example, result)
4. Implication (so what?)
5. Call to action or question

FORMAT REQUIREMENTS:
- Length: 1,200-1,500 characters
- Paragraphs: 1-2 sentences each
- Line breaks for readability
- No emojis (unless data visualization: 📊 📈)
- Hashtags: 3-5 relevant, not trending-chasing

POST FORMAT GUIDE:
- insight: Share operational lesson with specific example
- story: Brief narrative with clear takeaway
- data: Lead with number/metric, explain why it matters
- question: Pose genuine question to audience
- contrarian: Challenge common assumption with evidence

AUTHENTICITY CHECK:
- Would Adolfo actually say this?
- Does it sound like a real operator, not a marketer?
- Is the insight specific enough to be valuable?
- Does it reinforce C-suite positioning without being arrogant?

Generate the post text, then provide hashtags separately."""

        return prompt
    
    def _generate_claude(self, prompt: str) -> str:
        """Generate using Claude (Anthropic)"""
        message = self.claude.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.content[0].text
    
    def _generate_gpt4(self, prompt: str) -> str:
        """Generate using GPT-4o (OpenAI)"""
        response = self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a LinkedIn post writer for a mining operations executive with 24 years experience. Write authentic, insightful posts that demonstrate expertise without sounding like marketing."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1024,
            temperature=0.7
        )
        return response.choices[0].message.content
    
    def _generate_gemini(self, prompt: str) -> str:
        """Generate using Gemini (Google)"""
        response = self.gemini.generate_content(prompt)
        return response.text
    
    def _parse_response(self, text: str) -> Dict:
        """Parse AI response into structured format"""
        # Clean up common AI response patterns
        text = text.strip()
        
        # Remove common prefixes that Gemini adds
        prefixes_to_remove = [
            "Here is the LinkedIn post text:",
            "Here's the LinkedIn post:",
            "LinkedIn Post:",
            "**LinkedIn Post:**",
        ]
        for prefix in prefixes_to_remove:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
        
        # Split by various hashtag markers
        split_markers = ["Hashtags:", "---", "**#"]
        post_text = text
        hashtag_section = ""
        
        for marker in split_markers:
            if marker in text:
                parts = text.split(marker, 1)
                post_text = parts[0].strip()
                hashtag_section = parts[1].strip()
                break
        
        # If no marker found, look for hashtags at the end
        if not hashtag_section:
            lines = text.split('\n')
            # Check if last few lines are hashtags
            hashtag_lines = []
            for line in reversed(lines):
                line = line.strip()
                if line and (line.startswith('#') or all(word.startswith('#') for word in line.split() if word)):
                    hashtag_lines.insert(0, line)
                elif line:  # Stop at first non-hashtag line
                    break
            
            if hashtag_lines:
                hashtag_section = ' '.join(hashtag_lines)
                # Remove hashtag lines from post text
                for _ in hashtag_lines:
                    lines.pop()
                post_text = '\n'.join(lines).strip()
        
        # Extract hashtags
        hashtags = []
        for word in hashtag_section.split():
            word = word.strip('*,.-')  # Remove markdown and punctuation
            if word.startswith("#"):
                clean_tag = word.split()[0] if ' ' in word else word  # Take first word if multiple
                if clean_tag not in hashtags:  # Avoid duplicates
                    hashtags.append(clean_tag)
        
        # If no hashtags found, generate some from the post
        if not hashtags:
            hashtags = ["#Leadership", "#Mining", "#Operations"]
        
        return {
            "text": post_text.strip(),
            "hashtags": " ".join(hashtags[:5])  # Max 5 hashtags
        }
    
    def batch_generate(self, 
                      count: int,
                      pillar_distribution: Optional[Dict[str, float]] = None) -> List[Dict]:
        """
        Generate multiple posts following pillar distribution
        
        Args:
            count: Number of posts to generate
            pillar_distribution: Custom distribution (defaults to config)
            
        Returns:
            List of generated posts
        """
        if not pillar_distribution:
            pillar_distribution = {
                "asset_management": 0.25,
                "technology": 0.30,
                "consulting": 0.10,
                "entrepreneurship": 0.25,
                "thought_leadership": 0.10
            }
        
        # Calculate post counts per pillar
        pillar_counts = {
            pillar: int(count * percentage)
            for pillar, percentage in pillar_distribution.items()
        }
        
        # Adjust for rounding
        total = sum(pillar_counts.values())
        if total < count:
            # Add remaining to largest pillar
            largest_pillar = max(pillar_distribution, key=pillar_distribution.get)
            pillar_counts[largest_pillar] += (count - total)
        
        # Generate posts
        posts = []
        formats = ["insight", "story", "data", "question", "contrarian"]
        providers = ["claude", "gpt4", "gemini"]
        
        for pillar, pillar_count in pillar_counts.items():
            for i in range(pillar_count):
                format_type = random.choice(formats)
                provider = random.choice(providers)
                
                try:
                    post = self.generate_post(
                        pillar=pillar,
                        format_type=format_type,
                        provider=provider
                    )
                    posts.append(post)
                    print(f"✓ Generated {pillar} / {format_type} post ({len(posts)}/{count})")
                except Exception as e:
                    print(f"✗ Error generating {pillar} post: {e}")
        
        return posts


if __name__ == "__main__":
    # Test generation
    generator = PostGenerator()
    
    print("Generating test post...")
    post = generator.generate_post(
        pillar="asset_management",
        format_type="insight",
        provider="claude"
    )
    
    print("\n" + "="*60)
    print("GENERATED POST:")
    print("="*60)
    print(post["text"])
    print("\n" + post["hashtags"])
    print("\n" + "="*60)
    print(f"Pillar: {post['pillar']}")
    print(f"Format: {post['format']}")
    print(f"Length: {post['length']} characters")
    print(f"Provider: {post['provider']}")
