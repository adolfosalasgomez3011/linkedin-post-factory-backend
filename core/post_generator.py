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
import re
import anthropic
import openai
from google import generativeai as genai
try:
    from core.vertex_wrapper import VertexWrapper
except ImportError:
    VertexWrapper = None

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
        # Gemini (Google) - Primary provider (1.5 Flash - most stable)
        google_key = os.getenv("GOOGLE_API_KEY")
        
        # Initialize Vertex AI Wrapper (for Enterprise/Cloud usage without geo-blocking)
        if VertexWrapper:
            self.vertex = VertexWrapper() # Auto-detects credentials
        else:
            self.vertex = None
            
        if google_key:
            # Force REST transport to avoid gRPC geo-blocking issues on cloud servers
            try:
                genai.configure(api_key=google_key, transport='rest')
                self.gemini = genai.GenerativeModel('gemini-2.0-flash')
            except Exception as e:
                print(f"Gemini initialization error: {e}")
                self.gemini = None
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
                     channel: str = "personal_career",
                     language: str = "english",
                     provider: str = "gemini",
                     source_context: Optional[Dict] = None) -> Dict:
        """
        Generate a LinkedIn post
        
        Args:
            pillar: Content pillar (asset_management, technology, consulting, entrepreneurship, thought_leadership)
            format_type: Post format (insight, story, data, question, contrarian)
            topic: Optional specific topic
            channel: Channel profile (personal_career, goalpraxis_company)
            language: Language (english, spanish, both)
            provider: AI provider (claude, gpt4, gemini)
            
        Returns:
            Dict with post text, metadata, and voice score
        """
        # Build prompt
        prompt = self._build_prompt(pillar, format_type, topic, channel, language, source_context)
        
        # Generate with selected provider
        text = self._generate_with_provider(provider, prompt)
        
        # Extract components
        post_data = self._parse_response(text)

        # If source context exists, enforce a strict no-fabrication safety pass.
        if source_context and self._has_unsupported_source_claims(post_data.get("text", ""), source_context):
            correction_prompt = (
                prompt
                + "\n\nSAFETY REVISION (MANDATORY):"
                + "\nThe prior draft introduced unsupported source claims."
                + "\nRewrite the post so every company-to-vendor relation is source-grounded."
                + "\nNever claim hiring, selection, deployment, partnership, implementation, or customer status unless explicitly in the source evidence."
                + "\nIf uncertain, use neutral wording like: 'the article suggests', 'this may indicate', or 'for teams pursuing similar outcomes'."
            )
            text = self._generate_with_provider(provider, correction_prompt)
            post_data = self._parse_response(text)

            # Final hard guardrail: strip risky sentences if model still violates source grounding.
            if self._has_unsupported_source_claims(post_data.get("text", ""), source_context):
                post_data["text"] = self._strip_unsupported_source_claims(post_data.get("text", ""))
        
        # Add metadata
        post_data.update({
            "pillar": pillar,
            "format": format_type,
            "topic": topic or "general",
            "channel": channel,
            "provider": provider,
            "generated_at": datetime.now().isoformat(),
            "length": len(post_data["text"])
        })
        
        return post_data

    def _generate_with_provider(self, provider: str, prompt: str) -> str:
        if provider == "gemini":
            return self._generate_gemini(prompt)
        if provider == "gpt4":
            return self._generate_gpt4(prompt)
        if provider == "claude":
            if self.claude is None:
                raise ValueError("Claude API not configured. Use 'gemini' or 'gpt4' instead.")
            return self._generate_claude(prompt)
        raise ValueError(f"Unknown provider: {provider}. Use 'gemini' or 'gpt4'.")
    
    def _build_prompt(self, pillar: str, format_type: str, topic: Optional[str], channel: str, language: str = "english", source_context: Optional[Dict] = None) -> str:
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
        tone = voice["tone"]

        # Channel profile (safe defaults if missing in config)
        channel_profiles = self.config.get("channel_profiles", {})
        channel_profile = channel_profiles.get(channel, {
            "label": "Personal Career",
            "goal": "Position as a senior mining operations leader",
            "audience": [
                "Mining General Managers",
                "COOs",
                "Executive recruiters"
            ],
            "cta_style": "conversation",
            "do_not_mix": ["company sales pitch"],
        })

        audience_text = ", ".join(channel_profile.get("audience", []))
        do_not_mix_text = ", ".join(channel_profile.get("do_not_mix", []))
        
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
        
        source_block = ""
        if source_context:
            source_title = (source_context.get("source_title") or topic or "").strip()
            source_url = (source_context.get("source_url") or "").strip()
            source_summary = (source_context.get("source_summary") or source_context.get("reasoning") or "").strip()
            source_name = (source_context.get("source_name") or "").strip()
            key_findings = source_context.get("key_findings") or []
            article_text = (source_context.get("article_text") or "").strip()

            findings_block = ""
            if key_findings:
                findings_list = "\n    ".join([
                    f"• {item.get('finding', '')} {item.get('source_attribution', '')}"
                    for item in key_findings
                    if item.get('finding')
                ])
                # Pick the single most "shocking" finding to force into the hook
                first_finding = next(
                    (item for item in key_findings if item.get('finding')), None
                )
                hook_example = (
                    f'"{first_finding["finding"].strip()}"'
                    if first_finding else "the specific statistic above"
                )
                findings_block = f"""
⚠️  KEY FINDINGS — THESE MUST APPEAR IN YOUR POST (NON-NEGOTIABLE):
    {findings_list}

    ═══════════════════════════════════════════════
    OPENING MANDATE — READ BEFORE WRITING ANYTHING:
    ═══════════════════════════════════════════════
    Your FIRST paragraph MUST open with the most shocking/specific finding above.
    Quote or closely paraphrase it — do NOT save it for later.
    Do NOT open with generic statements like "Technology is transforming mining."

    BAD opening: "Breakthroughs are creating new tailwinds for innovation in mining."
    GOOD opening: {hook_example}

    If you skip this rule, the post FAILS. Start with the data. Every time."""
            else:
                if article_text:
                    findings_block = f"""
    ARTICLE TEXT (use this as your primary evidence — ground the post in what the article actually says):
    ---
    {article_text[:3000]}
    ---
    No structured statistics were auto-extracted, but the full article text above IS available.
    Read it carefully and build the post around the most relevant facts, claims, or trends it contains.
    Do NOT invent numbers, companies, or events beyond what is stated in the text above.
    Label any interpretation clearly as your view (e.g. "In my view..." or "This suggests...").
"""
                else:
                    findings_block = """
    NO EXTRACTED FINDINGS WERE AVAILABLE.
    You must stay anchored to the selected source title and source summary only.
    Do NOT import outside statistics, OECD/McKinsey data, or generic mining narratives unless they are explicitly present in the source evidence above.
    If the source is high-level, write a high-level post about that exact market/theme and clearly label any interpretation as your view, not as sourced fact.
"""
            
            source_block = f"""
    SOURCE EVIDENCE (STRICT GROUNDING REQUIRED):
    - Source Name: {source_name or "Unknown"}
    - Source Title: {source_title or "Unknown"}
    - Source URL: {source_url or "Unknown"}
    - Source Summary: {source_summary or "Unknown"}
{findings_block}

    SOURCE-TRUTH RULES (MANDATORY):
    1) Do NOT invent company relationships, contracts, deployments, partnerships, customer status, or vendor selections.
    2) If the source does not explicitly mention a relationship with MinePulse (or any vendor), do not state or imply it as fact.
    3) Separate statements clearly:
       - FACT: only what source states.
       - INTERPRETATION: use labels like "this may indicate".
       - BRAND POV: generic capability framing only (no claim about the source company).
    4) Never write unsupported claims such as "X hired/selected/partnered with MinePulse" unless explicitly evidenced above.
    """

        # Channel-specific brand voice
        channel_brand_voice = ""
        if channel == "goalpraxis_company":
            channel_brand_voice = """
    BRAND VOICE FOR GOALPRAXIS COMPANY CHANNEL (CRITICAL):
    - Focus on GoalPraxis's unique approach, methodology, or market position
    - Highlight client value, outcomes, and strategic differentiation
    - Minimize personal credentials and autobiography
    - Emphasize operational results, technology alignment, and measurable impact
    - CTA should drive toward pilot engagement, business cases, or strategic conversations
    - Avoid "I have 24 years..." phrasing; use "GoalPraxis enables..." or "Our approach..."
    """
        else:
            channel_brand_voice = """
    PERSONAL CAREER CHANNEL - USE YOUR AUTHENTIC VOICE:
    - Lead with your 24-year journey and diverse experience
    - Share specific operational lessons from client-side, supplier, and advisor roles
    - Your unique positioning: operator + supplier + consultant + entrepreneur
    - Make it personal; readers want to connect with YOUR insights, not a corporation
    - Use "I've observed", "In my experience", "When I led..."
    """

        # Build prompt
        prompt = f"""Generate a LinkedIn post with these specifications:

    CHANNEL MODE: {channel_profile.get("label", channel)}
    CHANNEL GOAL: {channel_profile.get("goal", "Build trust and visibility")}
    CHANNEL AUDIENCE: {audience_text}
    DO NOT MIX WITH: {do_not_mix_text}
    CTA STYLE: {channel_profile.get("cta_style", "conversation")}
{channel_brand_voice}

CONTENT PILLAR: {pillar}
POST FORMAT: {format_type}
TOPIC: {topic}

{source_block}

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
- Does it stay strictly in the selected channel context?

Generate the post text, then provide hashtags separately."""

        return prompt

    def _has_unsupported_source_claims(self, text: str, source_context: Dict) -> bool:
        if not text:
            return False

        evidence = " ".join([
            str(source_context.get("source_title") or ""),
            str(source_context.get("source_summary") or ""),
            str(source_context.get("reasoning") or ""),
        ]).lower()

        if not evidence:
            return False

        evidence_mentions_minepulse = "minepulse" in evidence
        minepulse_related_pattern = re.compile(
            r"(minepulse|goalpraxis).{0,80}(partner|partnership|hire|hired|select|selected|choose|chose|deploy|deployed|implement|implemented|use|using|customer|client|contract)|"
            r"(partner|partnership|hire|hired|select|selected|choose|chose|deploy|deployed|implement|implemented|use|using|customer|client|contract).{0,80}(minepulse|goalpraxis)",
            flags=re.IGNORECASE,
        )
        spanish_relation_pattern = re.compile(
            r"(minepulse|goalpraxis).{0,80}(alianza|asociaci[oó]n|contrat[oó]|seleccion[oó]|implement[oó]|cliente)|"
            r"(alianza|asociaci[oó]n|contrat[oó]|seleccion[oó]|implement[oó]|cliente).{0,80}(minepulse|goalpraxis)",
            flags=re.IGNORECASE,
        )

        if not evidence_mentions_minepulse and (minepulse_related_pattern.search(text) or spanish_relation_pattern.search(text)):
            return True

        return False

    def _strip_unsupported_source_claims(self, text: str) -> str:
        if not text:
            return text

        risky = re.compile(
            r"(minepulse|goalpraxis).{0,120}(partner|partnership|hire|hired|select|selected|choose|chose|deploy|deployed|implement|implemented|use|using|customer|client|contract|alianza|asociaci[oó]n|contrat[oó]|seleccion[oó]|implement[oó])|"
            r"(partner|partnership|hire|hired|select|selected|choose|chose|deploy|deployed|implement|implemented|use|using|customer|client|contract|alianza|asociaci[oó]n|contrat[oó]|seleccion[oó]|implement[oó]).{0,120}(minepulse|goalpraxis)",
            flags=re.IGNORECASE,
        )

        sentences = re.split(r'(?<=[.!?])\s+', text)
        safe_sentences = [s for s in sentences if not risky.search(s)]
        cleaned = " ".join(safe_sentences).strip()
        if not cleaned:
            cleaned = (
                "The article highlights an operational technology trend in mining. "
                "A useful takeaway is to focus on measurable outcomes and avoid unsupported assumptions about vendor relationships."
            )
        return cleaned
    
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
        error_msg = ""
        
        # On Render (cloud), skip standard Gemini entirely - it always fails with geo-block
        # Go straight to Vertex AI which we know works
        is_cloud = os.getenv("RENDER") or os.getenv("RAILWAY_ENVIRONMENT")
        
        # 1. Try Standard Gemini (Consumer API) - Only on local dev
        if not is_cloud:
            try:
                if self.gemini:
                    response = self.gemini.generate_content(prompt)
                    return response.text
            except Exception as e:
                error_msg = str(e)
                print(f"Standard Gemini failed ({e}), trying fallbacks...")
        else:
            error_msg = "Skipped on cloud (geo-blocked)"
            print("Skipping standard Gemini on cloud, using Vertex AI directly...")

        # 2. Try Vertex AI (Enterprise API - Bypasses Geo Block)
        vertex_error = ""
        if self.vertex and self.vertex.credentials:
            try:
                print("Attempting generation via Vertex AI...")
                vertex_response = self.vertex.generate_content(prompt)
                if vertex_response:
                    return vertex_response
                else:
                    vertex_error = "Vertex AI returned empty response"
                    print(vertex_error)
            except Exception as ve:
                vertex_error = str(ve)
                print(f"Vertex AI exception: {vertex_error}")
        else:
            vertex_error = f"Vertex not available (vertex={self.vertex is not None}, creds={self.vertex.credentials is not None if self.vertex else 'N/A'})"
            print(vertex_error)
        
        # 3. Fallback to OpenAI
        if self.openai_client:
            print(f"All Gemini methods failed. Falling back to OpenAI...")
            return self._generate_gpt4(prompt)
            
        # If we got here, everything failed
        raise Exception(f"All AI providers failed. Gemini error: {error_msg} | Vertex error: {vertex_error}")
    
    def _parse_response(self, text: str) -> Dict:
        """Parse AI response into structured format"""
        # Clean up common AI response patterns
        text = text.strip()
        
        # Remove common prefixes that Gemini adds
        prefixes_to_remove = [
            "Here's a LinkedIn post draft meeting your specifications:",
            "Here is a LinkedIn post draft meeting your specifications:",
            "Here is the LinkedIn post text:",
            "Here's the LinkedIn post:",
            "LinkedIn Post:",
            "**LinkedIn Post:**",
        ]
        for prefix in prefixes_to_remove:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()

        for post_text_marker in ["**POST TEXT:**", "POST TEXT:", "### Post Text"]:
            if post_text_marker in text:
                text = text.split(post_text_marker, 1)[1].strip()
                break
        
        # Split by various hashtag markers (removed --- to preserve bilingual separator)
        split_markers = ["**HASHTAGS:**", "HASHTAGS:", "Hashtags:", "### Hashtags", "**#"]
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

        post_text = post_text.strip()
        while post_text.endswith("---") or post_text.endswith("**"):
            if post_text.endswith("---"):
                post_text = post_text[:-3].rstrip()
            if post_text.endswith("**"):
                post_text = post_text[:-2].rstrip()
        
        return {
            "text": post_text,
            "hashtags": hashtags[:5]
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
    print("\n" + " ".join(post["hashtags"]))
    print("\n" + "="*60)
    print(f"Pillar: {post['pillar']}")
    print(f"Format: {post['format']}")
    print(f"Length: {post['length']} characters")
    print(f"Provider: {post['provider']}")
