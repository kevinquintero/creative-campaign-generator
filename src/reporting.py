import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def write_report(
    output_folder: str,
    campaign_name: str,
    products_processed: list[str],
    assets_reused: list[str],
    assets_generated: list[str],
    outputs_created: list[str],
    compliance_warnings: list[str],
    errors: list[str],
    generation_providers: dict[str, str] | None = None,
) -> str:
    """Write run_report.json and return its path."""
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "campaign_name": campaign_name,
        "products_processed": products_processed,
        "assets_reused": assets_reused,
        "assets_generated": assets_generated,
        "generation_providers": generation_providers or {},
        "outputs_created": outputs_created,
        "compliance_warnings": compliance_warnings,
        "errors": errors,
        "summary": {
            "total_products": len(products_processed),
            "total_outputs": len(outputs_created),
            "reused_count": len(assets_reused),
            "generated_count": len(assets_generated),
            "warning_count": len(compliance_warnings),
            "error_count": len(errors),
        },
    }

    os.makedirs(output_folder, exist_ok=True)
    path = os.path.join(output_folder, "run_report.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logger.info("Run report written: %s", path)
    return path
