"""
Media Asset Generation Service
Generates stunning visual assets for LinkedIn posts
"""
import io
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
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
        
        # Check if carousel is bilingual by looking at first slide
        is_bilingual_carousel = len(slides) > 0 and bool(slides[0].get('content_en') and slides[0].get('content_es'))
        
        # ====================================================================
        # PHASE 1: Generate ALL images in PARALLEL (before PDF assembly)
        # This avoids Render's 30s timeout by running Imagen calls concurrently
        # ====================================================================
        style_descriptors = {
            'professional': 'clean, modern, professional business',
            'relaxed': 'warm, natural, organic',
            'corporate': 'sleek, corporate, executive',
            'creative': 'vibrant, artistic, creative',
            'minimal': 'minimalist, simple, clean'
        }
        style_desc = style_descriptors.get(style, 'professional')
        
        # Build prompts: index 0 = cover, index 1..N = slides
        image_prompts = {}
        cover_title_for_prompt = title if len(title) <= 70 else title[:70]
        image_prompts['cover'] = f"Photorealistic, {style_desc} aesthetic, high-quality image representing: {cover_title_for_prompt}. 16:9 aspect ratio, no text or words in image."
        
        for idx, slide in enumerate(slides):
            slide_content = slide.get('content_en', '') or slide.get('content', '')
            slide_title_raw = slide.get('title', '')
            topic = slide_title_raw if slide_title_raw else slide_content[:80]
            image_prompts[f'slide_{idx}'] = f"Photorealistic, {style_desc} aesthetic, high-quality image for: {topic}. Professional, clean, no text or words in image."
        
        # Fire all Imagen calls in parallel
        print(f"DEBUG: Generating {len(image_prompts)} images in parallel via Imagen 3...")
        import time as _time
        img_start = _time.time()
        generated_images = {}  # key -> PIL Image
        
        def _gen_image(key_prompt):
            key, prompt = key_prompt
            # Retry up to 2 times with backoff for rate-limit (429) errors
            for attempt in range(3):
                try:
                    img_bytes = self.generate_realistic_image(prompt)
                    return key, Image.open(io.BytesIO(img_bytes))
                except Exception as e:
                    err_str = str(e)
                    if '429' in err_str or 'quota' in err_str.lower():
                        wait = 2 * (attempt + 1)  # 2s, 4s, 6s
                        print(f"  Image '{key}' rate-limited, retry {attempt+1} in {wait}s...")
                        _time.sleep(wait)
                    else:
                        print(f"  Image '{key}' failed: {e}")
                        return key, None
            print(f"  Image '{key}' failed after 3 attempts (rate-limited)")
            return key, None
        
        # Cap concurrency at 4 to avoid Imagen quota limits (5 req/min default)
        max_parallel = min(4, len(image_prompts))
        with ThreadPoolExecutor(max_workers=max_parallel) as executor:
            futures = {executor.submit(_gen_image, (k, p)): k for k, p in image_prompts.items()}
            for future in as_completed(futures):
                try:
                    key, img = future.result()
                    if img:
                        generated_images[key] = img
                except Exception as e:
                    print(f"  Image future error: {e}")
        
        img_elapsed = _time.time() - img_start
        print(f"DEBUG: {len(generated_images)}/{len(image_prompts)} images generated in {img_elapsed:.1f}s")
        
        # ====================================================================
        # PHASE 2: Batch-translate titles in a single API call
        # ====================================================================
        
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Generate cover page
        c.setFillColorRGB(*color_scheme["bg"])
        c.rect(0, 0, width, height, fill=1)
        
        # Cover title - use directly if short enough, only summarize if too long
        cover_title = title if len(title) <= 70 else self._create_summary_title(title, max_chars=70)
        
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
        
        # Pre-translate all titles in a SINGLE API call (instead of per-slide)
        slide_titles_es = {}
        cover_title_es = ""
        if is_bilingual_carousel:
            all_titles_to_translate = [cover_title]
            for idx, slide in enumerate(slides):
                t = slide.get('title', '')
                if t and not t.startswith('Key Point'):
                    all_titles_to_translate.append(t)
            
            try:
                batch_prompt = "Translate each line below from English to Spanish. Return ONLY the translations, one per line, in the same order:\n" + "\n".join(all_titles_to_translate)
                batch_result = self._call_gemini(batch_prompt)
                translated_lines = [line.strip() for line in batch_result.strip().split('\n') if line.strip()]
                
                # First translation is the cover title
                cover_title_es = translated_lines[0] if translated_lines else cover_title
                
                # Rest are slide titles
                title_idx = 1
                for idx, slide in enumerate(slides):
                    t = slide.get('title', '')
                    if t and not t.startswith('Key Point') and title_idx < len(translated_lines):
                        slide_titles_es[idx] = translated_lines[title_idx]
                        title_idx += 1
                print(f"DEBUG: Batch-translated {len(all_titles_to_translate)} titles in 1 API call")
            except Exception as e:
                print(f"Batch translation failed: {e}")
                cover_title_es = cover_title  # Fallback: use English

        # Draw cover Spanish title if bilingual
        if is_bilingual_carousel and cover_title_es:
            
            c.setFillColorRGB(*color_scheme["secondary"])
            c.setFont("Helvetica-Oblique", 18)
            
            # Wrap Spanish title if too long (max width 550px)
            max_es_width = 550
            if c.stringWidth(cover_title_es, "Helvetica-Oblique", 18) > max_es_width:
                # Split into multiple lines
                words = cover_title_es.split()
                line1_words = []
                line2_words = []
                
                for i, word in enumerate(words):
                    test_line = ' '.join(line1_words + [word])
                    if c.stringWidth(test_line, "Helvetica-Oblique", 18) <= max_es_width:
                        line1_words.append(word)
                    else:
                        line2_words = words[i:]
                        break
                
                # Draw line 1
                line1 = ' '.join(line1_words)
                if line1:
                    title_width_es = c.stringWidth(line1, "Helvetica-Oblique", 18)
                    x_pos_es = (width - title_width_es) / 2
                    c.drawString(x_pos_es, y_pos, line1)
                    y_pos -= 24
                
                # Draw line 2
                line2 = ' '.join(line2_words)
                if line2:
                    title_width_es = c.stringWidth(line2, "Helvetica-Oblique", 18)
                    x_pos_es = (width - title_width_es) / 2
                    c.drawString(x_pos_es, y_pos, line2)
                    y_pos -= 24
            else:
                # Single line
                title_width_es = c.stringWidth(cover_title_es, "Helvetica-Oblique", 18)
                x_pos_es = (width - title_width_es) / 2
                c.drawString(x_pos_es, y_pos, cover_title_es)
                y_pos -= 28
        
        # Generate cover image using pre-generated AI image
        try:
            cover_img = generated_images.get('cover')
            if not cover_img:
                # Fallback to gradient if Imagen failed for cover
                cover_img = self._generate_cover_gradient(style, int(width * 0.85), int(height * 0.38))
            
            # Size for cover (fit within page)
            cover_max_h = height * 0.4
            cover_max_w = width * 0.85
            cover_img.thumbnail((int(cover_max_w), int(cover_max_h)), Image.Resampling.LANCZOS)
            
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
            
            # Title (wrapped and centered) - Intelligently condense if needed
            slide_title = slide.get('title', '')
            content_en = slide.get('content_en', '')
            content_es = slide.get('content_es', '')
            
            # Check if bilingual
            is_bilingual = bool(content_en and content_es)
            
            if not slide_title or slide_title.startswith('Key Point'):
                # Create title from content only if no title provided
                content_preview = content_en or slide.get('content', '')
                slide_title = self._create_summary_title(content_preview, max_chars=65)
            elif len(slide_title) > 65:
                # Only condense if actually too long (skip API call for short titles)
                slide_title = self._create_summary_title(slide_title, max_chars=65)
            
            # English title with intelligent wrapping
            c.setFillColorRGB(*color_scheme["accent"])
            c.setFont("Helvetica-Bold", 20)
            
            title_y = height - 40
            max_title_width = 520
            
            # Wrap title intelligently if needed
            title_lines = []
            if c.stringWidth(slide_title, "Helvetica-Bold", 20) > max_title_width:
                # Split into lines that fit
                words = slide_title.split()
                current_line = []
                
                for word in words:
                    test_line = ' '.join(current_line + [word])
                    if c.stringWidth(test_line, "Helvetica-Bold", 20) <= max_title_width:
                        current_line.append(word)
                    else:
                        if current_line:
                            title_lines.append(' '.join(current_line))
                        current_line = [word]
                
                if current_line:
                    title_lines.append(' '.join(current_line))
            else:
                title_lines = [slide_title]
            
            # Draw title lines (max 2 lines)
            for line in title_lines[:2]:
                title_width = c.stringWidth(line, "Helvetica-Bold", 20)
                title_x = (width - title_width) / 2
                c.drawString(title_x, title_y, line)
                title_y -= 26
            
            # Spanish translation if bilingual (use batch-translated title)
            if is_bilingual:
                slide_title_es = slide_titles_es.get(idx, slide_title)  # Fallback to English
                
                c.setFillColorRGB(*color_scheme["secondary"])
                c.setFont("Helvetica-Oblique", 14)
                title_width_es = c.stringWidth(slide_title_es, "Helvetica-Oblique", 14)
                title_x_es = (width - title_width_es) / 2
                c.drawString(title_x_es, title_y, slide_title_es)
                title_y -= 25
            
            # Calculate image start position after title
            image_start_y = title_y - 15
            
            # Use pre-generated AI image for this slide
            try:
                slide_img = generated_images.get(f'slide_{idx}')
                if not slide_img:
                    # Fallback to gradient if Imagen failed for this slide
                    slide_img = self._generate_themed_gradient(style, int(width * 0.65), int(height * 0.28))
                else:
                    # Resize AI image to fit slide area
                    slide_img.thumbnail((int(width * 0.65), int(height * 0.28)), Image.Resampling.LANCZOS)
                
                # Save to temp buffer
                img_buffer = io.BytesIO()
                slide_img.save(img_buffer, format='PNG')
                img_buffer.seek(0)
                
                # Position image centered below title
                img_x = (width - slide_img.width) / 2
                img_y = image_start_y - slide_img.height
                
                c.drawImage(ImageReader(img_buffer), img_x, img_y, 
                           width=slide_img.width, height=slide_img.height, mask='auto')
                
                content_start_y = img_y - 50
            except Exception as e:
                print(f"Slide image generation failed: {e}")
                content_start_y = height - 200
            
            # Get content
            content_en = slide.get('content_en', '')
            content_es = slide.get('content_es', '')
            
            # If bilingual content exists
            if content_en and content_es:
                # Use provided Spanish content directly (already translated by post generator)
                content_es_translated = content_es
                
                # Ensure content ends with period
                if content_en and not content_en.endswith(('.', '!', '?')):
                    content_en += '.'
                if content_es_translated and not content_es_translated.endswith(('.', '!', '?')):
                    content_es_translated += '.'
                
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
                
                # Content as flowing paragraphs with proper wrapping
                c.setFillColorRGB(*color_scheme["text"])
                c.setFont("Helvetica", 11)
                
                # Process English content (left) - wrap as complete text
                y_pos = content_start_y - 10
                wrapped_en = self._wrap_text(content_en, 28)
                for line in wrapped_en:
                    if y_pos < 100:  # Stop if too close to bottom
                        break
                    c.drawString(50, y_pos, line.strip())
                    y_pos -= 16
                
                # Process Spanish content (right) - wrap as complete text
                y_pos = content_start_y - 10
                wrapped_es = self._wrap_text(content_es_translated, 28)
                for line in wrapped_es:
                    if y_pos < 100:  # Stop if too close to bottom
                        break
                    c.drawString(divider_x + 25, y_pos, line.strip())
                    y_pos -= 16
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
    
    def _call_gemini(self, prompt_text: str, max_tokens: int = 500) -> str:
        """Call Gemini API with Vertex AI fallback for cloud environments"""
        import json
        
        is_cloud = os.getenv("RENDER") or os.getenv("RAILWAY_ENVIRONMENT")
        
        # Try consumer API first (only works locally, not on cloud)
        if not is_cloud:
            try:
                api_key = os.getenv('GOOGLE_API_KEY')
                if api_key:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-2.0-flash')
                    response = model.generate_content(prompt_text)
                    return response.text.strip()
            except Exception as e:
                print(f"Consumer Gemini failed: {e}, trying Vertex AI...")
        
        # Use Vertex AI (works on cloud servers)
        import requests
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account
        
        PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'linkedin-post-factory')
        LOCATION = 'us-central1'
        MODEL_ID = 'gemini-2.5-flash'
        
        creds_b64 = os.getenv('GCP_CREDENTIALS_JSON_B64')
        if not creds_b64:
            raise Exception("No GCP_CREDENTIALS_JSON_B64 env var for Vertex AI")
        
        creds_json = base64.b64decode(creds_b64).decode('utf-8')
        creds_data = json.loads(creds_json)
        
        credentials = service_account.Credentials.from_service_account_info(
            creds_data,
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        if not os.getenv('GCP_PROJECT_ID'):
            PROJECT_ID = creds_data.get('project_id', PROJECT_ID)
        
        auth_req = Request()
        credentials.refresh(auth_req)
        
        url = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{MODEL_ID}:generateContent"
        
        data = {
            "contents": [{"role": "user", "parts": [{"text": prompt_text}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": max_tokens}
        }
        
        response = requests.post(
            url,
            headers={
                'Authorization': f'Bearer {credentials.token}',
                'Content-Type': 'application/json'
            },
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            candidates = result.get('candidates', [])
            if candidates:
                parts = candidates[0].get('content', {}).get('parts', [])
                if parts:
                    return parts[0].get('text', '').strip()
        
        raise Exception(f"Vertex AI returned {response.status_code}: {response.text[:200]}")

    def _translate_to_spanish(self, english_text: str) -> str:
        """Translate English text to proper Spanish using Gemini API (with Vertex AI fallback)"""
        try:
            prompt_text = f"""Translate ONLY the following English text to Spanish. 
Return ONLY the Spanish translation, nothing else - no explanations, no options, no extra text.
Keep it professional and concise.

English: {english_text}

Spanish:"""
            
            spanish_text = self._call_gemini(prompt_text)
            
            # Clean up any markdown, labels, or extra formatting
            spanish_text = spanish_text.replace('**', '').replace('*', '').strip()
            
            # Remove common prefixes that Gemini might add
            prefixes_to_remove = [
                'Spanish:', 'Translation:', 'Spanish translation:', 
                'Translated:', 'Spanish Options', 'most common',
                'direct first', '(', ')'
            ]
            for prefix in prefixes_to_remove:
                if spanish_text.startswith(prefix):
                    spanish_text = spanish_text[len(prefix):].strip()
                spanish_text = spanish_text.replace(prefix + ':', '').strip()
            
            # Remove any text after a colon (usually explanations)
            if ':' in spanish_text and spanish_text.index(':') < 30:
                parts = spanish_text.split(':', 1)
                if len(parts) > 1:
                    spanish_text = parts[1].strip()
            
            return spanish_text
        except Exception as e:
            print(f"Translation error: {e}")
            # Fallback to original text if translation fails
            return english_text
    
    def _create_summary_title(self, text: str, max_chars: int = 60) -> str:
        """Create a condensed, compelling title from longer text using Gemini"""
        if not text or not text.strip():
            return "Key Insight"
        
        # If already short enough, use as-is
        if len(text.strip()) <= max_chars:
            return text.strip()
        
        # Use Gemini to intelligently condense while keeping meaning
        try:
            prompt_text = f"""Condense this text into a short, compelling title (max {max_chars} characters).
Keep the core meaning but make it concise and punchy.
Return ONLY the condensed title, nothing else.

Text: {text}

Condensed title:"""
            
            condensed = self._call_gemini(prompt_text)
            
            # Clean up
            condensed = condensed.replace('**', '').replace('*', '').strip()
            for prefix in ['Title:', 'Condensed:', 'Condensed title:']:
                if condensed.startswith(prefix):
                    condensed = condensed[len(prefix):].strip()
            
            # If still too long, truncate intelligently
            if len(condensed) > max_chars:
                words = condensed.split()
                result = []
                length = 0
                for word in words:
                    if length + len(word) + 1 <= max_chars:
                        result.append(word)
                        length += len(word) + 1
                    else:
                        break
                condensed = ' '.join(result)
            
            return condensed
        except:
            # Fallback: take first sentence/phrase
            first_sentence = text.split('.')[0].split('?')[0].split('!')[0]
            if len(first_sentence) > max_chars:
                words = first_sentence.split()[:6]
                return ' '.join(words)
            return first_sentence
    
    def _format_as_bullets(self, text: str) -> List[str]:
        """Convert text into bullet points, ensuring each ends with period"""
        if not text.strip():
            return []
        
        # Split by newlines or periods for sentences
        lines = text.replace('. ', '.\n').split('\n')
        bullets = []
        
        for line in lines:
            line = line.strip()
            if len(line) > 10:
                # Ensure bullet ends with period for completeness
                if not line.endswith(('.', '!', '?', ';')):
                    line += '.'
                bullets.append(line)
        
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
            from google.auth.transport.requests import Request
            from google.oauth2 import service_account
            
            # Vertex AI configuration - use new clean project
            PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'linkedin-post-factory')
            LOCATION = 'us-central1'
            MODEL_NAME = 'imagen-3.0-generate-001'
            
            print(f"🎨 Generating image via Vertex AI Imagen 3...")
            print(f"   Project: {PROJECT_ID}")
            print(f"   Prompt: {prompt[:80]}...")
            
            # Load credentials from GCP_CREDENTIALS_JSON_B64 (same as vertex_wrapper.py)
            credentials = None
            creds_b64 = os.getenv('GCP_CREDENTIALS_JSON_B64')
            
            if creds_b64:
                print(f"   Using credentials from GCP_CREDENTIALS_JSON_B64")
                creds_json = base64.b64decode(creds_b64).decode('utf-8')
                creds_data = json.loads(creds_json)
                
                cred_type = creds_data.get('type', '')
                if cred_type == 'service_account':
                    credentials = service_account.Credentials.from_service_account_info(
                        creds_data,
                        scopes=['https://www.googleapis.com/auth/cloud-platform']
                    )
                    # Use project from credentials if not set
                    if not os.getenv('GCP_PROJECT_ID'):
                        PROJECT_ID = creds_data.get('project_id', PROJECT_ID)
                else:
                    from google.oauth2.credentials import Credentials
                    credentials = Credentials(
                        token=None,
                        refresh_token=creds_data.get('refresh_token'),
                        token_uri='https://oauth2.googleapis.com/token',
                        client_id=creds_data.get('client_id'),
                        client_secret=creds_data.get('client_secret'),
                        scopes=['https://www.googleapis.com/auth/cloud-platform']
                    )
            else:
                # Fallback: try GOOGLE_APPLICATION_CREDENTIALS file path
                creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
                if creds_path and os.path.exists(creds_path):
                    print(f"   Using credentials from: {creds_path}")
                    credentials = service_account.Credentials.from_service_account_file(
                        creds_path,
                        scopes=['https://www.googleapis.com/auth/cloud-platform']
                    )
                else:
                    print(f"   Using default credentials (ADC)")
                    from google.auth import default
                    credentials, project = default(
                        scopes=['https://www.googleapis.com/auth/cloud-platform']
                    )
            
            if not credentials:
                raise Exception("No credentials available for Vertex AI")
            
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
            err_msg = str(e)
            # Re-raise rate-limit / quota errors so callers can retry
            if '429' in err_msg or 'quota' in err_msg.lower() or 'RESOURCE_EXHAUSTED' in err_msg:
                print(f"⚠️ IMAGEN RATE LIMITED — re-raising for retry")
                raise
            
            print(f"❌ IMAGEN GENERATION FAILED ❌")
            print(f"   Error type: {type(e).__name__}")
            print(f"   Error message: {err_msg}")
            import traceback
            traceback.print_exc()
            print(f"   Falling back to clean gradient placeholder")
            
            # Fallback: Clean professional gradient (no text overlay)
            img = Image.new('RGB', (1200, 675), (15, 20, 30))
            draw = ImageDraw.Draw(img)
            
            # Multi-layer gradient for depth
            for y in range(675):
                factor = y / 675
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
            
            # Subtle circle accents
            for cx, cy, r in [(200, 200, 120), (900, 400, 160), (600, 100, 80)]:
                overlay_draw.ellipse(
                    [(cx-r, cy-r), (cx+r, cy+r)],
                    outline=(255, 255, 255, 15), width=2
                )
            
            img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
            
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
    
    def _generate_themed_gradient(self, style: str, width: int, height: int) -> Image.Image:
        """Generate a professional themed gradient image matching carousel style"""
        import random
        
        # Style-specific gradient colors (start_rgb, end_rgb, accent_rgb)
        gradients = {
            "professional": ((15, 25, 50), (30, 80, 160), (74, 158, 255)),
            "relaxed": ((220, 230, 215), (180, 210, 190), (102, 179, 128)),
            "corporate": ((10, 15, 35), (20, 50, 100), (0, 102, 179)),
            "creative": ((40, 10, 55), (80, 20, 100), (230, 77, 153)),
            "minimal": ((240, 240, 245), (220, 225, 235), (100, 100, 120)),
        }
        
        start, end, accent = gradients.get(style, gradients["professional"])
        
        # Create gradient
        img = Image.new('RGB', (width, height), start)
        draw = ImageDraw.Draw(img)
        
        for y in range(height):
            factor = y / height
            r = int(start[0] + (end[0] - start[0]) * factor)
            g = int(start[1] + (end[1] - start[1]) * factor)
            b = int(start[2] + (end[2] - start[2]) * factor)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        
        # Add subtle geometric overlay
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Diagonal lines
        for i in range(0, width + height, 60):
            overlay_draw.line([(i - height, 0), (i, height)], fill=(255, 255, 255, 6), width=1)
        
        # Accent circles
        random.seed(hash(style))  # Deterministic per style
        for _ in range(3):
            cx = random.randint(int(width * 0.1), int(width * 0.9))
            cy = random.randint(int(height * 0.1), int(height * 0.9))
            r = random.randint(30, 80)
            overlay_draw.ellipse(
                [(cx - r, cy - r), (cx + r, cy + r)],
                outline=(*accent, 25), width=2
            )
        
        # Horizontal accent line
        line_y = height // 2
        overlay_draw.line(
            [(int(width * 0.15), line_y), (int(width * 0.85), line_y)],
            fill=(*accent, 20), width=1
        )
        
        img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
        return img

    def _generate_cover_gradient(self, style: str, width: int, height: int) -> Image.Image:
        """Generate a premium cover gradient image with more visual richness than slide gradients"""
        import random, math
        
        # Richer gradient palettes for covers (primary, secondary, highlight, accent)
        palettes = {
            "professional": ((8, 15, 40), (20, 60, 130), (45, 100, 200), (74, 158, 255)),
            "relaxed": ((200, 215, 195), (160, 195, 170), (120, 180, 140), (80, 160, 100)),
            "corporate": ((5, 10, 25), (15, 35, 80), (25, 60, 120), (0, 100, 180)),
            "creative": ((30, 5, 45), (65, 15, 85), (120, 30, 130), (230, 80, 160)),
            "minimal": ((245, 245, 250), (230, 232, 240), (210, 215, 228), (120, 125, 145)),
        }
        
        p1, p2, p3, accent = palettes.get(style, palettes["professional"])
        
        # Create multi-stop vertical gradient (fast line-based)
        img = Image.new('RGB', (width, height), p1)
        draw = ImageDraw.Draw(img)
        
        for y in range(height):
            factor = y / height
            if factor < 0.5:
                t = factor * 2
                r = int(p1[0] + (p2[0] - p1[0]) * t)
                g = int(p1[1] + (p2[1] - p1[1]) * t)
                b = int(p1[2] + (p2[2] - p1[2]) * t)
            else:
                t = (factor - 0.5) * 2
                r = int(p2[0] + (p3[0] - p2[0]) * t)
                g = int(p2[1] + (p3[1] - p2[1]) * t)
                b = int(p2[2] + (p3[2] - p2[2]) * t)
            draw.line([(0, y), (width, y)], fill=(min(255, r), min(255, g), min(255, b)))
        
        # Apply slight blur for smoothness
        img = img.filter(ImageFilter.GaussianBlur(radius=2))
        
        # Rich overlay with geometric design
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Grid of subtle dots
        dot_spacing = 40
        for x in range(0, width, dot_spacing):
            for y in range(0, height, dot_spacing):
                overlay_draw.ellipse(
                    [(x - 1, y - 1), (x + 1, y + 1)],
                    fill=(255, 255, 255, 8)
                )
        
        # Flowing curves
        random.seed(hash(style) + 42)
        for curve_idx in range(3):
            points = []
            base_y = height * (0.25 + curve_idx * 0.25)
            for x in range(0, width, 4):
                y_offset = math.sin(x / 80 + curve_idx * 2) * 30 + math.cos(x / 120) * 15
                points.append((x, int(base_y + y_offset)))
            if len(points) > 1:
                overlay_draw.line(points, fill=(*accent, 18), width=2)
        
        # Large accent circles (glass-like)
        for _ in range(5):
            cx = random.randint(0, width)
            cy = random.randint(0, height)
            radius = random.randint(40, 120)
            overlay_draw.ellipse(
                [(cx - radius, cy - radius), (cx + radius, cy + radius)],
                outline=(*accent, 15), width=2
            )
            # Inner ring
            inner_r = int(radius * 0.7)
            overlay_draw.ellipse(
                [(cx - inner_r, cy - inner_r), (cx + inner_r, cy + inner_r)],
                outline=(255, 255, 255, 8), width=1
            )
        
        # Bottom accent bar
        bar_height = 4
        overlay_draw.rectangle(
            [(int(width * 0.1), height - bar_height - 10),
             (int(width * 0.9), height - 10)],
            fill=(*accent, 40)
        )
        
        img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
        return img

    async def generate_interactive_html(
        self,
        prompt: str,
        title: str = "Interactive Demo"
    ) -> bytes:
        """
        Generate a self-contained interactive HTML file using AI
        """
        try:
            system_prompt = f"""Create a single-file, self-contained HTML/JS/CSS interactive component.
Topic: {title}
Description of functionality: {prompt}

Requirements:
- Must be a single HTML file with embedded CSS and JS.
- Design: Modern, professional, clean (like Stripe or Linear docs).
- Use Tailwind CSS (include via CDN: <script src="https://cdn.tailwindcss.com"></script>).
- Make it fully functional and interactive (buttons work, calcs work, etc.).
- Do not include markdown formatting (like ```html), just return the raw HTML."""
            
            html_content = self._call_gemini(system_prompt, max_tokens=8000)
            
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
