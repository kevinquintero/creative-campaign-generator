"""
Basic brand compliance checks.
Flags prohibited words and validates output completeness.
"""

import os
import logging
from src.config import PROHIBITED_WORDS, ASPECT_RATIOS
from src.utils import safe_folder_name

logger = logging.getLogger(__name__)


def check_message(campaign_message: str) -> list[str]:
    """Return list of compliance warnings for the campaign message."""
    warnings = []
    msg_lower = campaign_message.lower()

    if not campaign_message.strip():
        warnings.append("Campaign message is empty.")

    for word in PROHIBITED_WORDS:
        if word in msg_lower:
            warnings.append(f"Prohibited phrase detected in campaign message: '{word}'.")

    return warnings


def check_outputs(output_folder: str, product_names: list[str]) -> list[str]:
    """Verify all expected output files exist."""
    warnings = []
    for name in product_names:
        folder = safe_folder_name(name)
        for ratio_key in ASPECT_RATIOS:
            path = os.path.join(output_folder, folder, ratio_key, "final.png")
            if not os.path.isfile(path):
                warnings.append(f"Missing output: {folder}/{ratio_key}/final.png")
    return warnings
