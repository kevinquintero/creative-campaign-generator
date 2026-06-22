"""
Creative Design System
Shared tokens (color, spacing, type) and low-level drawing primitives.
All values derive from canvas dimensions — nothing is hardcoded per call site.
"""

import colorsys
from dataclasses import dataclass
from typing import Sequence

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ── Type aliases ──────────────────────────────────────────────────────────────
RGB  = tuple[int, int, int]
RGBA = tuple[int, int, int, int]


# ── Color math ────────────────────────────────────────────────────────────────

def hex_to_rgb(hex_color: str) -> RGB:
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return (30, 58, 95)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _to_hls(rgb: RGB) -> tuple[float, float, float]:
    r, g, b = (x / 255 for x in rgb)
    return colorsys.rgb_to_hls(r, g, b)


def _from_hls(h: float, l: float, s: float) -> RGB:
    r, g, b = colorsys.hls_to_rgb(h, max(0.0, min(1.0, l)), max(0.0, min(1.0, s)))
    return (int(r * 255), int(g * 255), int(b * 255))


def luminance(rgb: RGB) -> float:
    return (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255


def lighten(rgb: RGB, amount: float) -> RGB:
    h, l, s = _to_hls(rgb)
    return _from_hls(h, l + amount, s)


def darken(rgb: RGB, amount: float) -> RGB:
    h, l, s = _to_hls(rgb)
    return _from_hls(h, l - amount, s)


def saturate(rgb: RGB, amount: float) -> RGB:
    h, l, s = _to_hls(rgb)
    return _from_hls(h, l, s + amount)


def desaturate(rgb: RGB, amount: float) -> RGB:
    h, l, s = _to_hls(rgb)
    return _from_hls(h, l, s - amount)


def shift_hue(rgb: RGB, degrees: float) -> RGB:
    h, l, s = _to_hls(rgb)
    return _from_hls((h + degrees / 360) % 1.0, l, s)


def blend_rgb(a: RGB, b: RGB, t: float) -> RGB:
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


def text_on(bg: RGB) -> RGB:
    """Return legible text color (white or near-black) for a given background."""
    return (250, 251, 252) if luminance(bg) < 0.50 else (14, 16, 20)


def clamp_rgb(r: int, g: int, b: int) -> RGB:
    return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))


# ── Palette ───────────────────────────────────────────────────────────────────

@dataclass
class Palette:
    brand:        RGB   # Primary brand color
    brand_dark:   RGB   # Darker variant
    brand_deep:   RGB   # Very dark (for overlays / panels)
    brand_light:  RGB   # Lighter variant
    secondary:    RGB   # Secondary / accent
    cta:          RGB   # CTA button fill
    cta_text:     RGB   # CTA button label
    headline:     RGB   # Primary headline text
    subtext:      RGB   # Supporting text (muted)
    badge_bg:     RGB   # Small badge background
    badge_text:   RGB   # Small badge text
    is_dark_brand: bool


def build_palette(primary_hex: str, secondary_hex: str = "") -> Palette:
    brand = hex_to_rgb(primary_hex)
    is_dark = luminance(brand) < 0.45

    brand_dark  = darken(brand, 0.22)
    brand_deep  = darken(brand, 0.48)
    brand_light = lighten(brand, 0.30)

    # Secondary — use brief value if provided and distinct
    if secondary_hex and secondary_hex.strip("#") and secondary_hex.lower() not in ("#ffffff", "#fff"):
        secondary = hex_to_rgb(secondary_hex)
    else:
        # Derive a warm accent: shift hue +15° and boost saturation
        secondary = saturate(shift_hue(brand, 15), 0.20)
        secondary = lighten(secondary, 0.18) if is_dark else darken(secondary, 0.10)

    # CTA: should be visually pop-y (mid-luminance is best)
    lum_s = luminance(secondary)
    if 0.15 < lum_s < 0.88:
        cta = secondary
    else:
        # Warm golden fallback
        cta = _from_hls(0.11, 0.58, 0.85)  # warm amber

    return Palette(
        brand       = brand,
        brand_dark  = brand_dark,
        brand_deep  = brand_deep,
        brand_light = brand_light,
        secondary   = secondary,
        cta         = cta,
        cta_text    = text_on(cta),
        headline    = (250, 251, 252),
        subtext     = (185, 198, 215),
        badge_bg    = (255, 255, 255, 38),
        badge_text  = (245, 246, 248),
        is_dark_brand = is_dark,
    )


# ── Spacing ───────────────────────────────────────────────────────────────────

@dataclass
class Spacing:
    unit:   int    # Base unit (~21px at 1080)
    xs:     int    # ½u  — fine gaps, icon padding
    sm:     int    # 1u  — tight gap between related elements
    md:     int    # 2u  — gap between distinct elements
    lg:     int    # 3u  — section gap
    xl:     int    # 5u  — generous gap / CTA horizontal padding
    margin: int    # Outer canvas safe margin (both axes, derived from min dimension)
    inner:  int    # Panel-interior gap — narrower than margin, used where image meets text
    vpad:   int    # Vertical safe padding from top/bottom canvas edges


def build_spacing(w: int, h: int) -> Spacing:
    ref  = min(w, h)          # Orientation-invariant reference dimension
    unit = max(14, ref // 50)
    return Spacing(
        unit   = unit,
        xs     = max(6,  unit // 2),
        sm     = unit,
        md     = unit * 2,
        lg     = unit * 3,
        xl     = unit * 5,
        margin = max(44, int(ref * 0.076)),   # ~82px at 1080 — consistent across orientations
        inner  = max(28, int(ref * 0.048)),   # ~52px at 1080 — tighter, for panel seams
        vpad   = max(36, int(h   * 0.052)),   # Vertical: relative to canvas height
    )


# ── Typography scale ──────────────────────────────────────────────────────────

@dataclass
class TypeScale:
    display: int   # Giant marketing headline
    h1:      int   # Large headline
    h2:      int   # Subheadline
    body:    int   # Product name / supporting copy
    small:   int   # Captions, labels
    micro:   int   # Badges, fine print
    cta:     int   # CTA button label


def build_type_scale(w: int, h: int) -> TypeScale:
    ref = min(w, h)
    return TypeScale(
        display = max(54, int(ref * 0.092)),
        h1      = max(42, int(ref * 0.072)),
        h2      = max(32, int(ref * 0.052)),
        body    = max(24, int(ref * 0.034)),
        small   = max(18, int(ref * 0.024)),
        micro   = max(14, int(ref * 0.017)),
        cta     = max(22, int(ref * 0.030)),
    )


# ── Font loader ───────────────────────────────────────────────────────────────

_CACHE: dict[tuple, ImageFont.FreeTypeFont] = {}

_FONTS: dict[str, list[str]] = {
    "black":   ["ariblk.ttf", "impact.ttf", "arialbd.ttf"],
    "bold":    ["segoeuib.ttf", "arialbd.ttf", "calibrib.ttf", "verdanab.ttf"],
    "semibold":["segoeuisb.ttf", "segoeuib.ttf", "calibrib.ttf", "arialbd.ttf"],
    "regular": ["segoeui.ttf", "calibri.ttf", "arial.ttf", "verdana.ttf"],
    "light":   ["segoeuil.ttf", "calibril.ttf", "calibri.ttf", "arial.ttf"],
    "serif":   ["georgia.ttf", "times.ttf", "arial.ttf"],
    "serif-bold": ["georgiab.ttf", "timesbd.ttf", "arialbd.ttf"],
    "italic":  ["segoeuii.ttf", "calibrii.ttf", "ariali.ttf", "georgia.ttf"],
}


def font(style: str = "regular", size: int = 24) -> ImageFont.FreeTypeFont:
    key = (style, size)
    if key in _CACHE:
        return _CACHE[key]
    for path in _FONTS.get(style, _FONTS["regular"]):
        try:
            f = ImageFont.truetype(path, size)
            _CACHE[key] = f
            return f
        except (IOError, OSError):
            continue
    f = ImageFont.load_default()
    _CACHE[key] = f
    return f


# ── Image utilities ───────────────────────────────────────────────────────────

def cover_crop(img: Image.Image, w: int, h: int, focus_y: float = 0.45) -> Image.Image:
    """
    Scale image to cover (w, h), then crop.
    focus_y: vertical center point to keep (0=top, 0.5=center, 1=bottom).
    """
    img = img.convert("RGB")
    iw, ih = img.size
    scale = max(w / iw, h / ih)
    nw = max(w, int(iw * scale) + 1)
    nh = max(h, int(ih * scale) + 1)
    img = img.resize((nw, nh), Image.LANCZOS)
    left = (nw - w) // 2
    top  = int((nh - h) * focus_y)
    top  = max(0, min(top, nh - h))
    return img.crop((left, top, left + w, top + h))


def vignette(img: Image.Image, strength: float = 0.55) -> Image.Image:
    """Apply a radial dark vignette around the edges."""
    w, h = img.size
    vig = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(vig)
    steps = 48
    for i in range(steps):
        t = i / steps
        alpha = int(strength * 255 * (t ** 2.2))
        pw = int(w * t / 2)
        ph = int(h * t / 2)
        draw.rectangle([pw, ph, w - pw, h - ph], outline=(0, 0, 0, alpha), width=max(2, w // 120))
    return Image.alpha_composite(img.convert("RGBA"), vig).convert("RGB")


def gradient_overlay(
    img: Image.Image,
    color: RGB,
    direction: str = "bottom",   # "bottom" | "top" | "right" | "left"
    start_pct: float = 0.40,     # where gradient begins
    max_alpha: int = 220,
    curve: float = 0.72,
) -> Image.Image:
    """Paint a directional gradient overlay onto img (in-place copy returned)."""
    w, h = img.size
    canvas = img.convert("RGBA")
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    if direction == "bottom":
        total = h - int(h * start_pct)
        for i in range(total):
            t = i / total
            a = int(max_alpha * (t ** curve))
            y = int(h * start_pct) + i
            draw.line([(0, y), (w, y)], fill=(*color, a))

    elif direction == "top":
        total = int(h * (1 - start_pct))
        for i in range(total):
            t = (total - i) / total
            a = int(max_alpha * (t ** curve))
            draw.line([(0, i), (w, i)], fill=(*color, a))

    elif direction == "right":
        total = w - int(w * start_pct)
        for i in range(total):
            t = i / total
            a = int(max_alpha * (t ** curve))
            x = int(w * start_pct) + i
            draw.line([(x, 0), (x, h)], fill=(*color, a))

    elif direction == "left":
        total = int(w * (1 - start_pct))
        for i in range(total):
            t = (total - i) / total
            a = int(max_alpha * (t ** curve))
            draw.line([(i, 0), (i, h)], fill=(*color, a))

    return Image.alpha_composite(canvas, overlay).convert("RGB")


def solid_panel(
    img: Image.Image,
    color: RGB,
    side: str = "right",   # "right" | "left" | "bottom" | "top"
    split: float = 0.45,   # fraction for the panel
    blend_px: int = 60,    # soft-blend width
) -> Image.Image:
    """Paint a solid brand color panel on one side with a soft gradient blend at the seam."""
    w, h = img.size
    canvas = img.convert("RGBA")
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    if side == "right":
        px = int(w * (1 - split))
        # Hard panel beyond blend zone
        draw.rectangle([px + blend_px, 0, w, h], fill=(*color, 255))
        # Blend zone
        for i in range(blend_px):
            t = i / blend_px
            a = int(255 * (t ** 0.65))
            draw.line([(px + i, 0), (px + i, h)], fill=(*color, a))

    elif side == "left":
        px = int(w * split)
        draw.rectangle([0, 0, px - blend_px, h], fill=(*color, 255))
        for i in range(blend_px):
            t = (blend_px - i) / blend_px
            a = int(255 * (t ** 0.65))
            draw.line([(px - blend_px + i, 0), (px - blend_px + i, h)], fill=(*color, a))

    elif side == "bottom":
        py = int(h * (1 - split))
        draw.rectangle([0, py + blend_px, w, h], fill=(*color, 255))
        for i in range(blend_px):
            t = i / blend_px
            a = int(255 * (t ** 0.65))
            draw.line([(0, py + i), (w, py + i)], fill=(*color, a))

    return Image.alpha_composite(canvas, overlay).convert("RGB")


# ── Text utilities ────────────────────────────────────────────────────────────

def measure_text(draw: ImageDraw.Draw, text: str, fnt: ImageFont.FreeTypeFont) -> tuple[int, int]:
    bb = draw.textbbox((0, 0), text, font=fnt)
    return bb[2] - bb[0], bb[3] - bb[1]


def wrap_to_width(
    draw: ImageDraw.Draw,
    text: str,
    fnt: ImageFont.FreeTypeFont,
    max_px: int,
) -> str:
    """Word-wrap text so each line fits within max_px. Returns the wrapped string."""
    words = text.split()
    lines: list[str] = []
    current: list[str] = []

    for word in words:
        test = " ".join(current + [word])
        w, _ = measure_text(draw, test, fnt)
        if w <= max_px:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]

    if current:
        lines.append(" ".join(current))

    return "\n".join(lines) if lines else text


def fit_font(
    draw: ImageDraw.Draw,
    text: str,
    style: str,
    start_size: int,
    max_px_w: int,
    max_px_h: int,
    max_lines: int = 3,
) -> tuple[ImageFont.FreeTypeFont, str]:
    """
    Find the largest font size that makes `text` fit in (max_px_w × max_px_h).
    Returns (font, wrapped_text).
    """
    size = start_size
    while size >= 14:
        fnt = font(style, size)
        wrapped = wrap_to_width(draw, text, fnt, max_px_w)
        lines = wrapped.split("\n")
        if len(lines) > max_lines:
            size = int(size * 0.88)
            continue
        _, th = measure_text(draw, wrapped, fnt)
        if th <= max_px_h:
            return fnt, wrapped
        size = int(size * 0.88)
    fnt = font(style, 14)
    wrapped = wrap_to_width(draw, text, fnt, max_px_w)
    return fnt, wrapped


def draw_shadow_text(
    draw: ImageDraw.Draw,
    xy: tuple[int, int],
    text: str,
    fnt: ImageFont.FreeTypeFont,
    fill: RGB | tuple,
    shadow_color: tuple = (0, 0, 0, 100),
    offset: int = 3,
):
    x, y = xy
    # Multi-layer shadow for depth
    for ox, oy, a in ((offset + 1, offset + 1, 60), (offset, offset, shadow_color[3])):
        draw.text((x + ox, y + oy), text, font=fnt, fill=(*shadow_color[:3], a))
    draw.text((x, y), text, font=fnt, fill=fill)


def draw_cta(
    draw: ImageDraw.Draw,
    cx: int,                # Anchor x — meaning depends on align
    y: int,                 # Top y of button
    label: str,
    fnt: ImageFont.FreeTypeFont,
    fill: RGB,
    text_color: RGB,
    corner: int = 0,        # 0 = full pill
    pad_x: int = 40,
    pad_y: int = 18,
    align: str = "center",  # "center": cx is center | "left": cx is left edge | "right": cx is right edge
) -> int:
    """Draw a CTA button. Returns button bottom y."""
    tw, th = measure_text(draw, label, fnt)
    bw = tw + pad_x * 2
    bh = th + pad_y * 2
    radius = corner if corner > 0 else bh // 2

    if align == "left":
        x1, x2 = cx, cx + bw
    elif align == "right":
        x1, x2 = cx - bw, cx
    else:  # center
        x1 = cx - bw // 2
        x2 = cx + bw // 2

    y2 = y + bh

    # Subtle inner glow ring
    glow = lighten(fill, 0.12)
    draw.rounded_rectangle([x1 - 2, y - 2, x2 + 2, y2 + 2], radius=radius + 2, fill=(*glow, 80))
    draw.rounded_rectangle([x1, y, x2, y2], radius=radius, fill=fill)

    # anchor="mm" visually centers glyphs at button center — handles font bearing precisely
    btn_cx = (x1 + x2) // 2
    btn_cy = y + bh // 2
    draw.text((btn_cx, btn_cy), label, font=fnt, fill=text_color, anchor="mm")

    return y2


def draw_badge(
    draw: ImageDraw.Draw,
    x: int, y: int,
    text: str,
    fnt: ImageFont.FreeTypeFont,
    bg: tuple = (0, 0, 0, 120),
    fg: RGB = (245, 246, 248),
    pad_x: int = 14,
    pad_y: int = 8,
    corner: int = 8,
    align: str = "left",   # "left" | "right" (x is the anchor edge)
) -> int:
    """Draw a pill badge. Returns right edge x."""
    tw, th = measure_text(draw, text, fnt)
    bw = tw + pad_x * 2
    bh = th + pad_y * 2

    if align == "right":
        x1 = x - bw
    else:
        x1 = x

    draw.rounded_rectangle([x1, y, x1 + bw, y + bh], radius=corner, fill=bg)
    # anchor="mm" visually centers label glyphs within badge
    draw.text((x1 + bw // 2, y + bh // 2), text, font=fnt, fill=fg, anchor="mm")
    return x1 + bw


def draw_separator_line(draw: ImageDraw.Draw, x: int, y: int, length: int, color: RGB, vertical: bool = False):
    if vertical:
        draw.line([(x, y), (x, y + length)], fill=(*color, 90), width=1)
    else:
        draw.line([(x, y), (x + length, y)], fill=(*color, 90), width=1)
