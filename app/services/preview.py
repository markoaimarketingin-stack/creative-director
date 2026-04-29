from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageFont

from app.models import AdPreview, CreativeAsset, Platform


class AdPreviewGenerator:
    def generate(self, *, asset: CreativeAsset, campaign_dir: Path) -> AdPreview:
        layout_size = self._layout_size(asset.platform)
        preview = Image.new("RGBA", layout_size, ImageColor.getrgb("#EEF2F6"))
        draw = ImageDraw.Draw(preview, "RGBA")

        card_margin = 32
        card_box = (card_margin, 24, layout_size[0] - card_margin, layout_size[1] - 24)
        draw.rounded_rectangle(card_box, radius=28, fill=(255, 255, 255, 255))

        font_title = self._font(26)
        font_body = self._font(22)
        font_meta = self._font(18)
        label = "Sponsored" if asset.platform in {Platform.META, Platform.TIKTOK} else "Ad"

        draw.ellipse((56, 48, 108, 100), fill=(17, 17, 17, 255))
        draw.text((124, 52), asset.campaign_name, font=font_title, fill=(17, 17, 17, 255))
        draw.text((124, 84), label, font=font_meta, fill=(88, 98, 112, 255))

        image = Image.open(asset.rendered_ad.image_path).convert("RGBA")
        image.thumbnail((layout_size[0] - 96, int(layout_size[1] * 0.58)), Image.Resampling.LANCZOS)
        image_x = (layout_size[0] - image.width) // 2
        image_y = 132
        preview.alpha_composite(image, dest=(image_x, image_y))

        copy_y = image_y + image.height + 24
        body = (asset.primary_text or "")[:180]
        draw.text((56, copy_y), body, font=font_body, fill=(17, 17, 17, 255))
        draw.text((56, copy_y + 44), asset.headline or "", font=font_title, fill=(17, 17, 17, 255))

        preview_dir = campaign_dir / "previews"
        preview_dir.mkdir(parents=True, exist_ok=True)
        output_path = preview_dir / f"{asset.concept_id}-{asset.platform.value}.png"
        preview.save(output_path, format="PNG", optimize=True)

        return AdPreview(
            concept_id=asset.concept_id,
            platform=asset.platform,
            image_path=str(output_path),
            width=layout_size[0],
            height=layout_size[1],
        )

    @staticmethod
    def _layout_size(platform: Platform) -> tuple[int, int]:
        if platform == Platform.TIKTOK:
            return (1242, 2208)
        if platform == Platform.GOOGLE:
            return (1400, 1200)
        return (1242, 1660)

    @staticmethod
    def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        for candidate in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"):
            try:
                return ImageFont.truetype(candidate, size=size)
            except OSError:
                continue
        return ImageFont.load_default()
