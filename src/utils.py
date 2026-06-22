import re
import os


def normalize_name(name: str) -> str:
    """Normalize a product or file name for comparison/filesystem use."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def safe_folder_name(name: str) -> str:
    """Produce a safe filesystem folder name from a product name."""
    return re.sub(r"[^\w\s-]", "", name).strip().replace(" ", "_")


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert a hex color string to an (R, G, B) tuple."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return (30, 41, 59)  # fallback slate-800
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def allowed_file(filename: str, allowed_extensions: set[str]) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


def find_asset_for_product(product_name: str, upload_folder: str) -> str | None:
    """
    Search upload_folder for an image that matches the product name.
    Matches normalized product name against normalized filenames.
    """
    target = normalize_name(product_name)
    if not os.path.isdir(upload_folder):
        return None
    for fname in os.listdir(upload_folder):
        base, ext = os.path.splitext(fname)
        if ext.lower().lstrip(".") in {"png", "jpg", "jpeg", "webp"}:
            if normalize_name(base) == target:
                return os.path.join(upload_folder, fname)
    return None
