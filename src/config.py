import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "output")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

ASPECT_RATIOS = {
    "1x1":  (1080, 1080),
    "9x16": (1080, 1920),
    "16x9": (1920, 1080),
}

PROHIBITED_WORDS = [
    "guaranteed cure",
    "free money",
    "miracle",
    "risk free",
]

# Brand defaults used when brief doesn't specify
DEFAULT_PRIMARY_COLOR = "#1E293B"
DEFAULT_SECONDARY_COLOR = "#F8FAFC"
DEFAULT_ACCENT_COLOR = "#22C55E"

MAX_BRIEF_SIZE_BYTES = 1 * 1024 * 1024  # 1 MB
MAX_ASSET_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
