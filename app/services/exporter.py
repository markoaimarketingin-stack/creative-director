import csv
from pathlib import Path

from app.models import CreativeAsset, ExportRow


class MetaAdsCsvExporter:
    HEADERS = [
        "Campaign Name",
        "Ad Set Name",
        "Ad Name",
        "Primary Text",
        "Headline",
        "Description",
        "Call To Action",
        "Image Path",
        "Preview Path",
    ]

    def export(self, *, assets: list[CreativeAsset], campaign_dir: Path) -> list[ExportRow]:
        rows = [self._to_row(asset) for asset in assets if asset.rendered_ad]
        export_dir = campaign_dir / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        csv_path = export_dir / "meta_ads_bulk_upload.csv"

        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(self.HEADERS)
            for row in rows:
                writer.writerow(
                    [
                        row.campaign_name,
                        row.ad_set_name,
                        row.ad_name,
                        row.primary_text,
                        row.headline,
                        row.description,
                        row.cta,
                        row.image_path,
                        row.preview_path or "",
                    ]
                )

        return rows

    @staticmethod
    def _to_row(asset: CreativeAsset) -> ExportRow:
        return ExportRow(
            campaign_name=asset.campaign_name,
            ad_set_name=f"{asset.campaign_name} - {asset.angle_name}",
            ad_name=f"{asset.campaign_name} - {asset.concept_id}",
            platform=asset.platform,
            primary_text=asset.primary_text or "",
            headline=asset.headline or "",
            description=asset.description or "",
            cta=asset.cta or "",
            image_path=asset.rendered_ad.image_path if asset.rendered_ad else "",
            preview_path=asset.preview.image_path if asset.preview else None,
        )
