"""
Creative Templates
Each template produces polished ad compositions for all three aspect ratios.
Templates share the DesignSystem drawing primitives — no hardcoded pixel values.

Layout discipline:
  - All positions derived from Spacing / TypeScale tokens, never raw pixels.
  - Split layouts (landscape/story): text column left edge = img_col_right + spc.inner.
  - CTAs in split layouts: align="left" so button left edge aligns with text column.
  - Vertical centering in right panels: headline placed at optical center, brand/separator
    float above it, product + CTA flow below.
  - Full-bleed layouts: text zone anchored by percentage of canvas height, all elements
    centered on canvas center-x.
"""

import hashlib
from abc import ABC, abstractmethod

from PIL import Image, ImageDraw, ImageFilter

from src.design_system import (
    Palette, Spacing, TypeScale,
    build_palette, build_spacing, build_type_scale,
    cover_crop, vignette, gradient_overlay, solid_panel,
    font, measure_text, wrap_to_width, fit_font,
    draw_shadow_text, draw_cta, draw_badge, draw_separator_line,
    lighten, text_on, luminance,
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
        else:
            return self._landscape(canvas_w, canvas_h, product_image, campaign_message,
                                   product_name, region, brand_name, pal, spc, typ)

    @abstractmethod
    def _square(self, w, h, img, msg, product, region, brand, pal, spc, typ) -> Image.Image: ...
    @abstractmethod
    def _story(self, w, h, img, msg, product, region, brand, pal, spc, typ) -> Image.Image: ...
    @abstractmethod
    def _landscape(self, w, h, img, msg, product, region, brand, pal, spc, typ) -> Image.Image: ...

    # ── Shared layout helpers ─────────────────────────────────────────────────

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
    def _draw_headline(draw, x, y, text, style, start_size, max_w, max_h,
                       color, shadow=True, align="center"):
        """
        Draw a wrapped headline. x is the anchor: center when align="center",
        left edge when align="left". Returns bottom y of last line.
        """
        fnt, wrapped = fit_font(draw, text, style, start_size, max_w, max_h, max_lines=3)
        lines = wrapped.split("\n")
        _, lh = measure_text(draw, "Ag", fnt)
        line_gap = max(4, lh // 8)
        cur_y = y

        for line in lines:
            lw, _ = measure_text(draw, line, fnt)
            if align == "center":
                lx = x - lw // 2
            elif align == "right":
                lx = x - lw
            else:               # "left"
                lx = x

            if shadow:
                draw_shadow_text(draw, (lx, cur_y), line, fnt, fill=color,
                                 shadow_color=(0, 0, 0, 110), offset=3)
            else:
                draw.text((lx, cur_y), line, font=fnt, fill=color)
            cur_y += lh + line_gap

        return cur_y

    @staticmethod
    def _optical_hl_y(h: int, typ: TypeScale, spc: Spacing,
                      brand_present: bool = True) -> int:
        """
        Headline top y for vertically-centered split panels.
        Places the headline at optical center (~44 % down from top),
        with room above for brand name + separator.
        """
        above_hl = (typ.small + spc.sm + 4 + spc.md) if brand_present else 0
        hl_center = int(h * 0.44)
        return max(spc.vpad + above_hl, hl_center - typ.h1)

    @staticmethod
    def _product_shadow(canvas: Image.Image, img_x: int, img_y: int,
                        img_w: int, img_h: int, spc: Spacing) -> Image.Image:
        """
        Add a soft elliptical drop shadow below a contained product image.
        Returns a new canvas with shadow baked in. Caller must re-paste
        the product image on top after calling this.
        """
        w, h = canvas.size
        shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        sdraw  = ImageDraw.Draw(shadow)
        # Ellipse hugging the bottom edge of the product
        ex1 = img_x + img_w // 6
        ey1 = img_y + img_h - spc.xs
        ex2 = img_x + img_w - img_w // 6
        ey2 = img_y + img_h + spc.md
        sdraw.ellipse([ex1, ey1, ex2, ey2], fill=(0, 0, 0, 40))
        shadow = shadow.filter(ImageFilter.GaussianBlur(spc.sm))
        return Image.alpha_composite(canvas.convert("RGBA"), shadow).convert("RGB")

    @staticmethod
    def _minimal_badge(draw: ImageDraw.Draw, x: int, y: int, text: str,
                       fnt, brand_rgb: tuple, spc: Spacing) -> None:
        """
        Region badge style for light-background (Minimal) layouts.
        Light brand-tinted background, full brand-color text — reads cleanly
        on neutral and light canvases without clashing with the product.
        """
        from src.design_system import lighten
        badge_bg = (*lighten(brand_rgb, 0.52), 90)   # light tint, semi-opaque
        draw_badge(draw, x, y, text, fnt,
                   bg=badge_bg, fg=brand_rgb,
                   align="right", corner=max(6, spc.xs))


# ── Premium template ──────────────────────────────────────────────────────────

class PremiumTemplate(BaseTemplate):
    """
    Full-bleed product image, gradient overlay, Apple/Nike premium feel.
    Square/story: bottom-anchored text zone, center-aligned stack.
    Landscape: right panel with optically-centered text column.
    """
    name = "premium"

    def _square(self, w, h, img, msg, product, region, brand, pal, spc, typ):
        canvas = cover_crop(img, w, h, focus_y=0.38)
        canvas = vignette(canvas, strength=0.45)
        canvas = gradient_overlay(canvas, pal.brand_deep,
                                  direction="bottom", start_pct=0.40,
                                  max_alpha=220, curve=0.68)
        canvas = gradient_overlay(canvas, (0, 0, 0),
                                  direction="top", start_pct=0.82,
                                  max_alpha=75, curve=0.55)

        draw = ImageDraw.Draw(canvas)
        mx   = spc.margin
        # Full-width text column
        text_cx = w // 2
        text_w  = w - 2 * mx

        # ── Chrome: brand (top-left) + region badge (top-right) ──────────────
        badge_y = mx
        if brand:
            draw.text((mx, badge_y), brand.upper(),
                      font=font("light", typ.micro), fill=(*pal.subtext, 200))
        if region:
            draw_badge(draw, w - mx, badge_y, region,
                       font("regular", typ.micro),
                       bg=(0, 0, 0, 130), fg=pal.badge_text,
                       align="right", corner=max(8, spc.xs))

        # ── Text zone anchored from 54 % down ────────────────────────────────
        text_top = int(h * 0.54)
        hl_max_h = int(h * 0.22)

        headline  = self._shorten(msg, words=8)
        bottom_y  = self._draw_headline(
            draw, text_cx, text_top, headline,
            "black", typ.display, text_w, hl_max_h, pal.headline,
        )

        # Product name
        bottom_y += spc.sm
        prod_fnt   = font("light", typ.body)
        pw, ph     = measure_text(draw, product, prod_fnt)
        draw.text((text_cx - pw // 2, bottom_y), product,
                  font=prod_fnt, fill=(*pal.subtext, 220))

        # CTA — centered on text column
        bottom_y += ph + spc.md
        draw_cta(draw, text_cx, bottom_y, "Shop Now",
                 font("bold", typ.cta), pal.cta, pal.cta_text,
                 pad_x=spc.lg, pad_y=spc.sm)

        return canvas

    def _story(self, w, h, img, msg, product, region, brand, pal, spc, typ):
        # Full-bleed — consistent with _square. Brand-deep tint preserves brand atmosphere.
        canvas = cover_crop(img, w, h, focus_y=0.35)
        canvas = vignette(canvas, strength=0.50)
        canvas = gradient_overlay(canvas, pal.brand_deep,
                                  direction="bottom", start_pct=0.38,
                                  max_alpha=245, curve=0.58)
        canvas = gradient_overlay(canvas, (0, 0, 0),
                                  direction="top", start_pct=0.88,
                                  max_alpha=60, curve=0.50)

        draw    = ImageDraw.Draw(canvas)
        mx      = spc.margin
        text_cx = w // 2
        text_w  = w - 2 * mx

        # ── Chrome ────────────────────────────────────────────────────────────
        if brand:
            draw.text((mx, mx), brand.upper(),
                      font=font("light", typ.micro), fill=(*pal.subtext, 190))
        if region:
            draw_badge(draw, w - mx, mx, region,
                       font("regular", typ.micro),
                       bg=(0, 0, 0, 120), fg=pal.badge_text,
                       align="right", corner=max(6, spc.xs))

        # ── Text zone: 64 %–93 % ─────────────────────────────────────────────
        text_top = int(h * 0.64)
        hl_max_h = int(h * 0.20)

        headline = self._shorten(msg, words=9)
        bottom_y = self._draw_headline(
            draw, text_cx, text_top, headline,
            "black", typ.h1, text_w, hl_max_h, pal.headline,
        )

        # Thin separator line — full text column width
        bottom_y += spc.sm
        draw_separator_line(draw, mx, bottom_y, text_w, pal.brand_light)
        bottom_y += spc.md

        # Product name
        prod_fnt = font("light", typ.body)
        pw, ph   = measure_text(draw, product, prod_fnt)
        draw.text((text_cx - pw // 2, bottom_y), product,
                  font=prod_fnt, fill=(*pal.subtext, 220))

        # CTA
        bottom_y += ph + spc.lg
        draw_cta(draw, text_cx, bottom_y, "Shop Now",
                 font("bold", typ.cta), pal.cta, pal.cta_text,
                 pad_x=spc.xl, pad_y=spc.sm)

        # Brand lockup at bottom center
        if brand:
            lock_fnt = font("light", typ.micro)
            lw, lh   = measure_text(draw, brand.upper(), lock_fnt)
            draw.text((text_cx - lw // 2, h - spc.vpad - lh),
                      brand.upper(), font=lock_fnt, fill=(*pal.subtext, 150))

        return canvas

    def _landscape(self, w, h, img, msg, product, region, brand, pal, spc, typ):
        # Image: left 56 % full-height
        img_col_w = int(w * 0.56)
        canvas    = Image.new("RGB", (w, h), pal.brand_deep)
        canvas.paste(cover_crop(img, img_col_w, h, focus_y=0.45), (0, 0))
        canvas    = solid_panel(canvas, pal.brand_deep, side="right",
                                split=0.44, blend_px=max(60, int(w * 0.045)))
        canvas    = gradient_overlay(canvas, (0, 0, 0),
                                     direction="top", start_pct=0.90, max_alpha=50)

        draw = ImageDraw.Draw(canvas)

        # ── Text column: starts after image + inner gap ───────────────────────
        txt_x    = img_col_w + spc.inner
        txt_r    = w - spc.margin
        txt_w    = txt_r - txt_x

        # ── Optical vertical centering ────────────────────────────────────────
        hl_y     = self._optical_hl_y(h, typ, spc, brand_present=bool(brand))
        brand_y  = hl_y - typ.small - spc.md

        # Brand name + accent separator above headline
        if brand:
            bw, bh = measure_text(draw, brand.upper(), font("light", typ.small))
            draw.text((txt_x, brand_y), brand.upper(),
                      font=font("light", typ.small), fill=(*pal.subtext, 190))
            draw_separator_line(draw, txt_x, brand_y + bh + spc.xs,
                                spc.xl * 2, pal.cta)

        # ── Headline ──────────────────────────────────────────────────────────
        headline = self._shorten(msg, words=7)
        bottom_y = self._draw_headline(
            draw, txt_x, hl_y, headline,
            "black", typ.h1, txt_w, int(h * 0.36),
            pal.headline, align="left",
        )

        # Product name
        bottom_y += spc.md
        prod_fnt  = font("light", typ.body)
        draw.text((txt_x, bottom_y), product,
                  font=prod_fnt, fill=(*pal.subtext, 215))
        bottom_y += measure_text(draw, product, prod_fnt)[1] + spc.lg

        # CTA — left edge aligns with text column
        draw_cta(draw, txt_x, bottom_y, "Shop Now",
                 font("bold", typ.cta), pal.cta, pal.cta_text,
                 pad_x=spc.lg, pad_y=spc.sm, align="left")

        # Region badge — top-right of canvas
        if region:
            draw_badge(draw, w - spc.margin, spc.margin, region,
                       font("regular", typ.micro),
                       bg=(0, 0, 0, 120), fg=pal.badge_text,
                       align="right", corner=max(6, spc.xs))

        return canvas


# ── Minimal template ──────────────────────────────────────────────────────────

class MinimalTemplate(BaseTemplate):
    """
    Light background, editorial feel. Notion/Linear/Stripe aesthetic.
    Product is the hero — contained at top, generous white space, clean type.
    """
    name = "minimal"

    def _bg_color(self, pal: Palette) -> tuple:
        """
        Near-white canvas background for contained-product layouts.
        Stays close to the neutral studio bg used by product photography
        (both mock and real) so product images blend without visible seams.
        A faint brand hue hint is applied at very low saturation.
        """
        from src.design_system import _to_hls, _from_hls
        h, _, s = _to_hls(pal.brand)
        # Lightness 0.96 (~245/255), saturation 4 % of brand saturation — imperceptible tint
        return _from_hls(h, 0.96, s * 0.04)

    def _square(self, w, h, img, msg, product, region, brand, pal, spc, typ):
        # Full-bleed image, black scrim — restrained gradient (not brand-deep)
        # preserves photo clarity while keeping text legible.
        canvas = cover_crop(img, w, h, focus_y=0.38)
        canvas = vignette(canvas, strength=0.35)
        canvas = gradient_overlay(canvas, (0, 0, 0),
                                  direction="bottom", start_pct=0.44,
                                  max_alpha=185, curve=0.65)

        draw    = ImageDraw.Draw(canvas)
        mx      = spc.margin
        text_cx = w // 2
        text_w  = w - 2 * mx

        # Chrome — brand top-left, badge top-right
        if brand:
            draw.text((mx, mx), brand.upper(),
                      font=font("light", typ.micro), fill=(*pal.subtext, 180))
        if region:
            draw_badge(draw, w - mx, mx, region,
                       font("regular", typ.micro),
                       bg=(0, 0, 0, 130), fg=pal.badge_text,
                       align="right", corner=max(8, spc.xs))

        # Text zone — starts well inside the scrim
        text_top = int(h * 0.54)
        hl_max_h = int(h * 0.20)

        headline = self._shorten(msg, words=7)
        bottom_y = self._draw_headline(
            draw, text_cx, text_top, headline,
            "bold", typ.h2, text_w, hl_max_h, pal.headline, shadow=False,
        )

        # Thin accent line — brand color, centered under headline
        bottom_y += spc.sm
        line_len  = spc.xl * 2
        draw_separator_line(draw, text_cx - line_len // 2, bottom_y,
                            line_len, pal.cta)
        bottom_y += spc.md

        # Product name
        prod_fnt = font("light", typ.body)
        pw, ph   = measure_text(draw, product, prod_fnt)
        draw.text((text_cx - pw // 2, bottom_y), product,
                  font=prod_fnt, fill=(*pal.subtext, 210))

        # CTA — brand color, centered on text axis
        bottom_y += ph + spc.md
        draw_cta(draw, text_cx, bottom_y, "Shop Now",
                 font("bold", typ.cta), pal.cta, pal.cta_text,
                 pad_x=spc.lg, pad_y=spc.sm)

        return canvas

    def _story(self, w, h, img, msg, product, region, brand, pal, spc, typ):
        # Full-bleed — black gradient scrim, lighter than Bold for restrained feel.
        canvas = cover_crop(img, w, h, focus_y=0.35)
        canvas = vignette(canvas, strength=0.30)
        canvas = gradient_overlay(canvas, (0, 0, 0),
                                  direction="bottom", start_pct=0.40,
                                  max_alpha=200, curve=0.62)

        draw    = ImageDraw.Draw(canvas)
        mx      = spc.margin
        text_cx = w // 2
        text_w  = w - 2 * mx

        # Chrome
        if brand:
            draw.text((mx, spc.vpad), brand.upper(),
                      font=font("light", typ.micro), fill=(*pal.subtext, 180))
        if region:
            draw_badge(draw, w - mx, spc.vpad, region,
                       font("regular", typ.micro),
                       bg=(0, 0, 0, 130), fg=pal.badge_text,
                       align="right", corner=max(6, spc.xs))

        # Text zone
        text_top = int(h * 0.54)
        hl_max_h = int(h * 0.18)

        headline = self._shorten(msg, words=9)
        bottom_y = self._draw_headline(
            draw, text_cx, text_top, headline,
            "bold", typ.h1, text_w, hl_max_h, pal.headline, shadow=False,
        )

        bottom_y += spc.sm
        line_len  = spc.xl * 2
        draw_separator_line(draw, text_cx - line_len // 2, bottom_y,
                            line_len, pal.cta)
        bottom_y += spc.md

        prod_fnt = font("light", typ.body)
        pw, ph   = measure_text(draw, product, prod_fnt)
        draw.text((text_cx - pw // 2, bottom_y), product,
                  font=prod_fnt, fill=(*pal.subtext, 210))

        bottom_y += ph + spc.lg
        draw_cta(draw, text_cx, bottom_y, "Shop Now",
                 font("bold", typ.cta), pal.cta, pal.cta_text,
                 pad_x=spc.xl, pad_y=spc.sm)

        # Brand footer
        if brand:
            foot_fnt = font("light", typ.micro)
            lw, lh   = measure_text(draw, brand, foot_fnt)
            draw.text((text_cx - lw // 2, h - spc.vpad - lh),
                      brand, font=foot_fnt, fill=(*pal.subtext, 140))

        return canvas

    def _landscape(self, w, h, img, msg, product, region, brand, pal, spc, typ):
        # Full-bleed, right-side black scrim — lighter than Bold so photo
        # still breathes on the left while text column is dark and legible.
        canvas = cover_crop(img, w, h, focus_y=0.45)
        canvas = vignette(canvas, strength=0.40)
        canvas = gradient_overlay(canvas, (0, 0, 0),
                                  direction="right", start_pct=0.40,
                                  max_alpha=200, curve=0.58)
        canvas = gradient_overlay(canvas, (0, 0, 0),
                                  direction="right", start_pct=0.55,
                                  max_alpha=155, curve=0.52)

        draw = ImageDraw.Draw(canvas)

        # Text column occupies right 48 % of canvas
        txt_x = int(w * 0.52) + spc.inner
        txt_r = w - spc.margin
        txt_w = txt_r - txt_x

        # Optically centered vertical stack
        hl_y    = self._optical_hl_y(h, typ, spc, brand_present=bool(brand))
        brand_y = hl_y - typ.small - spc.md

        if brand:
            bw, bh = measure_text(draw, brand.upper(), font("light", typ.small))
            draw.text((txt_x, brand_y), brand.upper(),
                      font=font("light", typ.small), fill=(*pal.subtext, 190))
            draw_separator_line(draw, txt_x, brand_y + bh + spc.xs,
                                spc.xl * 2, pal.cta)

        headline = self._shorten(msg, words=7)
        bottom_y = self._draw_headline(
            draw, txt_x, hl_y, headline,
            "bold", typ.h1, txt_w, int(h * 0.35),
            pal.headline, shadow=False, align="left",
        )

        bottom_y += spc.md
        prod_fnt  = font("light", typ.body)
        draw.text((txt_x, bottom_y), product,
                  font=prod_fnt, fill=(*pal.subtext, 210))
        bottom_y += measure_text(draw, product, prod_fnt)[1] + spc.lg

        draw_cta(draw, txt_x, bottom_y, "Shop Now",
                 font("bold", typ.cta), pal.cta, pal.cta_text,
                 pad_x=spc.lg, pad_y=spc.sm, align="left")

        # Region badge — top-right
        if region:
            draw_badge(draw, w - spc.margin, spc.margin, region,
                       font("regular", typ.micro),
                       bg=(0, 0, 0, 130), fg=pal.badge_text,
                       align="right", corner=max(6, spc.xs))

        return canvas


# ── Bold template ─────────────────────────────────────────────────────────────

class BoldTemplate(BaseTemplate):
    """
    High-contrast, oversized type — Nike/streetwear energy.
    Entire text stack is LEFT-ALIGNED to the margin edge.
    Brand name acts as eyebrow above the headline, not floating top-left chrome.
    """
    name = "bold"

    def _square(self, w, h, img, msg, product, region, brand, pal, spc, typ):
        canvas = cover_crop(img, w, h, focus_y=0.32)
        canvas = vignette(canvas, strength=0.60)
        # Primary gradient: covers bottom 76 %, fully opaque at bottom
        canvas = gradient_overlay(canvas, pal.brand_deep,
                                  direction="bottom", start_pct=0.24,
                                  max_alpha=245, curve=0.50)
        # Reinforcing scrim from text zone down — guarantees legibility at any focus_y
        canvas = gradient_overlay(canvas, pal.brand_deep,
                                  direction="bottom", start_pct=0.42,
                                  max_alpha=180, curve=0.45)

        draw    = ImageDraw.Draw(canvas)
        mx      = spc.margin
        # Left-aligned text column
        txt_x   = mx
        txt_w   = w - 2 * mx

        # Region badge — top-right only chrome element
        if region:
            draw_badge(draw, w - mx, mx, region,
                       font("regular", typ.micro),
                       bg=(0, 0, 0, 140), fg=pal.badge_text,
                       align="right")

        # ── Text stack — fully left-aligned ───────────────────────────────────
        text_top = int(h * 0.44)

        # Brand eyebrow above headline zone
        if brand:
            draw.text((txt_x, text_top - typ.small - spc.sm), brand.upper(),
                      font=font("bold", typ.small), fill=pal.cta)

        # Oversized headline
        headline = self._shorten(msg, words=6)
        bottom_y = self._draw_headline(
            draw, txt_x, text_top, headline,
            "black", typ.display, txt_w, int(h * 0.24),
            pal.headline, align="left",
        )

        # Accent bar — same left edge as headline
        bottom_y += spc.sm
        bar_h     = max(4, spc.xs)
        draw.rectangle([txt_x, bottom_y, txt_x + spc.xl * 3, bottom_y + bar_h],
                       fill=pal.cta)
        bottom_y += bar_h + spc.md

        # Product name — left-aligned, all-caps
        prod_fnt = font("bold", typ.body)
        pw, ph   = measure_text(draw, product.upper(), prod_fnt)
        draw.text((txt_x, bottom_y), product.upper(),
                  font=prod_fnt, fill=(*pal.subtext, 230))
        bottom_y += ph + spc.lg

        # CTA — left edge aligns with text column
        draw_cta(draw, txt_x, bottom_y, "SHOP NOW",
                 font("black", typ.cta), pal.cta, pal.cta_text,
                 pad_x=spc.xl, pad_y=spc.sm, align="left")

        return canvas

    def _story(self, w, h, img, msg, product, region, brand, pal, spc, typ):
        canvas = cover_crop(img, w, h, focus_y=0.28)
        canvas = vignette(canvas, strength=0.65)
        canvas = gradient_overlay(canvas, pal.brand_deep,
                                  direction="bottom", start_pct=0.20,
                                  max_alpha=250, curve=0.48)
        canvas = gradient_overlay(canvas, pal.brand_deep,
                                  direction="bottom", start_pct=0.38,
                                  max_alpha=190, curve=0.44)
        canvas = gradient_overlay(canvas, (0, 0, 0),
                                  direction="top", start_pct=0.82, max_alpha=70)

        draw  = ImageDraw.Draw(canvas)
        mx    = spc.margin
        txt_x = mx
        txt_w = w - 2 * mx

        # Region badge — top-right chrome
        if region:
            draw_badge(draw, w - mx, mx, region,
                       font("regular", typ.micro),
                       bg=(0, 0, 0, 140), fg=pal.badge_text, align="right")

        # ── Text stack — fully left-aligned ───────────────────────────────────
        text_top = int(h * 0.40)

        if brand:
            draw.text((txt_x, text_top - typ.small - spc.sm), brand.upper(),
                      font=font("bold", typ.small), fill=pal.cta)

        headline = self._shorten(msg, words=8)
        bottom_y = self._draw_headline(
            draw, txt_x, text_top, headline,
            "black", typ.display, txt_w, int(h * 0.26),
            pal.headline, align="left",
        )

        bottom_y += spc.sm
        bar_h     = max(4, spc.xs)
        draw.rectangle([txt_x, bottom_y, txt_x + spc.xl * 3, bottom_y + bar_h],
                       fill=pal.cta)
        bottom_y += bar_h + spc.md

        prod_fnt = font("bold", typ.body)
        draw.text((txt_x, bottom_y), product.upper(),
                  font=prod_fnt, fill=(*pal.subtext, 230))
        bottom_y += measure_text(draw, product.upper(), prod_fnt)[1] + spc.lg

        draw_cta(draw, txt_x, bottom_y, "SHOP NOW",
                 font("black", typ.cta), pal.cta, pal.cta_text,
                 pad_x=spc.xl, pad_y=spc.sm, align="left")

        return canvas

    def _landscape(self, w, h, img, msg, product, region, brand, pal, spc, typ):
        canvas = cover_crop(img, w, h, focus_y=0.45)
        canvas = vignette(canvas, strength=0.50)
        # Right gradient: covers 68 % of width from right edge — guarantees dark text panel
        canvas = gradient_overlay(canvas, pal.brand_deep,
                                  direction="right", start_pct=0.30,
                                  max_alpha=250, curve=0.55)
        # Reinforcing scrim on right 50 % where text lives
        canvas = gradient_overlay(canvas, pal.brand_deep,
                                  direction="right", start_pct=0.48,
                                  max_alpha=200, curve=0.50)
        canvas = gradient_overlay(canvas, (0, 0, 0),
                                  direction="top", start_pct=0.90, max_alpha=45)

        draw = ImageDraw.Draw(canvas)

        # ── Text column: right 48 % ───────────────────────────────────────────
        img_col_w = int(w * 0.52)
        txt_x     = img_col_w + spc.inner
        txt_r     = w - spc.margin
        txt_w     = txt_r - txt_x

        # Optically centered
        hl_y    = self._optical_hl_y(h, typ, spc, brand_present=bool(brand))
        brand_y = hl_y - typ.small - spc.md

        if brand:
            draw.text((txt_x, brand_y), brand.upper(),
                      font=font("bold", typ.small), fill=pal.cta)

        headline = self._shorten(msg, words=6)
        bottom_y = self._draw_headline(
            draw, txt_x, hl_y, headline,
            "black", typ.h1, txt_w, int(h * 0.40),
            pal.headline, align="left",
        )

        bottom_y += spc.sm
        bar_h     = max(4, spc.xs)
        draw.rectangle([txt_x, bottom_y, txt_x + spc.xl * 2, bottom_y + bar_h],
                       fill=pal.cta)
        bottom_y += bar_h + spc.md

        prod_fnt = font("bold", typ.body)
        draw.text((txt_x, bottom_y), product.upper(),
                  font=prod_fnt, fill=(*pal.subtext, 225))
        bottom_y += measure_text(draw, product.upper(), prod_fnt)[1] + spc.lg

        draw_cta(draw, txt_x, bottom_y, "SHOP NOW",
                 font("black", typ.cta), pal.cta, pal.cta_text,
                 pad_x=spc.lg, pad_y=spc.sm, align="left")

        # Region badge — top-right canvas edge
        if region:
            draw_badge(draw, w - spc.margin, spc.margin, region,
                       font("regular", typ.micro),
                       bg=(0, 0, 0, 130), fg=pal.badge_text, align="right")

        return canvas


# ── Editorial template ────────────────────────────────────────────────────────

class EditorialTemplate(BaseTemplate):
    """
    Magazine split-panel — Condé Nast precision.
    Square: product floated in color band above, editorial text below (no overlap).
    Story:  left accent stripe + full-bleed + centered text block.
    Landscape: brand-color right panel, image left, optically centered text.
    """
    name = "editorial"

    def _square(self, w, h, img, msg, product, region, brand, pal, spc, typ):
        # ── Background split ──────────────────────────────────────────────────
        split_y = int(h * 0.56)
        top_col = pal.brand
        bot_col = (248, 248, 250)
        text_col = text_on(bot_col)

        canvas   = Image.new("RGB", (w, h), bot_col)
        canvas.paste(Image.new("RGB", (w, split_y), top_col), (0, 0))

        # ── Product image: contained entirely within top band ─────────────────
        py     = spc.vpad
        max_ph = split_y - py - spc.sm    # image must end above split
        prod_sz = min(max_ph, w - 2 * spc.margin)  # square crop
        prod_crop = cover_crop(img.convert("RGB"), prod_sz, prod_sz, focus_y=0.45)
        px = (w - prod_sz) // 2

        # Drop shadow below product (simulate elevation over the split)
        shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        sdraw  = ImageDraw.Draw(shadow)
        sdraw.ellipse([px + prod_sz // 5, py + prod_sz - spc.xs,
                       px + prod_sz - prod_sz // 5, py + prod_sz + spc.md],
                      fill=(0, 0, 0, 45))
        shadow = shadow.filter(ImageFilter.GaussianBlur(14))
        canvas = Image.alpha_composite(canvas.convert("RGBA"), shadow).convert("RGB")
        canvas.paste(prod_crop, (px, py))  # product on top of shadow

        draw = ImageDraw.Draw(canvas)
        mx   = spc.margin

        # Chrome — brand & region on the top band
        if brand:
            draw.text((mx, mx), brand.upper(),
                      font=font("light", typ.micro),
                      fill=(*text_on(top_col), 175))
        if region:
            draw_badge(draw, w - mx, mx, region,
                       font("regular", typ.micro),
                       bg=(0, 0, 0, 100), fg=text_on(top_col),
                       align="right", corner=max(6, spc.xs))

        # ── Text block — starts below split, no image overlap ─────────────────
        text_top = split_y + spc.md
        text_cx  = w // 2
        text_w   = w - 2 * mx
        avail_h  = h - text_top - spc.vpad

        headline = self._shorten(msg, words=7)
        bottom_y = self._draw_headline(
            draw, text_cx, text_top, headline,
            "bold", typ.h2, text_w, int(avail_h * 0.46),
            text_col, shadow=False,
        )

        # Thin separator
        bottom_y += spc.sm
        draw_separator_line(draw, mx, bottom_y, text_w, pal.brand)
        bottom_y += spc.sm

        # Product name
        prod_fnt = font("light", typ.small)
        pw, ph   = measure_text(draw, product, prod_fnt)
        draw.text((text_cx - pw // 2, bottom_y), product,
                  font=prod_fnt, fill=(*pal.brand, 210))

        # CTA
        bottom_y += ph + spc.md
        draw_cta(draw, text_cx, bottom_y, "Discover",
                 font("bold", typ.cta), pal.brand, text_on(pal.brand),
                 pad_x=spc.lg, pad_y=spc.sm)

        return canvas

    def _story(self, w, h, img, msg, product, region, brand, pal, spc, typ):
        # Horizontal split: photo top 54 %, brand-deep panel bottom 46 %.
        # Text always on solid panel — no gradient legibility gambling.
        split_y  = int(h * 0.54)
        panel_tc = text_on(pal.brand_deep)

        canvas = Image.new("RGB", (w, h), pal.brand_deep)
        photo  = cover_crop(img, w, split_y, focus_y=0.40)
        canvas.paste(photo, (0, 0))

        # Scrim at photo bottom fades into panel seam
        canvas = gradient_overlay(canvas, pal.brand_deep,
                                  direction="bottom", start_pct=0.28,
                                  max_alpha=160, curve=0.50)

        # Left accent stripe spans full height
        stripe_w = max(16, int(w * 0.035))
        canvas.paste(Image.new("RGB", (stripe_w, h), pal.cta), (0, 0))

        draw    = ImageDraw.Draw(canvas)
        mx      = spc.margin
        text_cx = w // 2
        text_w  = w - 2 * mx

        # Chrome in photo zone top
        chrome_y = spc.vpad
        if brand:
            draw.text((mx, chrome_y), brand.upper(),
                      font=font("bold", typ.small), fill=pal.cta)
        if region:
            draw_badge(draw, w - mx, chrome_y, region,
                       font("regular", typ.micro),
                       bg=(0, 0, 0, 120), fg=pal.badge_text, align="right")

        # Text zone starts on the solid brand panel
        text_top = split_y + spc.md
        hl_max_h = int(h * 0.20)

        headline = self._shorten(msg, words=8)
        bottom_y = self._draw_headline(
            draw, text_cx, text_top, headline,
            "bold", typ.h1, text_w, hl_max_h,
            panel_tc, shadow=False,
        )

        bottom_y += spc.sm
        draw_separator_line(draw, mx, bottom_y, text_w, pal.cta)
        bottom_y += spc.md

        prod_fnt = font("light", typ.body)
        pw, ph   = measure_text(draw, product, prod_fnt)
        draw.text((text_cx - pw // 2, bottom_y), product,
                  font=prod_fnt, fill=(*panel_tc, 190))

        bottom_y += ph + spc.lg
        draw_cta(draw, text_cx, bottom_y, "Discover",
                 font("bold", typ.cta), pal.cta, pal.cta_text,
                 pad_x=spc.xl, pad_y=spc.sm)

        # Brand footer anchors bottom of panel
        if brand:
            footer_fnt = font("light", typ.micro)
            fw, _ = measure_text(draw, brand.upper(), footer_fnt)
            draw.text((text_cx - fw // 2, h - spc.vpad - typ.micro),
                      brand.upper(), font=footer_fnt,
                      fill=(*panel_tc, 90))

        return canvas

    def _landscape(self, w, h, img, msg, product, region, brand, pal, spc, typ):
        # Right panel: brand color. Image: left portion.
        panel_w   = int(w * 0.44)
        img_col_w = w - panel_w

        canvas = Image.new("RGB", (w, h), pal.brand)
        canvas.paste(cover_crop(img, img_col_w, h, focus_y=0.45), (0, 0))
        canvas = solid_panel(canvas, pal.brand, side="right",
                             split=panel_w / w,
                             blend_px=max(50, int(w * 0.038)))

        draw = ImageDraw.Draw(canvas)

        panel_text_color = text_on(pal.brand)

        # ── Text column ───────────────────────────────────────────────────────
        txt_x = img_col_w + spc.inner
        txt_r = w - spc.margin
        txt_w = txt_r - txt_x

        # Optically centered
        hl_y    = self._optical_hl_y(h, typ, spc, brand_present=bool(brand))
        brand_y = hl_y - typ.small - spc.md

        if brand:
            bw, bh = measure_text(draw, brand.upper(), font("light", typ.small))
            draw.text((txt_x, brand_y), brand.upper(),
                      font=font("light", typ.small),
                      fill=(*panel_text_color, 175))
            draw_separator_line(draw, txt_x, brand_y + bh + spc.xs,
                                spc.xl * 2, panel_text_color)

        headline = self._shorten(msg, words=6)
        bottom_y = self._draw_headline(
            draw, txt_x, hl_y, headline,
            "bold", typ.h1, txt_w, int(h * 0.38),
            panel_text_color, shadow=False, align="left",
        )

        # Product name
        bottom_y += spc.md
        prod_fnt  = font("light", typ.body)
        draw.text((txt_x, bottom_y), product,
                  font=prod_fnt, fill=(*panel_text_color, 200))
        bottom_y += measure_text(draw, product, prod_fnt)[1] + spc.lg

        # CTA — inverted: white fill, brand text (high contrast on brand panel)
        cta_fill  = panel_text_color    # (250, 251, 252) on dark brand
        draw_cta(draw, txt_x, bottom_y, "Discover",
                 font("bold", typ.cta), cta_fill, pal.brand,
                 pad_x=spc.lg, pad_y=spc.sm, align="left")

        # Region badge — top-right of the image zone (left of canvas)
        if region:
            draw_badge(draw, img_col_w - spc.inner, spc.margin, region,
                       font("regular", typ.micro),
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
    """Return a template instance by name (case-insensitive). Falls back to Premium."""
    cls = _REGISTRY.get(name.lower(), PremiumTemplate)
    return cls()


def auto_select_template(product_name: str, brand_primary: str) -> BaseTemplate:
    """
    Deterministically select a template. MD5 of (product_name + brand_primary)
    guarantees the same brief always produces the same template family.
    """
    seed_str = (product_name + brand_primary).encode()
    idx      = int(hashlib.md5(seed_str).hexdigest(), 16) % len(_REGISTRY)
    cls      = list(_REGISTRY.values())[idx]
    return cls()


def available_templates() -> list[str]:
    return list(_REGISTRY.keys())
