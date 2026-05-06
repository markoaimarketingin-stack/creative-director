from __future__ import annotations

import json
import zipfile
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageFont

from app.models import CreativeAsset


class CreativeDownloadArtifactExporter:
    def export(self, *, asset: CreativeAsset, campaign_dir: Path) -> tuple[Path, Path]:
        export_dir = campaign_dir / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)

        assets_zip_path = export_dir / f"{asset.concept_id}-assets.zip"
        mockup_pdf_path = export_dir / f"{asset.concept_id}-mockup.pdf"

        self._write_assets_bundle(asset=asset, campaign_dir=campaign_dir, output_path=assets_zip_path)
        self._write_mockup_pdf(asset=asset, campaign_dir=campaign_dir, output_path=mockup_pdf_path)

        return assets_zip_path, mockup_pdf_path

    def _write_assets_bundle(self, *, asset: CreativeAsset, campaign_dir: Path, output_path: Path) -> None:
        manifest = asset.model_dump(mode="json")
        rendered_path = self._resolve_source_path(asset.rendered_ad.image_path if asset.rendered_ad else None, campaign_dir)
        preview_path = self._resolve_source_path(asset.preview.image_path if asset.preview else None, campaign_dir)

        with zipfile.ZipFile(output_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            if rendered_path and rendered_path.exists():
                archive.write(rendered_path, arcname=f"{asset.concept_id}-rendered{rendered_path.suffix or '.png'}")
            if preview_path and preview_path.exists():
                archive.write(preview_path, arcname=f"{asset.concept_id}-preview{preview_path.suffix or '.png'}")
            archive.writestr(f"{asset.concept_id}-creative.json", json.dumps(manifest, indent=2, ensure_ascii=True))

    def _write_mockup_pdf(self, *, asset: CreativeAsset, campaign_dir: Path, output_path: Path) -> None:
        canvas = Image.new("RGB", (1600, 2200), ImageColor.getrgb("#F6F3ED"))
        draw = ImageDraw.Draw(canvas)

        header_font = self._font(52)
        title_font = self._font(34)
        label_font = self._font(22)
        body_font = self._font(24)
        small_font = self._font(20)

        left_margin = 64
        right_col_x = 1060

        draw.text((left_margin, 52), asset.campaign_name, font=header_font, fill=ImageColor.getrgb("#111111"))
        draw.text((left_margin, 118), f"Concept {asset.concept_id}", font=label_font, fill=ImageColor.getrgb("#667085"))
        draw.rounded_rectangle((left_margin, 168, 420, 224), radius=28, fill=ImageColor.getrgb("#111111"))
        draw.text((94, 183), "Ad mockup PDF", font=label_font, fill=ImageColor.getrgb("#FFFFFF"))

        image = self._load_preview_image(asset=asset, campaign_dir=campaign_dir)
        image.thumbnail((920, 1320), Image.Resampling.LANCZOS)
        image_box = (left_margin, 276, left_margin + 940, 276 + 1360)
        draw.rounded_rectangle(image_box, radius=36, fill=ImageColor.getrgb("#FFFFFF"), outline=ImageColor.getrgb("#E4E7EC"), width=2)
        image_x = left_margin + ((image_box[2] - image_box[0]) - image.width) // 2
        image_y = 306 + ((image_box[3] - image_box[1]) - image.height) // 2
        canvas.paste(image, (image_x, image_y), image if image.mode in {"RGBA", "LA"} else None)

        self._draw_info_card(
            draw=draw,
            x=right_col_x,
            y=276,
            width=476,
            title="Visual confidence",
            value=f"{asset.score.total_score}%",
            subtitle=asset.visual_concept.scene_description,
            title_font=title_font,
            value_font=header_font,
            body_font=body_font,
        )

        cards = [
            ("Best hook", asset.hook_text or "-"),
            ("Best angle", asset.angle_name or "-"),
            ("Headline", asset.headline or "-"),
            ("CTA", asset.cta or "-"),
            ("Primary text", asset.primary_text or "-"),
        ]

        cursor_y = 560
        for label, value in cards:
            card_height = 188 if label == "Primary text" else 138
            self._draw_text_card(
                draw=draw,
                x=right_col_x,
                y=cursor_y,
                width=476,
                height=card_height,
                label=label,
                value=value,
                label_font=label_font,
                body_font=body_font,
            )
            cursor_y += card_height + 18

        footer_text = f"Generated from {asset.generated_creative.provider} | Status: {asset.generated_creative.status}"
        draw.text((left_margin, 1980), footer_text, font=small_font, fill=ImageColor.getrgb("#667085"))

        canvas.save(output_path, format="PDF", resolution=144.0)

    def _draw_info_card(
        self,
        *,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        width: int,
        title: str,
        value: str,
        subtitle: str,
        title_font,
        value_font,
        body_font,
    ) -> None:
        card_box = (x, y, x + width, y + 240)
        draw.rounded_rectangle(card_box, radius=30, fill=ImageColor.getrgb("#FFFFFF"), outline=ImageColor.getrgb("#E4E7EC"), width=2)
        draw.text((x + 22, y + 18), title, font=title_font, fill=ImageColor.getrgb("#667085"))
        draw.text((x + 22, y + 60), value, font=value_font, fill=ImageColor.getrgb("#111111"))
        wrapped = self._wrap_text(draw, subtitle, body_font, width - 44, max_lines=4)
        cursor_y = y + 150
        for line in wrapped:
            draw.text((x + 22, cursor_y), line, font=body_font, fill=ImageColor.getrgb("#344054"))
            cursor_y += self._line_height(body_font) + 2

    def _draw_text_card(
        self,
        *,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        width: int,
        height: int,
        label: str,
        value: str,
        label_font,
        body_font,
    ) -> None:
        draw.rounded_rectangle((x, y, x + width, y + height), radius=24, fill=ImageColor.getrgb("#FFFFFF"), outline=ImageColor.getrgb("#E4E7EC"), width=2)
        draw.text((x + 20, y + 16), label.upper(), font=label_font, fill=ImageColor.getrgb("#667085"))
        lines = self._wrap_text(draw, value, body_font, width - 40, max_lines=4 if label == "Primary text" else 3)
        cursor_y = y + 52
        for line in lines:
            draw.text((x + 20, cursor_y), line, font=body_font, fill=ImageColor.getrgb("#111111"))
            cursor_y += self._line_height(body_font) + 4

    def _load_preview_image(self, *, asset: CreativeAsset, campaign_dir: Path) -> Image.Image:
        candidates = []
        if asset.preview and asset.preview.image_path:
            candidates.append(asset.preview.image_path)
        if asset.rendered_ad and asset.rendered_ad.image_path:
            candidates.append(asset.rendered_ad.image_path)

        for candidate in candidates:
            path = self._resolve_source_path(candidate, campaign_dir)
            if path and path.exists():
                return Image.open(path).convert("RGB")

        placeholder = Image.new("RGB", (1080, 1350), ImageColor.getrgb("#F2F4F7"))
        placeholder_draw = ImageDraw.Draw(placeholder)
        font = self._font(36)
        placeholder_draw.text((60, 60), "Preview unavailable", font=font, fill=ImageColor.getrgb("#667085"))
        return placeholder

    def _resolve_source_path(self, raw_path: str | None, campaign_dir: Path) -> Path | None:
        if not raw_path:
            return None

        path = Path(raw_path)
        if path.exists():
            return path

        normalized = raw_path.replace("\\", "/")
        output_root = campaign_dir.parent.parent
        if "/output/" in normalized:
            relative = normalized.split("/output/", 1)[1]
            return output_root / relative
        if normalized.startswith("output/"):
            return output_root / normalized.removeprefix("output/")
        return path

    @staticmethod
    def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        for candidate in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"):
            try:
                return ImageFont.truetype(candidate, size=size)
            except OSError:
                continue
        return ImageFont.load_default()

    @staticmethod
    def _wrap_text(
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        max_width: int,
        max_lines: int,
    ) -> list[str]:
        words = " ".join(text.split()).split()
        if not words:
            return [""]

        lines: list[str] = []
        current: list[str] = []
        for word in words:
            candidate = " ".join([*current, word]).strip()
            if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
                current.append(word)
                continue

            if current:
                lines.append(" ".join(current))
            current = [word]
            if len(lines) == max_lines - 1:
                break

        if current and len(lines) < max_lines:
            lines.append(" ".join(current))

        return lines[:max_lines]

    @staticmethod
    def _line_height(font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> int:
        bbox = font.getbbox("Ag")
        return (bbox[3] - bbox[1]) if bbox else 24