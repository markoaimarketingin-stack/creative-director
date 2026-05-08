import base64
import io
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

import httpx
from PIL import Image, ImageColor, ImageDraw, ImageFont

from app.models import BrandAssets, Platform, RenderedAd

ASPECT_RATIO_SIZES: dict[str, tuple[int, int]] = {
    "1:1": (1080, 1080),
    "4:5": (1080, 1350),
    "9:16": (1080, 1920),
    "16:9": (1200, 675),
    "1.91:1": (1200, 628),
}

DEFAULT_SAFE_ZONES: dict[Platform, tuple[int, int, int, int]] = {
    Platform.META: (56, 56, 56, 96),
    Platform.TIKTOK: (56, 120, 56, 180),
    Platform.GOOGLE: (48, 48, 48, 64),
}


class AdCompositionService:
    def __init__(self, output_root: Path) -> None:
        self._output_root = output_root

    def compose_ad(
        self,
        *,
        image_source: str,
        primary_text: str,
        headline: str,
        description: str,
        cta: str,
        brand_name: str,
        brand_assets: BrandAssets,
        concept_id: str,
        platform: Platform,
        aspect_ratio: str,
        campaign_dir: Path,
    ) -> RenderedAd:
        canvas = self._load_base_image(image_source, aspect_ratio=aspect_ratio)
        width, height = canvas.size
        left, top, right, bottom = DEFAULT_SAFE_ZONES.get(platform, (56, 56, 56, 96))
        
        # Create a drawing context for the canvas
        draw = ImageDraw.Draw(canvas, "RGBA")

        # 1. Add a subtle bottom-to-top gradient (scrim) for text readability at the bottom
        scrim = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        scrim_draw = ImageDraw.Draw(scrim, "RGBA")
        
        # Draw a smooth gradient from bottom (semi-transparent black) to middle (transparent)
        gradient_height = int(height * 0.45)
        for y in range(height - gradient_height, height):
            alpha = int(180 * ((y - (height - gradient_height)) / gradient_height))
            scrim_draw.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))
        
        canvas = Image.alpha_composite(canvas, scrim)
        draw = ImageDraw.Draw(canvas, "RGBA")

        # 2. Fit fonts and text
        headline_font, headline_lines = self._fit_wrapped_text(
            draw=draw,
            text=headline,
            max_width=width - left - right - 48,
            max_height=int(height * 0.15),
            preferred_size=int(height * 0.055),
            min_size=32,
            max_lines=2,
        )
        body_font, body_lines = self._fit_wrapped_text(
            draw=draw,
            text=primary_text,
            max_width=width - left - right - 48,
            max_height=int(height * 0.12),
            preferred_size=int(height * 0.028),
            min_size=20,
            max_lines=3,
        )
        support_font, support_lines = self._fit_wrapped_text(
            draw=draw,
            text=description,
            max_width=width - left - right - 48,
            max_height=int(height * 0.05),
            preferred_size=int(height * 0.022),
            min_size=16,
            max_lines=1,
        )
        brand_font = self._load_font(brand_assets.font_family, max(32, int(height * 0.032)))
        cta_font = self._load_font(brand_assets.cta_font_family or brand_assets.font_family, max(24, int(height * 0.026)))

        # 3. Position Logo/Brand at Top Left (Clean integration)
        logo_y = top + 24
        brand_logo_box = self._paste_logo(
            canvas=canvas,
            logo_source=brand_assets.logo_image,
            brand_name=brand_name,
            font=brand_font,
            box=(left + 24, logo_y, width - right - 24, logo_y + 80),
            text_color="#FFFFFF", # Force white for premium contrast on images
        )

        # 4. Draw Headline with subtle shadow for "Floating" premium look
        cursor_y = height - bottom - int(height * 0.32)
        for line in headline_lines:
            # Subtle shadow
            draw.text((left + 26, cursor_y + 2), line, font=headline_font, fill=(0, 0, 0, 128))
            draw.text((left + 24, cursor_y), line.upper(), font=headline_font, fill="#FFFFFF")
            cursor_y += self._line_height(headline_font) + 4

        # 5. Draw Primary Text
        cursor_y += 8
        for line in body_lines:
            draw.text((left + 26, cursor_y + 1), line, font=body_font, fill=(0, 0, 0, 128))
            draw.text((left + 24, cursor_y), line, font=body_font, fill="#E0E0E0")
            cursor_y += self._line_height(body_font) + 4

        # 6. Draw CTA (Modern Outline/Ghost Button Style)
        button_width = min(400, max(260, int(width * 0.3)))
        button_height = max(70, int(height * 0.065))
        button_x = left + 24
        button_y = height - bottom - button_height - 12
        
        self._draw_cta_button(
            draw=draw,
            box=(button_x, button_y, button_x + button_width, button_y + button_height),
            text=cta,
            font=cta_font,
            fill_color=brand_assets.accent_color,
            text_color="#FFFFFF",
        )

        rendered_dir = campaign_dir / "rendered"
        rendered_dir.mkdir(parents=True, exist_ok=True)
        output_path = rendered_dir / f"{concept_id}.png"
        canvas.save(output_path, format="PNG", optimize=True)

        return RenderedAd(
            concept_id=concept_id,
            image_path=str(output_path),
            width=width,
            height=height,
            headline_lines=headline_lines,
            body_lines=body_lines,
            supporting_text=" ".join([line.strip() for line in support_lines if line.strip()]) or None,
            cta_text=cta,
            brand_name=brand_name,
        )

    def _load_base_image(self, image_source: str, *, aspect_ratio: str) -> Image.Image:
        image_bytes = self._read_binary(image_source)
        image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        target_size = ASPECT_RATIO_SIZES.get(aspect_ratio, ASPECT_RATIO_SIZES["1:1"])
        return self._cover_resize(image, target_size)

    def _read_binary(self, source: str) -> bytes:
        if source.startswith("data:"):
            encoded = source.split(",", 1)[1]
            return base64.b64decode(encoded)

        if source.startswith("/output/"):
            relative = source[len("/output/"):].lstrip("/")
            candidate = self._output_root / relative
            if candidate.exists():
                return candidate.read_bytes()

        path = Path(source)
        if path.exists():
            return path.read_bytes()

        parsed = urlparse(source)
        if parsed.scheme in {"http", "https"}:
            response = httpx.get(source, timeout=20.0, follow_redirects=True)
            response.raise_for_status()
            return response.content

        raise ValueError(f"Unsupported image source: {source}")

    def _cover_resize(self, image: Image.Image, target_size: tuple[int, int]) -> Image.Image:
        target_width, target_height = target_size
        scale = max(target_width / image.width, target_height / image.height)
        resized = image.resize((int(image.width * scale), int(image.height * scale)), Image.Resampling.LANCZOS)
        left = max(0, (resized.width - target_width) // 2)
        top = max(0, (resized.height - target_height) // 2)
        return resized.crop((left, top, left + target_width, top + target_height))

    def _fit_wrapped_text(
        self,
        *,
        draw: ImageDraw.ImageDraw,
        text: str,
        max_width: int,
        max_height: int,
        preferred_size: int,
        min_size: int,
        max_lines: int,
    ) -> tuple[ImageFont.FreeTypeFont | ImageFont.ImageFont, list[str]]:
        compact_text = " ".join(text.split())
        for font_size in range(preferred_size, min_size - 1, -2):
            font = self._load_font(None, font_size)
            lines = self._wrap_text(draw=draw, text=compact_text, font=font, max_width=max_width, max_lines=max_lines)
            total_height = len(lines) * self._line_height(font)
            if lines and total_height <= max_height:
                return font, lines

        fallback_font = self._load_font(None, min_size)
        return fallback_font, self._wrap_text(
            draw=draw,
            text=compact_text,
            font=fallback_font,
            max_width=max_width,
            max_lines=max_lines,
        )

    def _wrap_text(
        self,
        *,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        max_width: int,
        max_lines: int,
    ) -> list[str]:
        words = text.split()
        if not words:
            return [""]

        lines: list[str] = []
        current: list[str] = []
        index = 0
        while index < len(words):
            word = words[index]
            candidate = " ".join([*current, word])
            if self._text_width(draw, candidate, font) <= max_width:
                current.append(word)
                index += 1
                continue

            if current:
                lines.append(" ".join(current))
            current = [word]
            if len(lines) == max_lines - 1:
                break
            index += 1

        remaining_words = words[index + 1:] if len(lines) == max_lines - 1 else []
        if current:
            tail = " ".join([*current, *remaining_words]).strip()
            lines.append(self._ellipsis_to_fit(draw=draw, text=tail, font=font, max_width=max_width))

        return lines[:max_lines]

    def _ellipsis_to_fit(
        self,
        *,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        max_width: int,
    ) -> str:
        if self._text_width(draw, text, font) <= max_width:
            return text
        words = text.split()
        while words:
            candidate = " ".join(words).rstrip(" ,.;:") + "..."
            if self._text_width(draw, candidate, font) <= max_width:
                return candidate
            words.pop()
        return "..."

    def _draw_cta_button(
        self,
        *,
        draw: ImageDraw.ImageDraw,
        box: tuple[int, int, int, int],
        text: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        fill_color: str,
        text_color: str,
    ) -> None:
        draw.rounded_rectangle(box, radius=24, fill=ImageColor.getrgb(fill_color))
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_x = box[0] + ((box[2] - box[0]) - (text_bbox[2] - text_bbox[0])) // 2
        text_y = box[1] + ((box[3] - box[1]) - (text_bbox[3] - text_bbox[1])) // 2 - 2
        draw.text((text_x, text_y), text, font=font, fill=ImageColor.getrgb(text_color))

    def _paste_logo(
        self,
        *,
        canvas: Image.Image,
        logo_source: str | None,
        brand_name: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        box: tuple[int, int, int, int],
        text_color: str,
    ) -> tuple[int, int, int, int]:
        draw = ImageDraw.Draw(canvas, "RGBA")
        if logo_source:
            try:
                logo = Image.open(io.BytesIO(self._read_binary(logo_source))).convert("RGBA")
                logo.thumbnail((180, 72), Image.Resampling.LANCZOS)
                canvas.alpha_composite(logo, dest=(box[0], box[1]))
                return (box[0], box[1], box[0] + logo.width, box[1] + logo.height)
            except Exception:
                pass

        draw.text((box[0], box[1]), brand_name.upper(), font=font, fill=ImageColor.getrgb(text_color))
        text_bbox = draw.textbbox((box[0], box[1]), brand_name.upper(), font=font)
        return text_bbox

    def _load_font(self, font_path: str | None, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        candidates = [font_path] if font_path else []
        candidates.extend(
            [
                "C:/Windows/Fonts/timesbd.ttf", # Times New Roman Bold (Premium Serif)
                "C:/Windows/Fonts/georgiab.ttf", # Georgia Bold (Premium Serif)
                "C:/Windows/Fonts/segoeuib.ttf", # Segoe UI Bold (Modern Sans)
                "C:/Windows/Fonts/arialbd.ttf",
                "C:/Windows/Fonts/arial.ttf",
            ]
        )
        for candidate in candidates:
            if not candidate:
                continue
            try:
                # Use absolute paths if possible
                return ImageFont.truetype(candidate, size=size)
            except OSError:
                continue
        return ImageFont.load_default()

    @staticmethod
    def _line_height(font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> int:
        bbox = font.getbbox("Ag")
        return bbox[3] - bbox[1]

    @staticmethod
    def _text_width(
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    ) -> int:
        return draw.textbbox((0, 0), text, font=font)[2]


def _safe_color(color_str: str, default: str) -> str:
    try:
        ImageColor.getrgb(color_str)
        return color_str
    except ValueError:
        return default

def build_brand_assets(
    *,
    brand_name: str,
    logo_image: str | None,
    brand_colors: Iterable[str],
    brand_fonts: Iterable[str],
) -> BrandAssets:
    colors = [value.strip() for value in brand_colors if value and value.strip()]
    fonts = [value.strip() for value in brand_fonts if value and value.strip()]
    
    primary = _safe_color(colors[0], "#111111") if len(colors) >= 1 else "#111111"
    secondary = _safe_color(colors[1], "#F4F1EA") if len(colors) >= 2 else "#F4F1EA"
    accent = _safe_color(colors[2], "#E85D04") if len(colors) >= 3 else "#E85D04"
    text_color = "#111111" if secondary.lower() in {"#ffffff", "#f4f1ea", "#fffaf3"} else "#FFFFFF"
    
    return BrandAssets(
        primary_color=primary,
        secondary_color=secondary,
        accent_color=accent,
        text_color=text_color,
        font_family=fonts[0] if fonts else None,
        cta_font_family=fonts[1] if len(fonts) > 1 else (fonts[0] if fonts else None),
        logo_image=logo_image,
    )
