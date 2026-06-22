"""
Composes final creative PNGs from product images + campaign data.
Delegates layout/composition to the template layer in creative_templates.py.
One final.png is produced per product per aspect ratio.
"""

import logging
import os

from PIL import Image

from src.config import ASPECT_RATIOS, OUTPUT_FOLDER
from src.creative_templates import auto_select_template, get_template
from src.utils import safe_folder_name

logger = logging.getLogger(__name__)


class CreativeBuilder:
    def __init__(
        self,
        output_folder: str = OUTPUT_FOLDER,
        template: str | None = None,   # None → auto-select per product
    ):
        self.output_folder = output_folder
        self._template_override = template

    def build(
        self,
        product_name: str,
        product_image: Image.Image,
        campaign_message: str,
        region: str,
        brand_primary: str = "#1E293B",
        brand_secondary: str = "#F8FAFC",
        brand_name: str = "",
    ) -> dict[str, str]:
        """
        Render final creatives for all three aspect ratios.
        Returns dict mapping ratio_key → absolute output path.
        """
        if self._template_override:
            tmpl = get_template(self._template_override)
        else:
            tmpl = auto_select_template(product_name, brand_primary)

        logger.info(
            "Building creatives for '%s' using template '%s'",
            product_name, tmpl.name,
        )

        results: dict[str, str] = {}
        folder = safe_folder_name(product_name)

        for ratio_key, (w, h) in ASPECT_RATIOS.items():
            out_dir  = os.path.join(self.output_folder, folder, ratio_key)
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, "final.png")

            try:
                creative = tmpl.compose(
                    ratio_key       = ratio_key,
                    canvas_w        = w,
                    canvas_h        = h,
                    product_image   = product_image,
                    campaign_message = campaign_message,
                    product_name    = product_name,
                    region          = region,
                    brand_name      = brand_name,
                    brand_primary   = brand_primary,
                    brand_secondary = brand_secondary,
                )
            except Exception:
                logger.exception(
                    "Template '%s' failed for ratio '%s' — using safe fallback.",
                    tmpl.name, ratio_key,
                )
                from src.creative_templates import PremiumTemplate
                creative = PremiumTemplate().compose(
                    ratio_key       = ratio_key,
                    canvas_w        = w,
                    canvas_h        = h,
                    product_image   = product_image,
                    campaign_message = campaign_message,
                    product_name    = product_name,
                    region          = region,
                    brand_name      = brand_name,
                    brand_primary   = brand_primary,
                    brand_secondary = brand_secondary,
                )

            creative.save(out_path, "PNG", optimize=False)
            logger.info("  → %s [%dx%d]", ratio_key, w, h)
            results[ratio_key] = out_path

        return results
