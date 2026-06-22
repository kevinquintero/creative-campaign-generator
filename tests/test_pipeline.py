"""
Pipeline integration tests.
Run: pytest tests/ -v
"""

import json
import os
import shutil
import tempfile

import pytest

from src.brief_parser import BriefValidationError, parse_brief
from src.compliance import check_message, check_outputs
from src.config import ASPECT_RATIOS
from src.creative_builder import CreativeBuilder
from src.image_generator import ImageGenerator, MockImageProvider
from src.reporting import write_report
from src.utils import normalize_name, find_asset_for_product, safe_folder_name


# ── Brief parser ──────────────────────────────────────────────────────────────

VALID_BRIEF = {
    "campaign_name": "Summer Launch",
    "region": "United States",
    "target_audience": "Young adults",
    "campaign_message": "Fuel your day anywhere",
    "products": [
        {"name": "Spark Energy Drink", "description": "Citrus energy drink"},
        {"name": "Pure Protein Bar",   "description": "High protein snack"},
    ],
    "brand": {"primary_color": "#1E3A5F", "secondary_color": "#FFFFFF"},
}


def test_parse_valid_brief():
    brief = parse_brief(VALID_BRIEF)
    assert brief.campaign_name == "Summer Launch"
    assert len(brief.products) == 2
    assert brief.products[0].name == "Spark Energy Drink"


def test_parse_brief_from_json_string():
    brief = parse_brief(json.dumps(VALID_BRIEF))
    assert brief.campaign_name == "Summer Launch"


def test_parse_brief_missing_field():
    bad = {**VALID_BRIEF}
    del bad["campaign_message"]
    with pytest.raises(BriefValidationError, match="campaign_message"):
        parse_brief(bad)


def test_parse_brief_too_few_products():
    bad = {**VALID_BRIEF, "products": [{"name": "One Product"}]}
    with pytest.raises(BriefValidationError, match="at least two"):
        parse_brief(bad)


def test_parse_brief_product_missing_name():
    bad = {**VALID_BRIEF, "products": [{"description": "no name"}, {"name": "Second"}]}
    with pytest.raises(BriefValidationError, match="missing a name"):
        parse_brief(bad)


def test_parse_brief_invalid_json():
    with pytest.raises(BriefValidationError, match="Invalid JSON"):
        parse_brief("not json {{{")


def test_sample_campaign_json_is_valid():
    """Verify the committed sample_campaign.json passes validation."""
    sample_path = os.path.join(os.path.dirname(__file__), "..", "sample_campaign.json")
    with open(sample_path) as f:
        data = json.load(f)
    brief = parse_brief(data)
    assert len(brief.products) >= 2


# ── Compliance ────────────────────────────────────────────────────────────────

def test_compliance_clean_message():
    assert check_message("Fuel your day anywhere") == []


def test_compliance_prohibited_word():
    warnings = check_message("This is a miracle product")
    assert any("miracle" in w for w in warnings)


def test_compliance_empty_message():
    warnings = check_message("")
    assert any("empty" in w.lower() for w in warnings)


# ── Image generator ───────────────────────────────────────────────────────────

def test_mock_provider_generates_image():
    provider = MockImageProvider()
    img = provider.generate("Test Product", "A test product", 400, 400, "#1E3A5F")
    assert img.size == (400, 400)
    assert img.mode == "RGB"


def test_image_generator_defaults_to_mock():
    gen = ImageGenerator()
    img, provider_name = gen.generate_product_image("Test", "Desc", 200, 200)
    assert img.size == (200, 200)
    assert provider_name == "mock"


def test_image_generator_from_env_defaults_to_mock(monkeypatch):
    monkeypatch.delenv("IMAGE_PROVIDER", raising=False)
    gen = ImageGenerator.from_env()
    assert gen.provider.name == "mock"


def test_image_generator_from_env_openai_missing_key(monkeypatch):
    monkeypatch.setenv("IMAGE_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    gen = ImageGenerator.from_env()
    assert gen.provider.name == "mock"


def test_image_generator_from_env_gemini_missing_key(monkeypatch):
    monkeypatch.setenv("IMAGE_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    gen = ImageGenerator.from_env()
    # Falls back to mock when key is absent
    assert gen.provider.name == "mock"


def test_image_generator_from_env_unknown_provider_falls_back(monkeypatch):
    monkeypatch.setenv("IMAGE_PROVIDER", "notreal")
    gen = ImageGenerator.from_env()
    assert gen.provider.name == "mock"


def test_gemini_provider_uses_single_model_constant():
    """GeminiImageProvider must have exactly one _MODEL constant (no dead model names)."""
    from src.image_generator import GeminiImageProvider
    assert hasattr(GeminiImageProvider, "_MODEL")
    assert not hasattr(GeminiImageProvider, "_IMAGEN_MODEL")
    assert not hasattr(GeminiImageProvider, "_FLASH_MODEL")
    assert "gemini" in GeminiImageProvider._MODEL.lower()


def test_gemini_404_falls_back_to_mock():
    """A 404 from the Gemini API causes ImageGenerator to fall back to mock."""
    from src.image_generator import BaseImageProvider

    class FakeGeminiProvider(BaseImageProvider):
        name = "gemini"
        def generate(self, *args, **kwargs):
            raise Exception("404 models/gemini-x is not found for API version v1beta")

    gen = ImageGenerator(provider=FakeGeminiProvider())
    img, provider_name = gen.generate_product_image("Test", "Desc", 200, 200)
    assert img.size == (200, 200)
    assert "fallback" in provider_name


def test_image_generator_fallback_on_provider_error():
    """If the configured provider raises, ImageGenerator falls back to mock."""
    from src.image_generator import BaseImageProvider

    class BrokenProvider(BaseImageProvider):
        name = "broken"
        def generate(self, *args, **kwargs):
            raise RuntimeError("simulated API failure")

    gen = ImageGenerator(provider=BrokenProvider())
    img, provider_name = gen.generate_product_image("Test", "Desc", 200, 200)
    assert img.size == (200, 200)
    assert "fallback" in provider_name


# ── Utils ─────────────────────────────────────────────────────────────────────

def test_normalize_name():
    assert normalize_name("Spark Energy Drink") == "spark_energy_drink"
    assert normalize_name("Pure Protein Bar!") == "pure_protein_bar"


def test_find_asset_matches_normalized(tmp_path):
    (tmp_path / "spark_energy_drink.png").write_bytes(b"")
    result = find_asset_for_product("Spark Energy Drink", str(tmp_path))
    assert result is not None
    assert "spark_energy_drink" in result


def test_find_asset_no_match(tmp_path):
    assert find_asset_for_product("Ghost Product", str(tmp_path)) is None


# ── Full pipeline integration ─────────────────────────────────────────────────

def test_pipeline_runs_end_to_end():
    """
    Full pipeline: parse brief → generate images → build creatives → report.
    Verifies outputs exist for all products × all aspect ratios.
    """
    brief = parse_brief(VALID_BRIEF)
    gen = ImageGenerator()

    with tempfile.TemporaryDirectory() as out_dir:
        builder = CreativeBuilder(output_folder=out_dir)
        outputs_created = []

        for product in brief.products:
            img, _provider = gen.generate_product_image(
                product_name=product.name,
                description=product.description,
                width=400, height=400,
                primary_color=brief.brand.primary_color,
            )
            ratio_paths = builder.build(
                product_name=product.name,
                product_image=img,
                campaign_message=brief.campaign_message,
                region=brief.region,
                brand_primary=brief.brand.primary_color,
                brand_secondary=brief.brand.secondary_color,
            )
            outputs_created.extend(ratio_paths.values())

        # All outputs must exist
        assert len(outputs_created) == len(brief.products) * len(ASPECT_RATIOS)
        for path in outputs_created:
            assert os.path.isfile(path), f"Missing: {path}"
            assert os.path.getsize(path) > 0, f"Empty file: {path}"

        # Each product must have all three ratios
        for product in brief.products:
            folder = safe_folder_name(product.name)
            for ratio_key in ASPECT_RATIOS:
                p = os.path.join(out_dir, folder, ratio_key, "final.png")
                assert os.path.isfile(p), f"Missing ratio output: {p}"

        # Report
        product_names = [p.name for p in brief.products]
        report_path = write_report(
            output_folder=out_dir,
            campaign_name=brief.campaign_name,
            products_processed=product_names,
            assets_reused=[],
            assets_generated=product_names,
            outputs_created=outputs_created,
            compliance_warnings=[],
            errors=[],
        )
        assert os.path.isfile(report_path)
        with open(report_path) as f:
            report = json.load(f)
        assert report["campaign_name"] == "Summer Launch"
        assert report["summary"]["total_outputs"] == len(outputs_created)

        # Compliance check on completed outputs
        output_warnings = check_outputs(out_dir, product_names)
        assert output_warnings == [], f"Unexpected compliance failures: {output_warnings}"
