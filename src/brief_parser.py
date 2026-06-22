import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Product:
    name: str
    description: str = ""


@dataclass
class Brand:
    name: str = ""
    primary_color: str = "#1E293B"
    secondary_color: str = "#F8FAFC"
    logo_required: bool = False


@dataclass
class CampaignBrief:
    campaign_name: str
    region: str
    target_audience: str
    campaign_message: str
    products: list[Product]
    brand: Brand = field(default_factory=Brand)


class BriefValidationError(Exception):
    pass


def parse_brief(raw: str | dict) -> CampaignBrief:
    """Parse and validate campaign brief from JSON string or dict."""
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise BriefValidationError(f"Invalid JSON: {e}") from e
    else:
        data = raw

    _require_fields(data, ["campaign_name", "region", "target_audience", "campaign_message", "products"])

    products_raw = data["products"]
    if not isinstance(products_raw, list) or len(products_raw) < 2:
        raise BriefValidationError("Brief must include at least two products.")

    products = []
    for i, p in enumerate(products_raw):
        if not isinstance(p, dict) or not p.get("name", "").strip():
            raise BriefValidationError(f"Product at index {i} is missing a name.")
        products.append(Product(name=p["name"].strip(), description=p.get("description", "")))

    brand_data = data.get("brand", {})
    brand = Brand(
        name=brand_data.get("name", ""),
        primary_color=brand_data.get("primary_color", "#1E293B"),
        secondary_color=brand_data.get("secondary_color", "#F8FAFC"),
        logo_required=bool(brand_data.get("logo_required", False)),
    )

    return CampaignBrief(
        campaign_name=data["campaign_name"].strip(),
        region=data["region"].strip(),
        target_audience=data["target_audience"].strip(),
        campaign_message=data["campaign_message"].strip(),
        products=products,
        brand=brand,
    )


def _require_fields(data: dict, fields: list[str]) -> None:
    for f in fields:
        value = data.get(f)
        if value is None:
            raise BriefValidationError(f"Missing required field: '{f}'.")
        if isinstance(value, str) and not value.strip():
            raise BriefValidationError(f"Field '{f}' must not be empty.")
