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
        title: str
    ) -> bytes:
        """
        Generate multi-page PDF carousel with bilingual content side-by-side
        """
        print(f"DEBUG: Generating PDF for title '{title}' with {len(slides)} slides")
        
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        for idx, slide in enumerate(slides):
            print(f"DEBUG: Processing slide {idx+1}")
            
            # Background gradient (simulated)
            c.setFillColorRGB(0.12, 0.12, 0.12)
            c.rect(0, 0, width, height, fill=1)
            
            # Slide number
            c.setFillColorRGB(0.5, 0.5, 0.5)
            c.setFont("Helvetica", 12)
            c.drawString(width - 60, 30, f"{idx + 1}/{len(slides)}")
            
            # Title (centered)
            slide_title = slide.get('title', f'Slide {idx + 1}')
            print(f"DEBUG: Slide title: {slide_title}")
            c.setFillColorRGB(0.29, 0.62, 1.0)  # Brand blue
            c.setFont("Helvetica-Bold", 32)
            
            # Center the title
            title_width = c.stringWidth(str(slide_title), "Helvetica-Bold", 32)
            title_x = (width - title_width) / 2
            c.drawString(title_x, height - 80, str(slide_title))
            
            # Get content and split by language if bilingual
            content = slide.get('content', '') or " "
            content_en = slide.get('content_en', '')
            content_es = slide.get('content_es', '')
            
            # If explicit English/Spanish provided, use bilingual layout
            if content_en and content_es:
                # Draw vertical divider
                divider_x = width / 2
                c.setStrokeColorRGB(0.29, 0.62, 1.0)
                c.setLineWidth(2)
                c.line(divider_x, height - 120, divider_x, 100)
                
                # Language labels
                c.setFillColorRGB(0.29, 0.62, 1.0)
                c.setFont("Helvetica-Bold", 14)
                c.drawString(60, height - 120, "🇺🇸 ENGLISH")
                c.drawString(divider_x + 30, height - 120, "🇪🇸 ESPAÑOL")
                
                # Content setup
                c.setFillColorRGB(1, 1, 1)
                c.setFont("Helvetica", 13)
                
                # Process English side (left)
                lines_en = self._wrap_text(content_en, 35)
                y_position = height - 155
                for line in lines_en[:18]:
                    c.drawString(50, y_position, line.strip())
                    y_position -= 24
                
                # Process Spanish side (right)
                lines_es = self._wrap_text(content_es, 35)
                y_position = height - 155
                for line in lines_es[:18]:
                    c.drawString(divider_x + 30, y_position, line.strip())
                    y_position -= 24
            else:
                # Single language layout (original behavior)
                c.setFillColorRGB(1, 1, 1)
                c.setFont("Helvetica", 16)
                
                # Simple text wrapping logic
                lines = self._wrap_text(content, 60)
                y_position = height - 140
                
                # Write lines
                for line in lines[:15]:
                    c.drawString(50, y_position, line.strip())
                    y_position -= 28
            
            # Border
            c.setStrokeColorRGB(0.29, 0.62, 1.0)
            c.setLineWidth(4)
            c.rect(10, 10, width - 20, height - 20)
            
            c.showPage()
        
        c.save()
        return buffer.getvalue()
    
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
