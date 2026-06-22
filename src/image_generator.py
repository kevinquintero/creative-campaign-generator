"""
Image generation provider layer.

MockImageProvider is the default — it creates branded placeholder PNGs using Pillow
so the pipeline works locally without any paid API keys.

To connect a real provider, set IMAGE_PROVIDER in .env and supply the matching API key.

Currently supported:
  IMAGE_PROVIDER=mock    (default, no API key needed)
  IMAGE_PROVIDER=openai  (requires OPENAI_API_KEY)

Adding a new provider:
  1. Subclass BaseImageProvider
  2. Implement generate() — return a PIL Image
  3. Register it in ImageGenerator.from_env()
"""

import io
import logging
import os
import urllib.request
from abc import ABC, abstractmethod

from PIL import Image, ImageDraw, ImageFont

from src.utils import hex_to_rgb

logger = logging.getLogger(__name__)


# ── Base interface ────────────────────────────────────────────────────────────

class BaseImageProvider(ABC):
    name: str = "base"

    @abstractmethod
    def generate(
        self,
        product_name: str,
        description: str,
        width: int,
        height: int,
        primary_color: str,
        campaign_message: str = "",
        region: str = "",
        target_audience: str = "",
    ) -> Image.Image:
        """Generate a product image and return a PIL Image."""
        ...


# ── Mock provider ─────────────────────────────────────────────────────────────

class MockImageProvider(BaseImageProvider):
    """
    Generates studio-style product placeholder images using Pillow only.
    Produces a lit, three-dimensional product form on a neutral background.
    No external API required.
    """

    name = "mock"

    def generate(
        self,
        product_name: str,
        description: str,
        width: int,
        height: int,
        primary_color: str,
        campaign_message: str = "",
        region: str = "",
        target_audience: str = "",
    ) -> Image.Image:
        logger.info("[MockImageProvider] Generating image for '%s' at %dx%d", product_name, width, height)

        brand = hex_to_rgb(primary_color)
        category = _detect_category(product_name, description)

        # Studio background: warm neutral gradient (top-right light source)
        img = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(img)
        self._draw_studio_bg(draw, width, height)

        # Product form centered, offset slightly upward
        cx = width // 2
        cy = int(height * 0.45)
        self._draw_product(draw, cx, cy, width, height, brand, category)

        # Soft ground shadow beneath product
        self._draw_ground_shadow(draw, cx, cy, width, height)

        return img

    # ── Studio background ─────────────────────────────────────────────────────

    def _draw_studio_bg(self, draw, w, h):
        """Radial gradient: near-white center, soft grey edges (studio sweep)."""
        center_col = (252, 252, 252)
        edge_col   = (220, 220, 225)
        cx, cy = int(w * 0.55), int(h * 0.35)  # off-center light position
        max_r  = int((w ** 2 + h ** 2) ** 0.5)

        steps = 80
        for i in range(steps, 0, -1):
            t  = i / steps
            r  = int(max_r * t)
            rc = int(center_col[0] * (1 - t) + edge_col[0] * t)
            gc = int(center_col[1] * (1 - t) + edge_col[1] * t)
            bc = int(center_col[2] * (1 - t) + edge_col[2] * t)
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(rc, gc, bc))

    # ── Product shape ─────────────────────────────────────────────────────────

    def _draw_product(self, draw, cx, cy, w, h, brand, category):
        unit = min(w, h) // 4

        if category in ("drink", "beverage", "energy", "coffee"):
            self._draw_can(draw, cx, cy, unit, brand)
        elif category in ("bar", "snack", "food"):
            self._draw_bar(draw, cx, cy, unit, brand)
        elif category in ("tech", "electronics"):
            self._draw_device(draw, cx, cy, unit, brand)
        elif category in ("beauty", "skincare", "serum"):
            self._draw_bottle(draw, cx, cy, unit, brand)
        else:
            self._draw_orb(draw, cx, cy, unit, brand)

    def _draw_can(self, draw, cx, cy, unit, brand):
        cw = int(unit * 0.72)
        ch = int(unit * 1.80)
        x1, y1 = cx - cw // 2, cy - ch // 2
        x2, y2 = x1 + cw, y1 + ch
        draw.rounded_rectangle([x1, y1, x2, y2], radius=cw // 3, fill=brand)
        # Highlight stripe (studio light reflection)
        hw = max(6, cw // 6)
        hx = x1 + cw // 4
        hl = _lighten_rgb(brand, 0.45)
        draw.rounded_rectangle([hx, y1 + 8, hx + hw, y2 - 8], radius=hw // 2, fill=(*hl, 180))
        # Top cap
        cap_h = max(8, ch // 16)
        dk    = _darken_rgb(brand, 0.15)
        draw.ellipse([x1, y1, x2, y1 + cap_h * 2], fill=dk)
        # Bottom cap
        draw.ellipse([x1, y2 - cap_h * 2, x2, y2], fill=dk)

    def _draw_bar(self, draw, cx, cy, unit, brand):
        bw = int(unit * 1.60)
        bh = int(unit * 0.70)
        x1, y1 = cx - bw // 2, cy - bh // 2
        dk = _darken_rgb(brand, 0.15)
        # Wrapper
        draw.rounded_rectangle([x1, y1, x1 + bw, y1 + bh], radius=14, fill=brand)
        # Inner wrapper stripe
        hl = _lighten_rgb(brand, 0.30)
        draw.rounded_rectangle([x1 + 10, y1 + 10, x1 + bw - 10, y1 + bh - 10],
                                radius=8, fill=hl)
        # Bottom face (3D depth)
        depth = max(8, bh // 6)
        draw.rectangle([x1 + 4, y1 + bh, x1 + bw - 4, y1 + bh + depth], fill=dk)

    def _draw_device(self, draw, cx, cy, unit, brand):
        dw = int(unit * 1.20)
        dh = int(unit * 1.55)
        x1, y1 = cx - dw // 2, cy - dh // 2
        dark = _darken_rgb(brand, 0.18)
        draw.rounded_rectangle([x1, y1, x1 + dw, y1 + dh], radius=18, fill=dark)
        # Screen
        sx, sy = x1 + 10, y1 + 18
        sw, sh = dw - 20, dh - 36
        draw.rectangle([sx, sy, sx + sw, sy + sh], fill=brand)
        # Screen glare
        hl = _lighten_rgb(brand, 0.38)
        draw.polygon([(sx, sy), (sx + sw // 3, sy), (sx, sy + sh // 4)], fill=(*hl, 100))
        # Home button
        r = max(5, dw // 10)
        bcx, bcy = cx, y1 + dh - r - 8
        draw.ellipse([bcx - r, bcy - r, bcx + r, bcy + r], fill=dark)

    def _draw_bottle(self, draw, cx, cy, unit, brand):
        bw = int(unit * 0.68)
        bh = int(unit * 1.65)
        x1, y1 = cx - bw // 2, cy - bh // 2
        # Body
        draw.rounded_rectangle([x1, y1 + bh // 5, x1 + bw, y1 + bh],
                                radius=bw // 3, fill=brand)
        # Neck
        nw = bw // 3
        nx = cx - nw // 2
        draw.rectangle([nx, y1, nx + nw, y1 + bh // 4], fill=brand)
        # Cap
        dk = _darken_rgb(brand, 0.20)
        draw.rounded_rectangle([nx - 2, y1, nx + nw + 2, y1 + bh // 8],
                                radius=4, fill=dk)
        # Highlight
        hl = _lighten_rgb(brand, 0.40)
        hw = max(5, bw // 8)
        draw.rounded_rectangle([x1 + bw // 5, y1 + bh // 4, x1 + bw // 5 + hw, y1 + bh - 16],
                                radius=hw // 2, fill=(*hl, 160))

    def _draw_orb(self, draw, cx, cy, unit, brand):
        r  = int(unit * 0.85)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=brand)
        # Highlight
        hl = _lighten_rgb(brand, 0.45)
        hr = r // 3
        draw.ellipse([cx - r + hr // 2, cy - r + hr // 2,
                      cx - r + hr * 2, cy - r + hr * 2], fill=(*hl, 180))

    def _draw_ground_shadow(self, draw, cx, cy, w, h):
        """Soft elliptical contact shadow below the product."""
        sw = int(w * 0.36)
        sh = int(h * 0.04)
        sx = cx - sw // 2
        sy = int(cy + h * 0.26)
        # Multi-layer for softness
        for i in range(12):
            t = i / 12
            a = int(55 * (1 - t))
            ex = int(sw * (1 + t * 0.5))
            ey = int(sh * (1 + t * 1.0))
            draw.ellipse([cx - ex // 2, sy - ey // 2, cx + ex // 2, sy + ey // 2],
                         fill=(60, 60, 65, a))


# ── OpenAI provider ───────────────────────────────────────────────────────────

class OpenAIImageProvider(BaseImageProvider):
    """
    Generates product images via OpenAI DALL-E 3.
    Falls back to MockImageProvider if the API call fails.

    Requires: pip install openai
    Config:   OPENAI_API_KEY in environment
    """

    name = "openai"

    def __init__(self, api_key: str):
        try:
            from openai import OpenAI as _OpenAI
            self._client = _OpenAI(api_key=api_key)
        except ImportError as e:
            raise RuntimeError(
                "openai package is not installed. Run: pip install openai"
            ) from e

    def generate(
        self,
        product_name: str,
        description: str,
        width: int,
        height: int,
        primary_color: str,
        campaign_message: str = "",
        region: str = "",
        target_audience: str = "",
    ) -> Image.Image:
        prompt = self._build_prompt(
            product_name, description, campaign_message, region, target_audience, primary_color
        )
        logger.info("[OpenAIImageProvider] Generating image for '%s'", product_name)
        logger.debug("Prompt: %s", prompt)

        response = self._client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size="1024x1024",
            quality="standard",
        )
        image_url = response.data[0].url

        with urllib.request.urlopen(image_url) as resp:
            img_bytes = resp.read()

        return Image.open(io.BytesIO(img_bytes)).convert("RGB")

    def _build_prompt(
        self,
        product_name: str,
        description: str,
        campaign_message: str,
        region: str,
        target_audience: str,
        primary_color: str,
    ) -> str:
        category  = _detect_category(product_name, description)
        style_mod = _category_photo_style(category)

        parts = [
            f"Commercial advertising product photography of '{product_name}'.",
            f"{description}." if description else "",
            style_mod,
            "Neutral studio sweep background, professional three-point lighting.",
            "Shallow depth of field, crisp product focus. No text. No logos.",
            f"Campaign theme: {campaign_message}." if campaign_message else "",
        ]
        return " ".join(p for p in parts if p)


# ── Gemini provider ───────────────────────────────────────────────────────────

def list_gemini_image_models(api_key: str) -> None:
    """
    Diagnostic helper — prints all Gemini models that support image output.
    Run this if you're getting 404s to find the correct model name for your key.

    Usage:
        from src.image_generator import list_gemini_image_models
        list_gemini_image_models("your-api-key")
    """
    try:
        from google import genai as _genai
    except ImportError:
        print("google-genai not installed. Run: pip install google-genai")
        return

    client = _genai.Client(api_key=api_key)
    print("\n── Available Gemini models ──────────────────────────────")
    image_capable = []
    for model in client.models.list():
        actions = getattr(model, "supported_actions", None) or []
        methods = getattr(model, "supported_generation_methods", None) or []
        combined = list(actions) + list(methods)
        is_image = any(
            kw in str(m).lower()
            for m in combined
            for kw in ("image", "generate_content")
        )
        marker = "  [image]" if is_image else ""
        print(f"  {model.name}{marker}")
        if is_image:
            image_capable.append(model.name)

    print("\n── Image-capable models ─────────────────────────────────")
    if image_capable:
        for m in image_capable:
            print(f"  {m}")
    else:
        print("  (none detected — check supported_actions manually)")
    print()


class GeminiImageProvider(BaseImageProvider):
    """
    Generates product images via Google Gemini image generation.

    Uses gemini-2.5-flash-image via generate_content with
    response_modalities=["IMAGE", "TEXT"].

    If the model returns a 404, logs all available models with image
    support to the terminal and raises so ImageGenerator falls back to mock.

    Requires: pip install google-genai
    Config:   GEMINI_API_KEY in environment
    """

    name = "gemini"

    # Update this if Google renames the model again.
    _MODEL = "gemini-2.5-flash-image"

    def __init__(self, api_key: str):
        try:
            from google import genai as _genai
            from google.genai import types as _types
            self._client = _genai.Client(api_key=api_key)
            self._types = _types
            self._api_key = api_key
        except ImportError as e:
            raise RuntimeError(
                "google-genai package is not installed. Run: pip install google-genai"
            ) from e

    def generate(
        self,
        product_name: str,
        description: str,
        width: int,
        height: int,
        primary_color: str,
        campaign_message: str = "",
        region: str = "",
        target_audience: str = "",
    ) -> Image.Image:
        prompt = self._build_prompt(
            product_name, description, campaign_message, region, target_audience, primary_color
        )
        logger.info("[GeminiImageProvider] model=%s  product='%s'", self._MODEL, product_name)
        logger.debug("Prompt: %s", prompt)

        try:
            return self._call(prompt)
        except Exception as e:
            err_str = str(e)
            if "404" in err_str or "not found" in err_str.lower():
                logger.error(
                    "[GeminiImageProvider] 404 — model '%s' not found or not supported on this key.",
                    self._MODEL,
                )
                self._log_available_models()
            raise

    def _call(self, prompt: str) -> Image.Image:
        response = self._client.models.generate_content(
            model=self._MODEL,
            contents=prompt,
            config=self._types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                return Image.open(io.BytesIO(part.inline_data.data)).convert("RGB")
        raise RuntimeError(
            f"Model '{self._MODEL}' returned no image data. "
            "The model may not support image output on this key tier."
        )

    def _log_available_models(self) -> None:
        """Print image-capable models to the terminal to help the user fix their config."""
        try:
            print("\n" + "─" * 60)
            print("  GEMINI DIAGNOSTIC — image-capable models on your key")
            print("─" * 60)
            image_capable = []
            for model in self._client.models.list():
                actions = list(getattr(model, "supported_actions", None) or [])
                methods = list(getattr(model, "supported_generation_methods", None) or [])
                combined = actions + methods
                is_image = any(
                    kw in str(m).lower()
                    for m in combined
                    for kw in ("image",)
                ) or "generateContent" in combined
                marker = "  ← image output" if is_image else ""
                print(f"  {model.name}{marker}")
                if is_image:
                    image_capable.append(model.name)

            print("─" * 60)
            if image_capable:
                print("  Image-capable:")
                for m in image_capable:
                    print(f"    {m}")
                print(f"\n  → Set _MODEL = '<model_name>' in GeminiImageProvider")
                print(f"    File: src/image_generator.py  (search: _MODEL =)")
            else:
                print("  No image-capable models detected.")
                print("  Your API key may not have image generation access.")
            print("─" * 60 + "\n")
        except Exception as diag_err:
            logger.warning("Could not list Gemini models: %s", diag_err)

    def _build_prompt(
        self,
        product_name: str,
        description: str,
        campaign_message: str,
        region: str,
        target_audience: str,
        primary_color: str,
    ) -> str:
        category  = _detect_category(product_name, description)
        style_mod = _category_photo_style(category)

        parts = [
            f"Commercial product photography of '{product_name}'.",
            f"{description}." if description else "",
            style_mod,
            "Shot on a neutral studio background with clean, professional lighting.",
            "Shallow depth of field, sharp product focus.",
            "High-end advertising quality. No text, no labels, no logos.",
            f"Campaign mood: {campaign_message}." if campaign_message else "",
            f"Target market: {region}." if region else "",
        ]
        return " ".join(p for p in parts if p)


# ── Orchestrator ──────────────────────────────────────────────────────────────

class ImageGenerator:
    """Runs generation through the configured provider with automatic fallback."""

    def __init__(self, provider: BaseImageProvider | None = None):
        self.provider = provider or MockImageProvider()

    @classmethod
    def from_env(cls) -> "ImageGenerator":
        """Construct from IMAGE_PROVIDER and API key environment variables."""
        provider_name = os.environ.get("IMAGE_PROVIDER", "mock").lower().strip()

        if provider_name == "openai":
            api_key = os.environ.get("OPENAI_API_KEY", "").strip()
            if not api_key:
                logger.warning("IMAGE_PROVIDER=openai but OPENAI_API_KEY is not set — falling back to mock.")
                return cls(provider=MockImageProvider())
            try:
                return cls(provider=OpenAIImageProvider(api_key=api_key))
            except RuntimeError as e:
                logger.warning("Could not initialise OpenAI provider: %s — falling back to mock.", e)
                return cls(provider=MockImageProvider())

        if provider_name == "gemini":
            api_key = os.environ.get("GEMINI_API_KEY", "").strip()
            if not api_key:
                logger.warning("IMAGE_PROVIDER=gemini but GEMINI_API_KEY is not set — falling back to mock.")
                return cls(provider=MockImageProvider())
            try:
                return cls(provider=GeminiImageProvider(api_key=api_key))
            except RuntimeError as e:
                logger.warning("Could not initialise Gemini provider: %s — falling back to mock.", e)
                return cls(provider=MockImageProvider())

        if provider_name != "mock":
            logger.warning("Unknown IMAGE_PROVIDER '%s' — using mock.", provider_name)

        return cls(provider=MockImageProvider())

    def generate_product_image(
        self,
        product_name: str,
        description: str,
        width: int,
        height: int,
        primary_color: str = "#1E293B",
        campaign_message: str = "",
        region: str = "",
        target_audience: str = "",
    ) -> tuple[Image.Image, str]:
        """
        Generate a product image.
        Returns (image, provider_name_used).
        Falls back to MockImageProvider if the configured provider raises.
        """
        try:
            img = self.provider.generate(
                product_name=product_name,
                description=description,
                width=width,
                height=height,
                primary_color=primary_color,
                campaign_message=campaign_message,
                region=region,
                target_audience=target_audience,
            )
            return img, self.provider.name
        except Exception as e:
            logger.warning(
                "Provider '%s' failed for '%s': %s — falling back to mock.",
                self.provider.name, product_name, e,
            )
            fallback = MockImageProvider()
            img = fallback.generate(
                product_name=product_name,
                description=description,
                width=width,
                height=height,
                primary_color=primary_color,
            )
            return img, "mock (fallback)"


# ── Category detection and photography styles ─────────────────────────────────

def _detect_category(product_name: str, description: str) -> str:
    """Keyword-based product category detection for prompt/mock customisation."""
    combined = (product_name + " " + description).lower()
    if any(k in combined for k in ("drink", "beverage", "energy", "soda", "juice", "water", "coffee", "tea", "brew")):
        return "drink"
    if any(k in combined for k in ("coffee", "espresso", "latte", "cappuccino", "roast", "bean")):
        return "coffee"
    if any(k in combined for k in ("bar", "snack", "protein", "cookie", "chip", "cracker", "food", "nutrition", "granola")):
        return "bar"
    if any(k in combined for k in ("phone", "laptop", "headphone", "speaker", "camera", "tablet", "tech", "electronic", "device", "earbu", "watch")):
        return "tech"
    if any(k in combined for k in ("serum", "cream", "skincare", "beauty", "moistur", "sunscreen", "lotion", "perfume", "fragrance", "makeup", "lipstick")):
        return "beauty"
    if any(k in combined for k in ("shirt", "jacket", "shoe", "sneaker", "apparel", "wear", "clothing", "fashion", "denim", "boot")):
        return "fashion"
    if any(k in combined for k in ("outdoor", "hiking", "camping", "sport", "fitness", "gym", "yoga", "running", "athlet")):
        return "outdoor"
    return "default"


def _category_photo_style(category: str) -> str:
    """Return a lighting/composition modifier string for the given category."""
    styles = {
        "drink":    "Dynamic pour shot or condensation-covered can on clean surface. Vivid, saturated, refreshing feel.",
        "coffee":   "Warm café atmosphere, steam rising, artisan presentation on wood or slate surface.",
        "bar":      "Rustic texture, natural light from the side, whole ingredients scattered around the product.",
        "tech":     "Minimal studio, clean reflective surface, blue-tinted ambient light. Precision product shot.",
        "beauty":   "Soft diffused light, marble or glass surface, luxury editorial feel. Subtle shadows.",
        "fashion":  "On a clean white or concrete surface. Natural daylight, lifestyle context suggested.",
        "outdoor":  "Natural setting with dramatic light. Rocky, mossy, or natural textures in background.",
        "default":  "Clean neutral studio background, soft box lighting, product centered on smooth surface.",
    }
    return styles.get(category, styles["default"])


def _lighten_rgb(rgb: tuple, amount: float) -> tuple:
    import colorsys
    r, g, b = (x / 255 for x in rgb)
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    r2, g2, b2 = colorsys.hls_to_rgb(h, min(1.0, l + amount), s)
    return (int(r2 * 255), int(g2 * 255), int(b2 * 255))


def _darken_rgb(rgb: tuple, amount: float) -> tuple:
    import colorsys
    r, g, b = (x / 255 for x in rgb)
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    r2, g2, b2 = colorsys.hls_to_rgb(h, max(0.0, l - amount), s)
    return (int(r2 * 255), int(g2 * 255), int(b2 * 255))


# ── Shared font loader ────────────────────────────────────────────────────────

def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = (
        ["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"] if bold
        else ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf"]
    )
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()
