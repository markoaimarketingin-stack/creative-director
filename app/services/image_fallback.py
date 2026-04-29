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
        text_dark = (24, 22, 19)
        text_light = (250, 245, 239)

        draw.rounded_rectangle((48, 48, size[0] - 48, size[1] - 48), radius=36, fill=panel)
        draw.rounded_rectangle((64, 64, size[0] - 64, int(size[1] * 0.28)), radius=28, fill=accent)

        title_font = self._font(max(34, int(size[1] * 0.04)))
        body_font = self._font(max(22, int(size[1] * 0.022)))
        brand_font = self._font(max(26, int(size[1] * 0.026)), bold=True)

        draw.text((88, 84), payload.brand_name.upper(), font=brand_font, fill=text_light)
        draw.text((88, 140), self._fit_line(concept.hook_text, 56), font=title_font, fill=text_light)

        body_top = int(size[1] * 0.36)
        body_lines = [
            self._fit_line(concept.angle_name, 36),
            self._fit_line(payload.key_benefits[0] if payload.key_benefits else payload.product_description, 58),
            self._fit_line(concept.scene_description, 64),
        ]
        for index, line in enumerate(body_lines):
            draw.text((88, body_top + (index * 54)), line, font=body_font, fill=text_dark)

        cta_box = (88, size[1] - 148, 340, size[1] - 84)
        draw.rounded_rectangle(cta_box, radius=22, fill=accent)
        draw.text((cta_box[0] + 28, cta_box[1] + 14), "Generate Ads", font=body_font, fill=text_light)

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
    def _primary_color(payload: CreativeInput) -> str:
        return payload.brand_colors[0] if payload.brand_colors else "#1F1A17"

    @staticmethod
    def _secondary_color(payload: CreativeInput) -> str:
        return payload.brand_colors[1] if len(payload.brand_colors) > 1 else "#FFF7EF"

    @staticmethod
    def _accent_color(payload: CreativeInput) -> str:
        return payload.brand_colors[2] if len(payload.brand_colors) > 2 else "#D0612A"
