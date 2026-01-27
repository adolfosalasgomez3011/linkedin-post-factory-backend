"""
Media Asset Generation Service
Generates stunning visual assets for LinkedIn posts
"""
import io
import base64
from typing import Dict, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import ImageFormatter
from pygments.styles import get_style_by_name
import qrcode
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
import google.generativeai as genai
import os


class MediaGenerator:
    """Generate beautiful visual assets for LinkedIn posts"""
    
    def __init__(self):
        self.base_width = 1200
        self.base_height = 630  # LinkedIn optimal image size
        
    def generate_code_image(
        self,
        code: str,
        language: str = "python",
        theme: str = "monokai",
        title: Optional[str] = None
    ) -> bytes:
        """
        Generate beautiful code snippet image
        
        Args:
            code: Source code to visualize
            language: Programming language (python, javascript, java, etc.)
            theme: Pygments theme (monokai, github-dark, dracula, etc.)
            title: Optional title above code
            
        Returns:
            PNG image bytes
        """
        try:
            lexer = get_lexer_by_name(language, stripall=True)
        except:
            lexer = guess_lexer(code)
        
        # Generate code image with syntax highlighting
        formatter = ImageFormatter(
            style=theme,
            line_numbers=True,
            font_size=16,
            line_pad=6
        )
        
        code_img_data = highlight(code, lexer, formatter)
        code_img = Image.open(io.BytesIO(code_img_data))
        
        # Create canvas with padding and title
        padding = 60
        title_height = 80 if title else 0
        canvas_width = self.base_width
        canvas_height = code_img.height + (padding * 2) + title_height
        
        # Create gradient background
        canvas_img = Image.new('RGB', (canvas_width, canvas_height), '#1e1e1e')
        draw = ImageDraw.Draw(canvas_img)
        
        # Add gradient effect
        for y in range(canvas_height):
            color_val = int(30 + (y / canvas_height) * 20)
            draw.line([(0, y), (canvas_width, y)], fill=(color_val, color_val, color_val))
        
        # Add title if provided
        if title:
            try:
                font = ImageFont.truetype("arial.ttf", 32)
            except:
                font = ImageFont.load_default()
            
            draw.text(
                (padding, padding // 2),
                title,
                fill='#ffffff',
                font=font
            )
        
        # Paste code image
        code_x = (canvas_width - code_img.width) // 2
        code_y = padding + title_height
        canvas_img.paste(code_img, (code_x, code_y))
        
        # Add subtle border
        draw.rectangle(
            [(5, 5), (canvas_width - 5, canvas_height - 5)],
            outline='#4a9eff',
            width=3
        )
        
        # Convert to bytes
        output = io.BytesIO()
        canvas_img.save(output, format='PNG', quality=95)
        return output.getvalue()
    
    def generate_chart(
        self,
        chart_type: str,
        data: Dict,
        title: str,
        theme: str = "plotly_dark"
    ) -> bytes:
        """
        Generate interactive-style chart image
        
        Args:
            chart_type: bar, line, pie, scatter, area, funnel
            data: Chart data {'labels': [...], 'values': [...], 'x': [...], 'y': [...]}
            title: Chart title
            theme: Plotly theme
            
        Returns:
            PNG image bytes
        """
        fig = None
        
        if chart_type == "bar":
            fig = go.Figure(data=[
                go.Bar(
                    x=data.get('labels', []),
                    y=data.get('values', []),
                    marker_color='#4a9eff',
                    text=data.get('values', []),
                    textposition='auto',
                )
            ])
        
        elif chart_type == "line":
            fig = go.Figure(data=[
                go.Scatter(
                    x=data.get('x', []),
                    y=data.get('y', []),
                    mode='lines+markers',
                    line=dict(color='#4a9eff', width=3),
                    marker=dict(size=10)
                )
            ])
        
        elif chart_type == "pie":
            fig = go.Figure(data=[
                go.Pie(
                    labels=data.get('labels', []),
                    values=data.get('values', []),
                    hole=0.3,
                    marker=dict(colors=px.colors.qualitative.Vivid)
                )
            ])
        
        elif chart_type == "scatter":
            fig = go.Figure(data=[
                go.Scatter(
                    x=data.get('x', []),
                    y=data.get('y', []),
                    mode='markers',
                    marker=dict(
                        size=data.get('sizes', 12),
                        color=data.get('colors', '#4a9eff'),
                        opacity=0.8
                    )
                )
            ])
        
        elif chart_type == "area":
            fig = go.Figure(data=[
                go.Scatter(
                    x=data.get('x', []),
                    y=data.get('y', []),
                    fill='tozeroy',
                    fillcolor='rgba(74, 158, 255, 0.3)',
                    line=dict(color='#4a9eff', width=2)
                )
            ])
        
        elif chart_type == "funnel":
            fig = go.Figure(data=[
                go.Funnel(
                    y=data.get('labels', []),
                    x=data.get('values', []),
                    textposition="inside",
                    textinfo="value+percent initial",
                    marker=dict(color=px.colors.sequential.Blues_r)
                )
            ])
        
        if fig:
            fig.update_layout(
                title=dict(text=title, font=dict(size=24)),
                template=theme,
                width=self.base_width,
                height=self.base_height,
                showlegend=True,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(30,30,30,1)'
            )
            
            # Convert to image bytes
            img_bytes = fig.to_image(format="png", engine="kaleido")
            return img_bytes
        
        raise ValueError(f"Unsupported chart type: {chart_type}")
    
    def generate_infographic(
        self,
        title: str,
        stats: List[Dict[str, str]],
        brand_color: str = "#4a9eff"
    ) -> bytes:
        """
        Generate infographic with key statistics
        
        Args:
            title: Main title
            stats: List of {'label': 'X', 'value': 'Y'} dicts
            brand_color: Primary color hex
            
        Returns:
            PNG image bytes
        """
        img = Image.new('RGB', (self.base_width, self.base_height), '#1e1e1e')
        draw = ImageDraw.Draw(img)
        
        # Gradient background
        for y in range(self.base_height):
            factor = y / self.base_height
            r = int(30 + factor * 20)
            g = int(30 + factor * 20)
            b = int(50 + factor * 30)
            draw.line([(0, y), (self.base_width, y)], fill=(r, g, b))
        
        try:
            title_font = ImageFont.truetype("arialbd.ttf", 48)
            label_font = ImageFont.truetype("arial.ttf", 28)
            value_font = ImageFont.truetype("arialbd.ttf", 42)
        except:
            title_font = ImageFont.load_default()
            label_font = ImageFont.load_default()
            value_font = ImageFont.load_default()
        
        # Draw title
        draw.text((60, 50), title, fill='#ffffff', font=title_font)
        
        # Draw stats in grid
        stats_per_row = 3
        stat_width = (self.base_width - 120) // stats_per_row
        stat_height = 200
        start_y = 180
        
        for idx, stat in enumerate(stats[:6]):  # Max 6 stats
            row = idx // stats_per_row
            col = idx % stats_per_row
            
            x = 60 + (col * stat_width)
            y = start_y + (row * stat_height)
            
            # Draw stat box
            box_coords = [x, y, x + stat_width - 40, y + stat_height - 40]
            draw.rounded_rectangle(
                box_coords,
                radius=15,
                fill='#2a2a2a',
                outline=brand_color,
                width=3
            )
            
            # Draw value (large)
            value = stat.get('value', '')
            label = stat.get('label', '')
            
            value_bbox = draw.textbbox((0, 0), value, font=value_font)
            value_width = value_bbox[2] - value_bbox[0]
            value_x = x + (stat_width - 40 - value_width) // 2
            draw.text((value_x, y + 40), value, fill=brand_color, font=value_font)
            
            # Draw label (small)
            label_bbox = draw.textbbox((0, 0), label, font=label_font)
            label_width = label_bbox[2] - label_bbox[0]
            label_x = x + (stat_width - 40 - label_width) // 2
            draw.text((label_x, y + 110), label, fill='#cccccc', font=label_font)
        
        # Convert to bytes
        output = io.BytesIO()
        img.save(output, format='PNG', quality=95)
        return output.getvalue()
    
    def generate_qr_code(
        self,
        url: str,
        logo_path: Optional[str] = None
    ) -> bytes:
        """
        Generate QR code with optional logo
        
        Args:
            url: Target URL
            logo_path: Optional path to logo image
            
        Returns:
            PNG image bytes
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="#000000", back_color="#ffffff")
        img = img.convert('RGB')
        
        # Add logo if provided
        if logo_path and os.path.exists(logo_path):
            logo = Image.open(logo_path)
            logo_size = img.size[0] // 4
            logo = logo.resize((logo_size, logo_size))
            
            logo_pos = ((img.size[0] - logo_size) // 2, (img.size[1] - logo_size) // 2)
            img.paste(logo, logo_pos)
        
        # Convert to bytes
        output = io.BytesIO()
        img.save(output, format='PNG')
        return output.getvalue()
    
    def generate_carousel_pdf(
        self,
        slides: List[Dict[str, str]],
        title: str,
        style: str = "professional"
    ) -> bytes:
        """
        Generate multi-page PDF carousel with AI images and bilingual content
        
        Styles: professional, relaxed, corporate, creative, minimal
        """
        print(f"DEBUG: Generating PDF for title '{title}' with {len(slides)} slides, style: {style}")
        
        # Define color schemes for each style
        styles = {
            "professional": {
                "bg": (0.12, 0.12, 0.12),
                "accent": (0.29, 0.62, 1.0),  # Blue
                "text": (1, 1, 1),
                "secondary": (0.8, 0.8, 0.8)
            },
            "relaxed": {
                "bg": (0.95, 0.94, 0.92),
                "accent": (0.4, 0.7, 0.5),  # Green
                "text": (0.2, 0.2, 0.2),
                "secondary": (0.4, 0.4, 0.4)
            },
            "corporate": {
                "bg": (0.05, 0.08, 0.15),
                "accent": (0.0, 0.4, 0.7),  # Navy
                "text": (1, 1, 1),
                "secondary": (0.7, 0.7, 0.7)
            },
            "creative": {
                "bg": (0.15, 0.05, 0.2),
                "accent": (0.9, 0.3, 0.6),  # Pink
                "text": (1, 1, 1),
                "secondary": (0.9, 0.9, 0.9)
            },
            "minimal": {
                "bg": (1, 1, 1),
                "accent": (0, 0, 0),
                "text": (0, 0, 0),
                "secondary": (0.5, 0.5, 0.5)
            }
        }
        
        color_scheme = styles.get(style, styles["professional"])
        
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Generate cover page
        c.setFillColorRGB(*color_scheme["bg"])
        c.rect(0, 0, width, height, fill=1)
        
        # Cover title - create short summary (6-8 words)
        cover_title = self._create_summary_title(title, max_words=8)
        
        c.setFillColorRGB(*color_scheme["accent"])
        c.setFont("Helvetica-Bold", 36)
        
        # Wrap title to fit page width
        max_width = width - 100
        title_lines = self._wrap_title(cover_title, "Helvetica-Bold", 36, max_width, c)
        
        y_pos = height - 120
        for line in title_lines:
            line_width = c.stringWidth(line, "Helvetica-Bold", 36)
            x_pos = (width - line_width) / 2
            c.drawString(x_pos, y_pos, line)
            y_pos -= 45
        
        # Generate cover image using Gemini
        try:
            # Include style in prompt for consistent imagery
            style_desc = f"{style} style" if style != 'professional' else 'professional'
            cover_prompt = f"Photorealistic, {style_desc}, modern image representing: {cover_title}"
            cover_img_bytes = self.generate_realistic_image(cover_prompt)
            cover_img = Image.open(io.BytesIO(cover_img_bytes))
            
            # Size for cover (50% of page)
            cover_height = height * 0.4
            cover_width = width * 0.8
            cover_img.thumbnail((int(cover_width), int(cover_height)), Image.Resampling.LANCZOS)
            
            cover_buffer = io.BytesIO()
            cover_img.save(cover_buffer, format='PNG')
            cover_buffer.seek(0)
            
            img_x = (width - cover_img.width) / 2
            img_y = y_pos - cover_img.height - 40
            
            c.drawImage(ImageReader(cover_buffer), img_x, img_y,
                       width=cover_img.width, height=cover_img.height, mask='auto')
        except Exception as e:
            print(f"Cover image generation failed: {e}")
        
        c.showPage()
        
        # Generate content slides
        for idx, slide in enumerate(slides):
            print(f"DEBUG: Processing slide {idx+1}")
            
            # Background
            c.setFillColorRGB(*color_scheme["bg"])
            c.rect(0, 0, width, height, fill=1)
            
            # Slide number
            c.setFillColorRGB(*color_scheme["secondary"])
            c.setFont("Helvetica", 12)
            c.drawString(width - 60, 30, f"{idx + 1}/{len(slides)}")
            
            # Title (wrapped and centered) - Create short compelling title
            slide_title = slide.get('title', '')
            content_en = slide.get('content_en', '')
            content_es = slide.get('content_es', '')
            
            # Check if bilingual
            is_bilingual = bool(content_en and content_es)
            
            if not slide_title or slide_title.startswith('Key Point'):
                # Create concise title from content
                content_preview = content_en or slide.get('content', '')
                slide_title = self._create_summary_title(content_preview, max_words=6)
            else:
                # Ensure existing title is concise
                slide_title = self._create_summary_title(slide_title, max_words=6)
            
            # English title
            c.setFillColorRGB(*color_scheme["accent"])
            c.setFont("Helvetica-Bold", 24)
            
            title_y = height - 40
            title_width = c.stringWidth(slide_title, "Helvetica-Bold", 24)
            title_x = (width - title_width) / 2
            c.drawString(title_x, title_y, slide_title)
            title_y -= 32
            
            # Spanish translation if bilingual
            if is_bilingual and content_es:
                # Create Spanish title from Spanish content
                slide_title_es = self._create_summary_title(content_es, max_words=6)
                c.setFillColorRGB(*color_scheme["secondary"])
                c.setFont("Helvetica", 16)
                title_width_es = c.stringWidth(slide_title_es, "Helvetica", 16)
                title_x_es = (width - title_width_es) / 2
                c.drawString(title_x_es, title_y, slide_title_es)
                title_y -= 28
            
            # Calculate image start position after title
            image_start_y = title_y - 15
            
            # Generate and insert AI image (40% of page height, centered)
            try:
                # Create detailed image prompt matching carousel style
                content_preview = (content_en or slide.get('content', ''))[:150]
                style_desc = f"{style} aesthetic" if style != 'professional' else 'professional'
                image_prompt = f"Photorealistic, {style_desc}, high-quality image about: {slide_title}. {content_preview[:100]}"
                img_bytes = self.generate_realistic_image(image_prompt)
                
                img = Image.open(io.BytesIO(img_bytes))
                
                # Calculate dimensions (30% of page height for better spacing)
                img_height = height * 0.28
                img_width = width * 0.65
                
                # Resize image to fit
                img.thumbnail((int(img_width), int(img_height)), Image.Resampling.LANCZOS)
                
                # Save to temp buffer
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='PNG')
                img_buffer.seek(0)
                
                # Position image centered below title
                img_x = (width - img.width) / 2
                img_y = image_start_y - img.height
                
                c.drawImage(ImageReader(img_buffer), img_x, img_y, 
                           width=img.width, height=img.height, mask='auto')
                
                content_start_y = img_y - 50
            except Exception as e:
                print(f"Image generation failed: {e}")
                content_start_y = height - 200
            
            # Get content and format as bullets
            content_en = slide.get('content_en', '')
            content_es = slide.get('content_es', '')
            
            # If bilingual content exists
            if content_en and content_es:
                # Draw vertical divider
                divider_x = width / 2
                c.setStrokeColorRGB(*color_scheme["accent"])
                c.setLineWidth(1)
                c.line(divider_x, content_start_y + 20, divider_x, 80)
                
                # Language labels
                c.setFillColorRGB(*color_scheme["accent"])
                c.setFont("Helvetica-Bold", 12)
                c.drawString(50, content_start_y + 20, "🇺🇸 English")
                c.drawString(divider_x + 25, content_start_y + 20, "🇪🇸 Español")
                
                # Content as bullets (increased font size)
                c.setFillColorRGB(*color_scheme["text"])
                c.setFont("Helvetica", 12)
                
                # Process English bullets (left)
                bullets_en = self._format_as_bullets(content_en)
                y_pos = content_start_y - 10
                for bullet in bullets_en[:8]:
                    c.drawString(50, y_pos, "•")
                    wrapped = self._wrap_text(bullet, 28)
                    for line in wrapped[:2]:
                        c.drawString(65, y_pos, line.strip())
                        y_pos -= 18
                
                # Process Spanish bullets (right)
                bullets_es = self._format_as_bullets(content_es)
                y_pos = content_start_y - 10
                for bullet in bullets_es[:8]:
                    c.drawString(divider_x + 25, y_pos, "•")
                    wrapped = self._wrap_text(bullet, 28)
                    for line in wrapped[:2]:
                        c.drawString(divider_x + 40, y_pos, line.strip())
                        y_pos -= 18
            else:
                # Single language - centered bullets
                content = slide.get('content', content_en or content_es or '')
                bullets = self._format_as_bullets(content)
                
                c.setFillColorRGB(*color_scheme["text"])
                c.setFont("Helvetica", 13)
                
                y_pos = content_start_y
                for bullet in bullets[:10]:
                    # Center each bullet
                    bullet_text = f"• {bullet}"
                    text_width = c.stringWidth(bullet_text, "Helvetica", 13)
                    x_pos = (width - text_width) / 2
                    c.drawString(x_pos, y_pos, bullet_text)
                    y_pos -= 22
            
            # Border
            c.setStrokeColorRGB(*color_scheme["accent"])
            c.setLineWidth(3)
            c.rect(10, 10, width - 20, height - 20)
            
            c.showPage()
        
        c.save()
        return buffer.getvalue()
    
    def _create_summary_title(self, text: str, max_words: int = 6) -> str:
        """Create a short, compelling title from longer text (6-8 words max)"""
        if not text or not text.strip():
            return "Key Insight"
        
        # Remove common prefixes and clean text
        cleaned = text.strip()
        prefixes = ['Breakthrough:', 'Introduction:', 'Key Point:', 'Insight:']
        for prefix in prefixes:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
        
        # Take first sentence or phrase
        first_sentence = cleaned.split('.')[0].split('?')[0].split('!')[0]
        words = first_sentence.split()[:max_words]
        
        return ' '.join(words).strip('.,!?;:')
    
    def _format_as_bullets(self, text: str) -> List[str]:
        """Convert text into bullet points"""
        if not text.strip():
            return []
        
        # Split by newlines or periods for sentences
        lines = text.replace('. ', '.\n').split('\n')
        bullets = [line.strip() for line in lines if len(line.strip()) > 10]
        
        return bullets[:10]  # Max 10 bullets per slide
    
    def _wrap_title(self, text: str, font_name: str, font_size: int, max_width: float, canvas_obj) -> List[str]:
        """Wrap title text to fit within max width"""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            if canvas_obj.stringWidth(test_line, font_name, font_size) <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines if lines else [text]
    
    def _wrap_text(self, text: str, max_chars_per_line: int) -> List[str]:
        """Helper to wrap text into lines"""
        lines = []
        
        if not text.strip():
            return [" "]
        
        for raw_line in text.split('\n'):
            words = raw_line.split()
            if not words:
                lines.append(" ")
                continue
                
            current_line = ""
            for word in words:
                if len(current_line) + len(word) + 1 <= max_chars_per_line:
                    current_line += (word + " ")
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word + " "
            if current_line:
                lines.append(current_line)
        
        return lines
    
    def generate_realistic_image(self, prompt: str) -> bytes:
        """Generate photorealistic image using Vertex AI Imagen 3"""
        try:
            import requests
            import json
            import tempfile
            from google.auth.transport.requests import Request
            from google.auth import default
            from google.oauth2.credentials import Credentials
            
            # Vertex AI configuration (same as MCP server)
            PROJECT_ID = 'gen-lang-client-0439499588'
            LOCATION = 'us-central1'
            MODEL_NAME = 'imagen-3.0-generate-001'
            
            print(f"🎨 Generating image via Vertex AI Imagen 3...")
            print(f"   Prompt: {prompt[:80]}...")
            
            # Check if credentials are in environment variable (from Render Secret File)
            creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            
            if creds_path and os.path.exists(creds_path):
                print(f"   Using credentials from: {creds_path}")
                # Load credentials from file
                with open(creds_path, 'r') as f:
                    creds_data = json.load(f)
                
                # Create credentials object
                credentials = Credentials(
                    token=None,
                    refresh_token=creds_data.get('refresh_token'),
                    token_uri='https://oauth2.googleapis.com/token',
                    client_id=creds_data.get('client_id'),
                    client_secret=creds_data.get('client_secret'),
                    scopes=['https://www.googleapis.com/auth/cloud-platform']
                )
            else:
                print(f"   Using default credentials (ADC)")
                # Get credentials using Google Auth default
                credentials, project = default(
                    scopes=['https://www.googleapis.com/auth/cloud-platform']
                )
            
            # Get access token
            auth_req = Request()
            credentials.refresh(auth_req)
            access_token = credentials.token
            
            if not access_token:
                raise Exception("Failed to get OAuth2 access token")
            
            print(f"   ✅ Access token obtained")
            
            # Build the Vertex AI endpoint URL
            url = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{MODEL_NAME}:predict"
            
            # Prepare request data
            data = {
                "instances": [{"prompt": prompt}],
                "parameters": {
                    "sampleCount": 1,
                    "aspectRatio": "16:9"
                }
            }
            
            # Make request with OAuth2 Bearer token
            response = requests.post(
                url,
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                predictions = result.get('predictions', [])
                
                if predictions and len(predictions) > 0:
                    base64_image = predictions[0].get('bytesBase64Encoded')
                    if base64_image:
                        image_bytes = base64.b64decode(base64_image)
                        print(f"✅ Generated {len(image_bytes)} bytes via Vertex AI Imagen 3")
                        return image_bytes
            
            # If we got here, something went wrong
            error_text = response.text[:500] if response.text else 'No error details'
            raise Exception(f"Vertex AI returned {response.status_code}: {error_text}")
                
        except Exception as e:
            print(f"❌ IMAGEN GENERATION FAILED ❌")
            print(f"   Error type: {type(e).__name__}")
            print(f"   Error message: {str(e)}")
            import traceback
            print(f"   Traceback:")
            traceback.print_exc()
            print(f"   GOOGLE_APPLICATION_CREDENTIALS env var: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")
            print(f"   Falling back to styled gradient placeholder")
            # Fallback: Create professional gradient
            img = Image.new('RGB', (1200, 675), (15, 20, 30))
        draw = ImageDraw.Draw(img)
        
        # Multi-layer gradient for depth
        for y in range(675):
            factor = y / 675
            # Deep blue to cyan gradient
            r = int(15 + 45 * factor)
            g = int(20 + 120 * factor)
            b = int(30 + 180 * factor)
            draw.line([(0, y), (1200, y)], fill=(r, g, b))
        
        # Add geometric overlay for visual interest
        overlay = Image.new('RGBA', (1200, 675), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Diagonal lines pattern
        for i in range(0, 1400, 100):
            overlay_draw.line([(i-200, 0), (i, 675)], fill=(255, 255, 255, 8), width=2)
        
        img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
        draw = ImageDraw.Draw(img)
        
        # Add centered text with prompt
        try:
            title_font = ImageFont.truetype("arial.ttf", 52)
            subtitle_font = ImageFont.truetype("arial.ttf", 28)
        except:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
        
        # Wrap prompt text
        words = prompt.split()
        lines = []
        current = []
        for word in words:
            current.append(word)
            test_line = ' '.join(current)
            if len(test_line) > 35:
                current.pop()
                if current:
                    lines.append(' '.join(current))
                current = [word]
        if current:
            lines.append(' '.join(current))
        
        # Draw text with shadow
        y_offset = 220
        for line in lines[:3]:
            bbox = draw.textbbox((0, 0), line, font=title_font)
            text_w = bbox[2] - bbox[0]
            x = (1200 - text_w) / 2
            # Shadow
            draw.text((x+3, y_offset+3), line, fill=(0, 0, 0, 180), font=title_font)
            # Main text
            draw.text((x, y_offset), line, fill=(255, 255, 255), font=title_font)
            y_offset += 70
        
        # Watermark
        watermark = "AI Generated Visual"
        wm_bbox = draw.textbbox((0, 0), watermark, font=subtitle_font)
        wm_w = wm_bbox[2] - wm_bbox[0]
        draw.text((1200 - wm_w - 30, 635), watermark, fill=(255, 255, 255, 100), font=subtitle_font)
        
        output = io.BytesIO()
        img.save(output, format='PNG', quality=95)
        return output.getvalue()
    
    def _get_bg_color(self, style: str) -> Tuple[int, int, int]:
        """Get background color for style"""
        colors = {
            "professional": (30, 30, 30),
            "relaxed": (242, 240, 235),
            "corporate": (13, 20, 38),
            "creative": (38, 13, 51),
            "minimal": (255, 255, 255)
        }
        return colors.get(style, (30, 30, 30))
    
    def _get_accent_color(self, style: str) -> Tuple[int, int, int]:
        """Get accent color for style"""
        colors = {
            "professional": (74, 158, 255),
            "relaxed": (102, 179, 128),
            "corporate": (0, 102, 179),
            "creative": (230, 77, 153),
            "minimal": (0, 0, 0)
        }
        return colors.get(style, (74, 158, 255))
    
    async def generate_interactive_html(
        self,
        prompt: str,
        title: str = "Interactive Demo"
    ) -> bytes:
        """
        Generate a self-contained interactive HTML file using AI
        """
        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            system_prompt = f"""
            Create a single-file, self-contained HTML/JS/CSS interactive component.
            Topic: {title}
            Description of functionality: {prompt}
            
            Requirements:
            - Must be a single HTML file with embedded CSS and JS.
            - Design: Modern, professional, clean (like Stripe or Linear docs).
            - Use Tailwind CSS (include via CDN: <script src="https://cdn.tailwindcss.com"></script>).
            - Make it fully functional and interactive (buttons work, calcs work, etc.).
            - Do not include markdown formatting (like ```html), just return the raw HTML.
            """
            
            response = model.generate_content(system_prompt)
            html_content = response.text
            
            # Clean up markdown if present
            if "```" in html_content:
                html_content = html_content.replace("```html", "").replace("```", "")
            
            return html_content.encode('utf-8')
        except Exception as e:
            print(f"Error generating HTML: {e}")
            fallback = f"<html><body><h1>Generation Error</h1><p>{str(e)}</p></body></html>"
            return fallback.encode('utf-8')

    async def generate_ai_image(
        self,
        prompt: str,
        style: str = "professional"
    ) -> bytes:
        """
        Generate AI image using Gemini Vision
        
        Args:
            prompt: Image description
            style: Style modifier (professional, artistic, technical, minimal)
            
        Returns:
            Image bytes (Note: Gemini doesn't generate images, returns placeholder)
        """
        # Note: Gemini Pro doesn't generate images
        # For image generation, you'd need DALL-E, Midjourney, or Stable Diffusion
        # This creates a placeholder with the prompt
        
        img = Image.new('RGB', (self.base_width, self.base_height), '#1e1e1e')
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("arial.ttf", 24)
            title_font = ImageFont.truetype("arialbd.ttf", 32)
        except:
            font = ImageFont.load_default()
            title_font = ImageFont.load_default()
        
        draw.text((60, 100), "AI Image Generation", fill='#4a9eff', font=title_font)
        draw.text((60, 180), "Prompt:", fill='#ffffff', font=font)
        
        # Wrap prompt text
        words = prompt.split()
        lines = []
        current_line = []
        
        for word in words:
            current_line.append(word)
            test_line = ' '.join(current_line)
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] > self.base_width - 120:
                current_line.pop()
                lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        y = 240
        for line in lines[:8]:
            draw.text((60, y), line, fill='#cccccc', font=font)
            y += 40
        
        draw.text(
            (60, self.base_height - 80),
            "Note: Connect DALL-E or Stable Diffusion for real AI images",
            fill='#888888',
            font=font
        )
        
        output = io.BytesIO()
        img.save(output, format='PNG', quality=95)
        return output.getvalue()


# Global instance
media_generator = MediaGenerator()
