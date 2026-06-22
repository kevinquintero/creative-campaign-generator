"""
Creative Templates
Each template produces polished ad compositions for all three aspect ratios.
Templates share the DesignSystem drawing primitives — no hardcoded pixel values.
"""

import hashlib
import textwrap
from abc import ABC, abstractmethod

from PIL import Image, ImageDraw, ImageFilter

from src.design_system import (
    Palette, Spacing, TypeScale,
    build_palette, build_spacing, build_type_scale,
    cover_crop, vignette, gradient_overlay, solid_panel,
    font, measure_text, wrap_to_width, fit_font,
    draw_shadow_text, draw_cta, draw_badge, draw_separator_line,
)


# ── Base template ─────────────────────────────────────────────────────────────

class BaseTemplate(ABC):
    name: str = "base"

    def compose(
        self,
        ratio_key: str,         # "1x1" | "9x16" | "16x9"
        canvas_w: int,
        canvas_h: int,
        product_image: Image.Image,
        campaign_message: str,
        product_name: str,
        region: str,
        brand_name: str,
        brand_primary: str,
        brand_secondary: str,
    ) -> Image.Image:
        pal  = build_palette(brand_primary, brand_secondary)
        spc  = build_spacing(canvas_w, canvas_h)
        typ  = build_type_scale(canvas_w, canvas_h)

        if ratio_key == "1x1":
            return self._square(canvas_w, canvas_h, product_image, campaign_message,
                                product_name, region, brand_name, pal, spc, typ)
        elif ratio_key == "9x16":
            return self._story(canvas_w, canvas_h, product_image, campaign_message,
                               product_name, region, brand_name, pal, spc, typ)
        else:  # 16x9
            return self._landscape(canvas_w, canvas_h, product_image, campaign_message,
                                   product_name, region, brand_name, pal, spc, typ)

    @abstractmethod
    def _square(self, w, h, img, msg, product, region, brand, pal, spc, typ) -> Image.Image: ...
    @abstractmethod
    def _story(self, w, h, img, msg, product, region, brand, pal, spc, typ) -> Image.Image: ...
    @abstractmethod
    def _landscape(self, w, h, img, msg, product, region, brand, pal, spc, typ) -> Image.Image: ...

    # ── Shared helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _safe_text(text: str, max_len: int = 60) -> str:
        return text[:max_len].strip() if text else ""

    @staticmethod
    def _shorten(text: str, words: int = 7) -> str:
        parts = text.split()
        if len(parts) <= words:
            return text
        return " ".join(parts[:words]) + "…"

    @staticmethod
    def _draw_headline(draw, cx, y, text, style, start_size, max_w, max_h,
                       color, shadow=True, align="center"):
        """Draw wrapped headline, returns bottom y."""
        fnt, wrapped = fit_font(draw, text, style, start_size, max_w, max_h, max_lines=3)
        lines = wrapped.split("\n")
        _, lh = measure_text(draw, "Ag", fnt)
        line_gap = max(4, lh // 6)
        total_h = len(lines) * lh + (len(lines) - 1) * line_gap
        cur_y = y

        for line in lines:
            lw, _ = measure_text(draw, line, fnt)
            if align == "center":
                lx = cx - lw // 2
            elif align == "right":
                lx = cx - lw
            else:
                lx = cx

            if shadow:
                draw_shadow_text(draw, (lx, cur_y), line, fnt, fill=color,
                                 shadow_color=(0, 0, 0, 120), offset=3)
            else:
                draw.text((lx, cur_y), line, font=fnt, fill=color)
            cur_y += lh + line_gap

        return cur_y  # bottom y of the block


# ── Premium template ──────────────────────────────────────────────────────────

class PremiumTemplate(BaseTemplate):
    """
    Full-bleed product image with gradient overlay, Apple/Nike-style.
    Dark, moody, premium feel.
    """
    name = "premium"

    def _square(self, w, h, img, msg, product, region, brand, pal, spc, typ):
        # Full-bleed image covers entire canvas
        canvas = cover_crop(img, w, h, focus_y=0.42)

        # Vignette — subtle edge darkening
        canvas = vignette(canvas, strength=0.45)

        # Bottom gradient — brand deep, starting at 40%
        canvas = gradient_overlay(canvas, pal.brand_deep,
                                  direction="bottom", start_pct=0.40,
                                  max_alpha=215, curve=0.68)

        # Top gradient — subtle dark for text legibility
        canvas = gradient_overlay(canvas, (0, 0, 0),
                                  direction="top", start_pct=0.82,
                                  max_alpha=80, curve=0.55)

        draw = ImageDraw.Draw(canvas)
        mx = spc.margin

        # Brand name — top left
        if brand:
            brand_fnt = font("light", typ.micro)
            draw.text((mx, mx), brand.upper(), font=brand_fnt, fill=(*pal.subtext, 210))

        # Region badge — top right
        if region:
            badge_fnt = font("regular", typ.micro)
            draw_badge(draw, w - mx, mx, region, badge_fnt,
                       bg=(0, 0, 0, 130), fg=pal.badge_text,
                       align="right", corner=max(8, spc.xs))

        # Text zone: 54% → 90% height
        text_top    = int(h * 0.54)
        text_bottom = int(h * 0.90)
        text_zone_h = text_bottom - text_top
        text_cx     = w // 2
        text_w      = int(w * 0.84)

        # Headline
        headline = self._shorten(msg, words=8)
        bottom_y = self._draw_headline(
            draw, text_cx, text_top, headline,
            "black", typ.display, text_w, int(text_zone_h * 0.55),
            pal.headline,
        )

        bottom_y += spc.sm

        # Product name
        prod_fnt = font("light", typ.body)
        pw, _ = measure_text(draw, product, prod_fnt)
        draw.text((text_cx - pw // 2, bottom_y), product, font=prod_fnt,
                  fill=(*pal.subtext, 220))
        bottom_y += measure_text(draw, product, prod_fnt)[1] + spc.md

        # CTA button
        cta_fnt = font("bold", typ.cta)
        cta_bottom = draw_cta(draw, text_cx, bottom_y, "Shop Now",
                              cta_fnt, pal.cta, pal.cta_text,
                              pad_x=spc.lg, pad_y=spc.sm)

        return canvas

    def _story(self, w, h, img, msg, product, region, brand, pal, spc, typ):
        # Product image: upper 62%
        img_h = int(h * 0.62)
        prod_crop = cover_crop(img, w, img_h, focus_y=0.40)

        # Lower panel: brand deep color
        canvas = Image.new("RGB", (w, h), pal.brand_deep)
        canvas.paste(prod_crop, (0, 0))

        # Blend gradient between image and panel
        canvas = gradient_overlay(canvas, pal.brand_deep,
                                  direction="bottom", start_pct=0.45,
                                  max_alpha=255, curve=0.60)
        canvas = gradient_overlay(canvas, (0, 0, 0),
                                  direction="top", start_pct=0.88,
                                  max_alpha=60, curve=0.50)

        draw = ImageDraw.Draw(canvas)
        mx = spc.margin

        # Brand name — top left over image
        if brand:
            brand_fnt = font("light", typ.micro)
            draw.text((mx, mx), brand.upper(), font=brand_fnt, fill=(*pal.subtext, 190))

        # Region — top right
        if region:
            badge_fnt = font("regular", typ.micro)
            draw_badge(draw, w - mx, mx, region, badge_fnt,
                       bg=(0, 0, 0, 120), fg=pal.badge_text,
                       align="right", corner=max(6, spc.xs))

        # Text zone: 64% → 93% height
        text_top = int(h * 0.64)
        text_cx  = w // 2
        text_w   = int(w * 0.86)
        avail_h  = int(h * 0.93) - text_top

        # Headline
        headline = self._shorten(msg, words=9)
        bottom_y = self._draw_headline(
            draw, text_cx, text_top, headline,
            "black", typ.h1, text_w, int(avail_h * 0.48),
            pal.headline,
        )
        bottom_y += spc.sm

        # Thin separator line
        draw_separator_line(draw, mx, bottom_y, w - 2 * mx,
                            pal.brand_light, vertical=False)
        bottom_y += spc.md

        # Product name
        prod_fnt = font("light", typ.body)
        pw, ph = measure_text(draw, product, prod_fnt)
        draw.text((text_cx - pw // 2, bottom_y), product, font=prod_fnt,
                  fill=(*pal.subtext, 220))
        bottom_y += ph + spc.lg

        # CTA
        cta_fnt = font("bold", typ.cta)
        draw_cta(draw, text_cx, bottom_y, "Shop Now",
                 cta_fnt, pal.cta, pal.cta_text,
                 pad_x=int(spc.xl * 1.2), pad_y=spc.sm)

        # Brand lockup at very bottom
        if brand:
            lock_fnt = font("light", typ.micro)
            lw, lh = measure_text(draw, brand.upper(), lock_fnt)
            draw.text((text_cx - lw // 2, h - spc.vpad - lh),
                      brand.upper(), font=lock_fnt, fill=(*pal.subtext, 160))

        return canvas

    def _landscape(self, w, h, img, msg, product, region, brand, pal, spc, typ):
        # Left 56%: product image (full-height bleed)
        img_w = int(w * 0.56)
        prod_crop = cover_crop(img, img_w, h, focus_y=0.45)

        canvas = Image.new("RGB", (w, h), pal.brand_deep)
        canvas.paste(prod_crop, (0, 0))

        # Horizontal gradient blending image into right panel
        canvas = solid_panel(canvas, pal.brand_deep, side="right",
                             split=0.44, blend_px=max(60, int(w * 0.05)))

        # Subtle top/bottom gradients
        canvas = gradient_overlay(canvas, (0, 0, 0),
                                  direction="top", start_pct=0.90, max_alpha=50)
        canvas = gradient_overlay(canvas, (0, 0, 0),
                                  direction="bottom", start_pct=0.88, max_alpha=50)

        draw = ImageDraw.Draw(canvas)

        # Right panel text block
        panel_x  = int(w * 0.56) + spc.margin
        panel_w  = w - panel_x - spc.margin
        panel_cx = panel_x + panel_w // 2

        # Vertical center of the right panel
        vcenter = h // 2

        # Brand name — above headline
        if brand:
            brand_fnt = font("light", typ.small)
            bw, bh = measure_text(draw, brand.upper(), brand_fnt)
            brand_y = vcenter - int(h * 0.28)
            draw.text((panel_x, brand_y), brand.upper(), font=brand_fnt,
                      fill=(*pal.subtext, 190))
            # Small accent line under brand
            draw_separator_line(draw, panel_x, brand_y + bh + spc.sm,
                                spc.xl, pal.cta, vertical=False)
            headline_y = brand_y + bh + spc.md + spc.sm
        else:
            headline_y = vcenter - int(h * 0.26)

        # Headline
        headline = self._shorten(msg, words=7)
        bottom_y = self._draw_headline(
            draw, panel_x, headline_y, headline,
            "black", typ.h1, panel_w, int(h * 0.36),
            pal.headline, align="left",
        )
        bottom_y += spc.md

        # Product name
        prod_fnt = font("light", typ.body)
        draw.text((panel_x, bottom_y), product, font=prod_fnt,
                  fill=(*pal.subtext, 215))
        bottom_y += measure_text(draw, product, prod_fnt)[1] + spc.lg

        # CTA — left-aligned
        cta_fnt = font("bold", typ.cta)
        draw_cta(draw, panel_x + spc.xl, bottom_y, "Shop Now",
                 cta_fnt, pal.cta, pal.cta_text,
                 pad_x=spc.lg, pad_y=spc.sm)

        # Region badge — top right
        if region:
            badge_fnt = font("regular", typ.micro)
            draw_badge(draw, w - spc.margin, spc.margin, region, badge_fnt,
                       bg=(0, 0, 0, 120), fg=pal.badge_text,
                       align="right", corner=max(6, spc.xs))

        return canvas


# ── Minimal template ──────────────────────────────────────────────────────────

class MinimalTemplate(BaseTemplate):
    """
    Light background, editorial feel. Notion/Linear/Vercel aesthetic.
    """
    name = "minimal"

    def _bg_color(self, pal: Palette) -> tuple:
        from src.design_system import lighten, luminance
        if luminance(pal.brand) > 0.7:
            return (245, 245, 248)
        return lighten(pal.brand_deep, 0.70) if pal.is_dark_brand else (244, 245, 247)

    def _square(self, w, h, img, msg, product, region, brand, pal, spc, typ):
        from src.design_system import darken, luminance, text_on

        bg = self._bg_color(pal)
        canvas = Image.new("RGB", (w, h), bg)
        draw = ImageDraw.Draw(canvas)
        mx = spc.margin

        # Product image — top 58%, centered with breathing room
        img_region_h = int(h * 0.56)
        img_region_w = int(w * 0.78)
        # fit-contain within the region
        prod = img.convert("RGB")
        prod.thumbnail((img_region_w, img_region_h), Image.LANCZOS)
        px = (w - prod.width) // 2
        py = mx
        canvas.paste(prod, (px, py))

        # Thin horizontal rule
        rule_y = img_region_h + mx
        draw_separator_line(draw, mx, rule_y, w - 2 * mx, pal.brand, vertical=False)

        text_top = rule_y + spc.md
        text_w   = int(w * 0.82)
        text_cx  = w // 2
        text_col = text_on(bg)

        # Headline
        headline = self._shorten(msg, words=7)
        bottom_y = self._draw_headline(
            draw, text_cx, text_top, headline,
            "bold", typ.h2, text_w, int(h * 0.20),
            text_col, shadow=False,
        )
        bottom_y += spc.sm

        # Product name — muted
        prod_fnt = font("regular", typ.small)
        pw, ph = measure_text(draw, product, prod_fnt)
        draw.text((text_cx - pw // 2, bottom_y), product, font=prod_fnt,
                  fill=(*pal.brand, 200))
        bottom_y += ph + spc.md

        # CTA — outlined style for minimal
        cta_fnt = font("bold", typ.cta)
        draw_cta(draw, text_cx, bottom_y, "Shop Now",
                 cta_fnt, pal.brand, text_on(pal.brand),
                 pad_x=spc.lg, pad_y=spc.sm)

        # Brand + region footer
        foot_fnt = font("light", typ.micro)
        foot_y = h - spc.vpad
        if brand:
            bw, bh = measure_text(draw, brand, foot_fnt)
            draw.text((mx, foot_y - bh), brand, font=foot_fnt,
                      fill=(*text_on(bg), 130))
        if region:
            rw, rh = measure_text(draw, region, foot_fnt)
            draw.text((w - mx - rw, foot_y - rh), region, font=foot_fnt,
                      fill=(*text_on(bg), 130))

        return canvas

    def _story(self, w, h, img, msg, product, region, brand, pal, spc, typ):
        from src.design_system import text_on

        bg = self._bg_color(pal)
        canvas = Image.new("RGB", (w, h), bg)
        draw = ImageDraw.Draw(canvas)
        mx = spc.margin

        # Image: upper 55%, slight horizontal padding for editorial look
        img_region_h = int(h * 0.52)
        prod = cover_crop(img, w, img_region_h, focus_y=0.45)
        canvas.paste(prod, (0, 0))

        # Very light bottom fade into bg
        canvas = gradient_overlay(canvas, bg, direction="bottom",
                                  start_pct=0.48, max_alpha=230, curve=0.65)

        draw = ImageDraw.Draw(canvas)
        text_col = text_on(bg)
        text_cx  = w // 2
        text_top = int(h * 0.56)
        text_w   = int(w * 0.82)

        # Headline
        headline = self._shorten(msg, words=9)
        bottom_y = self._draw_headline(
            draw, text_cx, text_top, headline,
            "bold", typ.h1, text_w, int(h * 0.22),
            text_col, shadow=False,
        )
        bottom_y += spc.sm

        # Accent line
        draw_separator_line(draw, mx, bottom_y, spc.xl * 2, pal.brand, vertical=False)
        bottom_y += spc.md

        # Product
        prod_fnt = font("regular", typ.body)
        pw, ph = measure_text(draw, product, prod_fnt)
        draw.text((text_cx - pw // 2, bottom_y), product, font=prod_fnt,
                  fill=(*pal.brand, 220))
        bottom_y += ph + spc.lg

        # CTA
        cta_fnt = font("bold", typ.cta)
        draw_cta(draw, text_cx, bottom_y, "Shop Now",
                 cta_fnt, pal.brand, text_on(pal.brand),
                 pad_x=int(spc.xl * 1.1), pad_y=spc.sm)

        # Footer
        foot_fnt = font("light", typ.micro)
        if brand:
            bw, bh = measure_text(draw, brand, foot_fnt)
            draw.text((text_cx - bw // 2, h - spc.vpad - bh), brand, font=foot_fnt,
                      fill=(*text_col, 110))

        return canvas

    def _landscape(self, w, h, img, msg, product, region, brand, pal, spc, typ):
        from src.design_system import text_on

        bg = self._bg_color(pal)
        canvas = Image.new("RGB", (w, h), bg)
        draw = ImageDraw.Draw(canvas)

        # Left 55%: contain image with padding
        left_w  = int(w * 0.52)
        pad     = spc.lg
        prod    = img.convert("RGB")
        avail_w = left_w - 2 * pad
        avail_h = h - 2 * pad
        prod.thumbnail((avail_w, avail_h), Image.LANCZOS)
        px = (left_w - prod.width) // 2
        py = (h - prod.height) // 2
        canvas.paste(prod, (px, py))

        # Vertical separator
        sep_x = left_w
        draw_separator_line(draw, sep_x, spc.lg, h - 2 * spc.lg, pal.brand, vertical=True)

        # Right panel text
        text_col = text_on(bg)
        panel_x  = left_w + spc.margin
        panel_w  = w - panel_x - spc.margin
        vcenter  = h // 2

        if brand:
            brand_fnt = font("light", typ.small)
            bw, bh = measure_text(draw, brand.upper(), brand_fnt)
            brand_y = vcenter - int(h * 0.28)
            draw.text((panel_x, brand_y), brand.upper(), font=brand_fnt,
                      fill=(*pal.brand, 200))
            headline_y = brand_y + bh + spc.lg
        else:
            headline_y = vcenter - int(h * 0.24)

        headline = self._shorten(msg, words=7)
        bottom_y = self._draw_headline(
            draw, panel_x, headline_y, headline,
            "bold", typ.h1, panel_w, int(h * 0.35),
            text_col, shadow=False, align="left",
        )
        bottom_y += spc.sm

        prod_fnt = font("regular", typ.body)
        draw.text((panel_x, bottom_y), product, font=prod_fnt,
                  fill=(*pal.brand, 200))
        bottom_y += measure_text(draw, product, prod_fnt)[1] + spc.lg

        cta_fnt = font("bold", typ.cta)
        draw_cta(draw, panel_x + spc.xl, bottom_y, "Shop Now",
                 cta_fnt, pal.brand, text_on(pal.brand),
                 pad_x=spc.lg, pad_y=spc.sm)

        if region:
            badge_fnt = font("regular", typ.micro)
            draw_badge(draw, w - spc.margin, spc.margin, region, badge_fnt,
                       bg=(*pal.brand, 30), fg=pal.brand,
                       align="right", corner=max(6, spc.xs))

        return canvas


# ── Bold template ─────────────────────────────────────────────────────────────

class BoldTemplate(BaseTemplate):
    """
    High-contrast, oversized typography — Nike/streetwear aesthetic.
    Diagonal color split or strong typography-forward layout.
    """
    name = "bold"

    def _square(self, w, h, img, msg, product, region, brand, pal, spc, typ):
        # Full bleed, but with stronger overlay and bolder text treatment
        canvas = cover_crop(img, w, h, focus_y=0.35)
        canvas = vignette(canvas, strength=0.65)
        canvas = gradient_overlay(canvas, pal.brand_deep, direction="bottom",
                                  start_pct=0.30, max_alpha=235, curve=0.55)

        draw = ImageDraw.Draw(canvas)
        mx = spc.margin

        # Brand — top left, larger, bolder
        if brand:
            brand_fnt = font("bold", typ.small)
            draw.text((mx, mx), brand.upper(), font=brand_fnt,
                      fill=pal.cta)

        # Large text zone: 42%–88%
        text_top = int(h * 0.42)
        text_w   = int(w * 0.86)
        text_cx  = w // 2
        avail_h  = int(h * 0.88) - text_top

        # Oversized headline — allow up to 2 lines
        headline = self._shorten(msg, words=6)
        bottom_y = self._draw_headline(
            draw, text_cx, text_top, headline,
            "black", typ.display, text_w, int(avail_h * 0.58),
            pal.headline,
        )
        bottom_y += spc.sm

        # Accent bar (brand color strip) left-aligned
        bar_h = max(4, spc.xs)
        draw.rectangle([mx, bottom_y, mx + spc.xl * 2, bottom_y + bar_h],
                        fill=pal.cta)
        bottom_y += bar_h + spc.md

        # Product — bold, all-caps
        prod_fnt = font("bold", typ.body)
        pw, ph = measure_text(draw, product.upper(), prod_fnt)
        draw.text((text_cx - pw // 2, bottom_y), product.upper(), font=prod_fnt,
                  fill=(*pal.subtext, 230))
        bottom_y += ph + spc.lg

        # CTA — solid CTA color, pill
        cta_fnt = font("black", typ.cta)
        draw_cta(draw, text_cx, bottom_y, "SHOP NOW",
                 cta_fnt, pal.cta, pal.cta_text,
                 pad_x=spc.xl, pad_y=spc.sm)

        if region:
            badge_fnt = font("regular", typ.micro)
            draw_badge(draw, w - mx, mx, region, badge_fnt,
                       bg=(0, 0, 0, 140), fg=pal.badge_text,
                       align="right")

        return canvas

    def _story(self, w, h, img, msg, product, region, brand, pal, spc, typ):
        canvas = cover_crop(img, w, h, focus_y=0.30)
        canvas = vignette(canvas, strength=0.70)
        canvas = gradient_overlay(canvas, pal.brand_deep, direction="bottom",
                                  start_pct=0.25, max_alpha=245, curve=0.52)
        canvas = gradient_overlay(canvas, (0, 0, 0), direction="top",
                                  start_pct=0.80, max_alpha=80)

        draw = ImageDraw.Draw(canvas)
        mx = spc.margin

        if brand:
            brand_fnt = font("bold", typ.small)
            draw.text((mx, mx), brand.upper(), font=brand_fnt, fill=pal.cta)

        text_top = int(h * 0.40)
        text_cx  = w // 2
        text_w   = int(w * 0.88)
        avail_h  = int(h * 0.87) - text_top

        headline = self._shorten(msg, words=8)
        bottom_y = self._draw_headline(
            draw, text_cx, text_top, headline,
            "black", typ.display, text_w, int(avail_h * 0.50),
            pal.headline,
        )
        bottom_y += spc.sm

        bar_h = max(4, spc.xs)
        draw.rectangle([mx, bottom_y, mx + int(w * 0.40), bottom_y + bar_h], fill=pal.cta)
        bottom_y += bar_h + spc.md

        prod_fnt = font("bold", typ.body)
        pw, ph = measure_text(draw, product.upper(), prod_fnt)
        draw.text((text_cx - pw // 2, bottom_y), product.upper(), font=prod_fnt,
                  fill=(*pal.subtext, 230))
        bottom_y += ph + spc.lg

        cta_fnt = font("black", typ.cta)
        draw_cta(draw, text_cx, bottom_y, "SHOP NOW",
                 cta_fnt, pal.cta, pal.cta_text,
                 pad_x=int(spc.xl * 1.3), pad_y=spc.sm)

        return canvas

    def _landscape(self, w, h, img, msg, product, region, brand, pal, spc, typ):
        canvas = cover_crop(img, w, h, focus_y=0.45)
        canvas = vignette(canvas, strength=0.55)
        canvas = gradient_overlay(canvas, pal.brand_deep, direction="right",
                                  start_pct=0.35, max_alpha=240, curve=0.60)
        canvas = gradient_overlay(canvas, (0, 0, 0), direction="top",
                                  start_pct=0.90, max_alpha=50)

        draw = ImageDraw.Draw(canvas)

        # Text in right 45%
        panel_x = int(w * 0.52)
        panel_w = w - panel_x - spc.margin
        vcenter = h // 2

        if brand:
            brand_fnt = font("bold", typ.small)
            draw.text((panel_x, spc.margin), brand.upper(), font=brand_fnt, fill=pal.cta)

        headline_y = vcenter - int(h * 0.28)
        headline = self._shorten(msg, words=6)
        bottom_y = self._draw_headline(
            draw, panel_x, headline_y, headline,
            "black", typ.h1, panel_w, int(h * 0.40),
            pal.headline, align="left",
        )
        bottom_y += spc.sm

        bar_h = max(4, spc.xs)
        draw.rectangle([panel_x, bottom_y, panel_x + spc.xl * 2, bottom_y + bar_h], fill=pal.cta)
        bottom_y += bar_h + spc.md

        prod_fnt = font("bold", typ.body)
        draw.text((panel_x, bottom_y), product.upper(), font=prod_fnt,
                  fill=(*pal.subtext, 225))
        bottom_y += measure_text(draw, product.upper(), prod_fnt)[1] + spc.lg

        cta_fnt = font("black", typ.cta)
        draw_cta(draw, panel_x + spc.xl, bottom_y, "SHOP NOW",
                 cta_fnt, pal.cta, pal.cta_text,
                 pad_x=spc.lg, pad_y=spc.sm)

        if region:
            badge_fnt = font("regular", typ.micro)
            draw_badge(draw, w - spc.margin, spc.margin, region, badge_fnt,
                       bg=(0, 0, 0, 130), fg=pal.badge_text, align="right")

        return canvas


# ── Editorial template ────────────────────────────────────────────────────────

class EditorialTemplate(BaseTemplate):
    """
    Magazine split-panel — Condé Nast / Vogue aesthetic.
    Strong brand color panel with product float.
    """
    name = "editorial"

    def _square(self, w, h, img, msg, product, region, brand, pal, spc, typ):
        from src.design_system import text_on

        # Split: top 52% brand color, bottom 48% near-white
        split_y  = int(h * 0.52)
        top_col  = pal.brand
        bot_col  = (248, 248, 250)
        text_col = text_on(bot_col)

        canvas = Image.new("RGB", (w, h), bot_col)
        top_band = Image.new("RGB", (w, split_y), top_col)
        canvas.paste(top_band, (0, 0))

        # Product image — centered, straddling the split, floated up
        prod = img.convert("RGB")
        prod_h = int(h * 0.52)
        prod_w = prod_h  # square crop
        prod_crop = cover_crop(prod, prod_w, prod_h, focus_y=0.45)
        px = (w - prod_w) // 2
        py = int(h * 0.12)
        canvas.paste(prod_crop, (px, py))

        # Light drop shadow under product (simulate elevation)
        shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        sdraw  = ImageDraw.Draw(shadow)
        sdraw.ellipse([px + prod_w // 6, py + prod_h - 10,
                       px + prod_w - prod_w // 6, py + prod_h + 24],
                      fill=(0, 0, 0, 50))
        shadow = shadow.filter(ImageFilter.GaussianBlur(12))
        canvas = Image.alpha_composite(canvas.convert("RGBA"), shadow).convert("RGB")
        canvas.paste(prod_crop, (px, py))  # re-paste after shadow

        draw = ImageDraw.Draw(canvas)
        mx = spc.margin

        # Brand name on top band, top-left
        if brand:
            brand_fnt = font("light", typ.micro)
            draw.text((mx, mx), brand.upper(), font=brand_fnt,
                      fill=(*text_on(top_col), 180))

        # Region badge top-right
        if region:
            badge_fnt = font("regular", typ.micro)
            draw_badge(draw, w - mx, mx, region, badge_fnt,
                       bg=(0, 0, 0, 100), fg=text_on(top_col),
                       align="right", corner=max(6, spc.xs))

        # Text block, bottom 42%
        text_top = split_y + spc.md
        text_w   = int(w * 0.82)
        text_cx  = w // 2
        avail_h  = h - text_top - spc.vpad

        headline = self._shorten(msg, words=7)
        bottom_y = self._draw_headline(
            draw, text_cx, text_top, headline,
            "bold", typ.h2, text_w, int(avail_h * 0.48),
            text_col, shadow=False,
        )
        bottom_y += spc.sm

        prod_fnt = font("light", typ.small)
        pw, ph = measure_text(draw, product, prod_fnt)
        draw.text((text_cx - pw // 2, bottom_y), product, font=prod_fnt,
                  fill=(*pal.brand, 210))
        bottom_y += ph + spc.md

        cta_fnt = font("bold", typ.cta)
        draw_cta(draw, text_cx, bottom_y, "Discover",
                 cta_fnt, pal.brand, text_on(pal.brand),
                 pad_x=spc.lg, pad_y=spc.sm)

        return canvas

    def _story(self, w, h, img, msg, product, region, brand, pal, spc, typ):
        from src.design_system import text_on

        # Left stripe + full bleed image
        canvas = cover_crop(img, w, h, focus_y=0.40)
        canvas = gradient_overlay(canvas, pal.brand_deep, direction="bottom",
                                  start_pct=0.42, max_alpha=218, curve=0.62)
        canvas = gradient_overlay(canvas, pal.brand_deep, direction="top",
                                  start_pct=0.84, max_alpha=70)

        # Left brand stripe
        stripe_w = max(10, int(w * 0.025))
        stripe   = Image.new("RGB", (stripe_w, h), pal.cta)
        canvas.paste(stripe, (0, 0))

        draw = ImageDraw.Draw(canvas)
        mx = spc.margin

        if brand:
            brand_fnt = font("bold", typ.small)
            draw.text((mx, mx), brand.upper(), font=brand_fnt, fill=pal.cta)

        if region:
            badge_fnt = font("regular", typ.micro)
            draw_badge(draw, w - mx, mx, region, badge_fnt,
                       bg=(0, 0, 0, 120), fg=pal.badge_text, align="right")

        text_top = int(h * 0.50)
        text_cx  = w // 2
        text_w   = int(w * 0.82)
        avail_h  = int(h * 0.90) - text_top

        headline = self._shorten(msg, words=8)
        bottom_y = self._draw_headline(
            draw, text_cx, text_top, headline,
            "bold", typ.h1, text_w, int(avail_h * 0.50),
            pal.headline,
        )
        bottom_y += spc.sm

        prod_fnt = font("light", typ.body)
        pw, ph = measure_text(draw, product, prod_fnt)
        draw.text((text_cx - pw // 2, bottom_y), product, font=prod_fnt,
                  fill=(*pal.subtext, 210))
        bottom_y += ph + spc.lg

        cta_fnt = font("bold", typ.cta)
        draw_cta(draw, text_cx, bottom_y, "Discover",
                 cta_fnt, pal.cta, pal.cta_text,
                 pad_x=int(spc.xl * 1.2), pad_y=spc.sm)

        return canvas

    def _landscape(self, w, h, img, msg, product, region, brand, pal, spc, typ):
        from src.design_system import text_on

        # Right 44%: brand color panel
        panel_w = int(w * 0.44)
        img_w   = w - panel_w

        prod_crop = cover_crop(img, img_w, h, focus_y=0.45)
        canvas = Image.new("RGB", (w, h), pal.brand)
        canvas.paste(prod_crop, (0, 0))

        # Blend image into panel
        canvas = solid_panel(canvas, pal.brand, side="right",
                             split=panel_w / w, blend_px=max(50, int(w * 0.04)))

        draw = ImageDraw.Draw(canvas)

        panel_text_color = text_on(pal.brand)
        panel_x  = img_w + spc.margin
        pnl_w    = panel_w - spc.margin * 2
        vcenter  = h // 2

        if brand:
            brand_fnt = font("light", typ.small)
            bw, bh = measure_text(draw, brand.upper(), brand_fnt)
            brand_y = vcenter - int(h * 0.30)
            draw.text((panel_x, brand_y), brand.upper(), font=brand_fnt,
                      fill=(*panel_text_color, 180))
            # Accent line
            draw_separator_line(draw, panel_x, brand_y + bh + spc.sm,
                                spc.xl * 2, panel_text_color, vertical=False)
            headline_y = brand_y + bh + spc.md + spc.sm
        else:
            headline_y = vcenter - int(h * 0.26)

        headline = self._shorten(msg, words=6)
        bottom_y = self._draw_headline(
            draw, panel_x, headline_y, headline,
            "bold", typ.h1, pnl_w, int(h * 0.38),
            panel_text_color, shadow=False, align="left",
        )
        bottom_y += spc.md

        prod_fnt = font("light", typ.body)
        draw.text((panel_x, bottom_y), product, font=prod_fnt,
                  fill=(*panel_text_color, 200))
        bottom_y += measure_text(draw, product, prod_fnt)[1] + spc.lg

        # CTA — lighter version for contrast on brand panel
        cta_fill = text_on(pal.brand)
        cta_fnt  = font("bold", typ.cta)
        draw_cta(draw, panel_x + spc.xl, bottom_y, "Discover",
                 cta_fnt, (*cta_fill,), pal.brand,
                 pad_x=spc.lg, pad_y=spc.sm)

        if region:
            badge_fnt = font("regular", typ.micro)
            draw_badge(draw, img_w - spc.margin, spc.margin, region, badge_fnt,
                       bg=(0, 0, 0, 110), fg=(248, 250, 252),
                       align="right", corner=max(6, spc.xs))

        return canvas


# ── Template registry ─────────────────────────────────────────────────────────

_REGISTRY: dict[str, type[BaseTemplate]] = {
    "premium":   PremiumTemplate,
    "minimal":   MinimalTemplate,
    "bold":      BoldTemplate,
    "editorial": EditorialTemplate,
}


def get_template(name: str) -> BaseTemplate:
    """Return a template instance by name (case-insensitive)."""
    cls = _REGISTRY.get(name.lower(), PremiumTemplate)
    return cls()


def auto_select_template(product_name: str, brand_primary: str) -> BaseTemplate:
    """
    Deterministically select a template based on product + brand.
    Same inputs always produce the same template — consistent per product.
    """
    seed_str = (product_name + brand_primary).encode()
    idx = int(hashlib.md5(seed_str).hexdigest(), 16) % len(_REGISTRY)
    cls = list(_REGISTRY.values())[idx]
    return cls()


def available_templates() -> list[str]:
    return list(_REGISTRY.keys())
