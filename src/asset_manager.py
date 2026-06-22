import os
import logging
from src.utils import find_asset_for_product
from src.config import UPLOAD_FOLDER

logger = logging.getLogger(__name__)


class AssetManager:
    """
    Locates product images from uploaded files or a local assets folder.
    Returns the path to the best matching image for each product, or None.
    """

    def __init__(self, upload_folder: str = UPLOAD_FOLDER, local_assets_folder: str | None = None):
        self.upload_folder = upload_folder
        self.local_assets_folder = local_assets_folder

    def resolve(self, product_name: str) -> tuple[str | None, str]:
        """
        Return (image_path, source_label) where source_label is 'uploaded', 'local', or 'none'.
        """
        path = find_asset_for_product(product_name, self.upload_folder)
        if path:
            logger.info("Asset matched from uploads for '%s': %s", product_name, path)
            return path, "uploaded"

        if self.local_assets_folder:
            path = find_asset_for_product(product_name, self.local_assets_folder)
            if path:
                logger.info("Asset matched from local folder for '%s': %s", product_name, path)
                return path, "local"

        logger.info("No asset found for '%s'; will generate mock.", product_name)
        return None, "none"
