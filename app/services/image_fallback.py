import base64
import io

from PIL import Image, ImageColor, ImageDraw, ImageFont

from app.models import CreativeInput, CreativeStatus, GeneratedCreative, VisualConcept
from app.services.composition import ASPECT_RATIO_SIZES


class LocalImageFallbackService:
    def generate_batch(
        self,
        *,
        payload: CreativeInput,
        concepts: list[VisualConcept],
        existing: list[GeneratedCreative],
    ) -> list[GeneratedCreative]:
        existing_lookup = {item.concept_id: item for item in existing}
        completed: list[GeneratedCreative] = []
        for concept in concepts:
            current = existing_lookup.get(concept.concept_id)
            if current and current.status == CreativeStatus.GENERATED and current.image_urls:
                completed.append(current)
                continue
            completed.append(self._build_placeholder(payload=payload, concept=concept, previous=current))
        return completed

    def _build_placeholder(
        self,
        *,
        payload: CreativeInput,
        concept: VisualConcept,
        previous: GeneratedCreative | None,
    ) -> GeneratedCreative:
        size = ASPECT_RATIO_SIZES.get(concept.aspect_ratio, ASPECT_RATIO_SIZES["1:1"])
        image = Image.new("RGB", size, ImageColor.getrgb(self._primary_color(payload)))
        draw = ImageDraw.Draw(image)

        accent = ImageColor.getrgb(self._accent_color(payload))
        panel = ImageColor.getrgb(self._secondary_color(payload))
        panel_dark = tuple(max(0, channel - 34) for channel in accent)
        text_dark = (27, 27, 27)
        text_light = (248, 246, 242)

        outer = (40, 40, size[0] - 40, size[1] - 40)
        draw.rounded_rectangle(outer, radius=36, fill=panel)

        spotlight = (72, 72, size[0] - 72, int(size[1] * 0.32))
        draw.rounded_rectangle(spotlight, radius=28, fill=accent)
        draw.rounded_rectangle(
            (spotlight[0], spotlight[1], spotlight[2], spotlight[1] + 92),
            radius=28,
            fill=panel_dark,
        )

        device_box = (int(size[0] * 0.18), int(size[1] * 0.4), int(size[0] * 0.82), int(size[1] * 0.8))
        screen_box = (device_box[0] + 18, device_box[1] + 18, device_box[2] - 18, device_box[3] - 18)
        draw.rounded_rectangle(device_box, radius=32, fill=(72, 72, 72))
        draw.rounded_rectangle(screen_box, radius=24, fill=(245, 247, 250))

        card_y = screen_box[1] + 34
        chip_font = self._font(max(18, int(size[1] * 0.018)), bold=True)
        label_font = self._font(max(20, int(size[1] * 0.02)))
        brand_font = self._font(max(26, int(size[1] * 0.026)), bold=True)

        draw.text((spotlight[0] + 28, spotlight[1] + 24), payload.brand_name.upper(), font=brand_font, fill=text_light)
        self._draw_chip(draw, (spotlight[0] + 28, spotlight[1] + 118), self._fit_line(concept.angle_name, 24), chip_font, text_light, panel_dark)
        self._draw_chip(draw, (spotlight[0] + 28, spotlight[1] + 174), self._fit_line(self._value_phrase(payload), 28), chip_font, text_light, panel_dark)

        ui_cards = [
            ("Hooks", accent),
            ("Copy", (98, 126, 234)),
            ("Creative", (49, 163, 118)),
        ]
        cursor_x = screen_box[0] + 26
        for label, fill in ui_cards:
            box = (cursor_x, card_y, cursor_x + 150, card_y + 84)
            draw.rounded_rectangle(box, radius=18, fill=fill)
            draw.text((box[0] + 18, box[1] + 26), label, font=chip_font, fill=text_light)
            cursor_x += 168

        feature_box = (screen_box[0] + 26, card_y + 120, screen_box[2] - 26, card_y + 260)
        draw.rounded_rectangle(feature_box, radius=20, fill=(230, 234, 240))
        draw.text((feature_box[0] + 20, feature_box[1] + 18), self._fit_line(payload.product_description.split(".")[0], 42), font=label_font, fill=text_dark)
        draw.text((feature_box[0] + 20, feature_box[1] + 62), self._fit_line(concept.scene_description, 54), font=label_font, fill=(74, 82, 96))

        badge_box = (screen_box[0] + 26, screen_box[3] - 110, screen_box[0] + 220, screen_box[3] - 44)
        draw.rounded_rectangle(badge_box, radius=22, fill=accent)
        draw.text((badge_box[0] + 18, badge_box[1] + 18), "Creative System", font=chip_font, fill=text_light)

        image_data_url = self._to_data_url(image)
        error_note = previous.error if previous and previous.error else "Local image fallback used."
        return GeneratedCreative(
            concept_id=concept.concept_id,
            provider="local-fallback",
            provider_api_version="v1",
            status=CreativeStatus.GENERATED,
            prompt=concept.generation_prompt,
            image_urls=[image_data_url],
            video_urls=[],
            error=error_note,
            raw_response={"fallback": True},
        )

    @staticmethod
    def _to_data_url(image: Image.Image) -> str:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/png;base64,{encoded}"

    def _draw_chip(self, draw: ImageDraw.ImageDraw, origin: tuple[int, int], text: str, font, text_color, fill_color) -> None:
        font_size = getattr(font, "size", 18)
        width = max(120, (len(text) * max(10, font_size // 2)) + 38)
        box = (origin[0], origin[1], origin[0] + width, origin[1] + 42)
        draw.rounded_rectangle(box, radius=18, fill=fill_color)
        draw.text((box[0] + 16, box[1] + 10), text, font=font, fill=text_color)

    @staticmethod
    def _font(size: int, bold: bool = False):
        candidates = [
            "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        ]
        for candidate in candidates:
            try:
                return ImageFont.truetype(candidate, size=size)
            except OSError:
                continue
        return ImageFont.load_default()

    @staticmethod
    def _fit_line(text: str, max_chars: int) -> str:
        compact = " ".join(text.split())
        if len(compact) <= max_chars:
            return compact
        words = compact.split()
        line: list[str] = []
        for word in words:
            candidate = " ".join([*line, word]).strip()
            if len(candidate) <= max_chars:
                line.append(word)
            else:
                break
        return " ".join(line).rstrip(" ,.;:") + "..."

    @staticmethod
    def _safe_color(color_str: str, default: str) -> str:
        try:
            ImageColor.getrgb(color_str)
            return color_str
        except ValueError:
            return default

    @staticmethod
    def _primary_color(payload: CreativeInput) -> str:
        if payload.brand_colors:
            return LocalImageFallbackService._safe_color(payload.brand_colors[0], "#1F1A17")
        return "#1F1A17"

    @staticmethod
    def _secondary_color(payload: CreativeInput) -> str:
        if len(payload.brand_colors) > 1:
            return LocalImageFallbackService._safe_color(payload.brand_colors[1], "#FFF7EF")
        return "#FFF7EF"

    @staticmethod
    def _accent_color(payload: CreativeInput) -> str:
        if len(payload.brand_colors) > 2:
            return LocalImageFallbackService._safe_color(payload.brand_colors[2], "#D0612A")
        return "#D0612A"

    @staticmethod
    def _value_phrase(payload: CreativeInput) -> str:
        for benefit in payload.key_benefits:
            normalized = benefit.strip()
            if normalized and normalized.lower() not in {"cheap", "fast", "faster", "better", "affordable"}:
                return normalized
        sentence = payload.product_description.split(".")[0].strip()
        return sentence or "Launch-ready ad production"
