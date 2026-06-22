"""
Creative Automation Pipeline — Flask entry point.
Run: python app.py
"""

import json
import logging
import os
import shutil
import zipfile
from io import BytesIO

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, send_file, url_for
from PIL import Image
from werkzeug.utils import secure_filename

from src.asset_manager import AssetManager
from src.brief_parser import BriefValidationError, parse_brief
from src.compliance import check_message, check_outputs
from src.config import (
    ALLOWED_EXTENSIONS,
    MAX_BRIEF_SIZE_BYTES,
    OUTPUT_FOLDER,
    UPLOAD_FOLDER,
)
from src.creative_builder import CreativeBuilder
from src.image_generator import ImageGenerator
from src.reporting import write_report
from src.utils import allowed_file

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def _active_provider_label() -> str:
    """Return a human-readable label for the currently configured provider."""
    name = os.environ.get("IMAGE_PROVIDER", "mock").lower()
    if name == "openai":
        return "OpenAI (DALL-E 3)" if os.environ.get("OPENAI_API_KEY", "").strip() else "Mock (OpenAI key missing)"
    if name == "gemini":
        return "Google Gemini (Imagen 3)" if os.environ.get("GEMINI_API_KEY", "").strip() else "Mock (Gemini key missing)"
    return "Mock (local)"


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", active_provider=_active_provider_label())


@app.route("/generate", methods=["POST"])
def generate():
    errors = []
    warnings = []

    # --- Parse brief ---
    brief_file = request.files.get("brief_file")
    brief_text = request.form.get("brief_text", "").strip()

    raw_brief = None
    if brief_file and brief_file.filename:
        if brief_file.content_length and brief_file.content_length > MAX_BRIEF_SIZE_BYTES:
            errors.append("Brief file exceeds 1 MB limit.")
        else:
            raw_brief = brief_file.read().decode("utf-8", errors="replace")
    elif brief_text:
        raw_brief = brief_text

    if not raw_brief:
        flash("Please provide a campaign brief (file upload or paste JSON).", "error")
        return redirect(url_for("index"))

    try:
        brief = parse_brief(raw_brief)
    except BriefValidationError as e:
        flash(f"Brief validation failed: {e}", "error")
        return redirect(url_for("index"))

    # --- Compliance: message ---
    warnings.extend(check_message(brief.campaign_message))

    # --- Clear previous run ---
    _clear_folder(UPLOAD_FOLDER)
    _clear_folder(OUTPUT_FOLDER)

    # --- Save uploaded assets ---
    for f in request.files.getlist("assets"):
        if f and f.filename and allowed_file(f.filename, ALLOWED_EXTENSIONS):
            f.save(os.path.join(UPLOAD_FOLDER, secure_filename(f.filename)))

    # --- Initialise pipeline components ---
    asset_manager = AssetManager(upload_folder=UPLOAD_FOLDER)
    image_gen = ImageGenerator.from_env()
    creative_builder = CreativeBuilder(output_folder=OUTPUT_FOLDER)

    assets_reused = []
    assets_generated = []
    generation_providers: dict[str, str] = {}
    outputs_created = []
    product_names = []

    for product in brief.products:
        product_names.append(product.name)
        asset_path, _source = asset_manager.resolve(product.name)

        if asset_path:
            product_img = Image.open(asset_path).convert("RGB")
            assets_reused.append(product.name)
        else:
            product_img, provider_used = image_gen.generate_product_image(
                product_name=product.name,
                description=product.description,
                width=1024,
                height=1024,
                primary_color=brief.brand.primary_color,
                campaign_message=brief.campaign_message,
                region=brief.region,
                target_audience=brief.target_audience,
            )
            assets_generated.append(product.name)
            generation_providers[product.name] = provider_used

        ratio_paths = creative_builder.build(
            product_name=product.name,
            product_image=product_img,
            campaign_message=brief.campaign_message,
            region=brief.region,
            brand_primary=brief.brand.primary_color,
            brand_secondary=brief.brand.secondary_color,
            brand_name=brief.brand.name,
        )
        outputs_created.extend(ratio_paths.values())

    # --- Compliance: outputs ---
    warnings.extend(check_outputs(OUTPUT_FOLDER, product_names))

    # --- Report ---
    report_path = write_report(
        output_folder=OUTPUT_FOLDER,
        campaign_name=brief.campaign_name,
        products_processed=product_names,
        assets_reused=assets_reused,
        assets_generated=assets_generated,
        outputs_created=outputs_created,
        compliance_warnings=warnings,
        errors=errors,
        generation_providers=generation_providers,
    )

    report_data = json.loads(open(report_path).read())
    previews = _build_preview_data(brief.products, OUTPUT_FOLDER)

    return render_template(
        "results.html",
        brief=brief,
        previews=previews,
        report=report_data,
        warnings=warnings,
        errors=errors,
        active_provider=_active_provider_label(),
    )


@app.route("/output/<path:filename>")
def serve_output(filename):
    return send_file(os.path.join(OUTPUT_FOLDER, filename))


@app.route("/download-zip")
def download_zip():
    if not os.path.isdir(OUTPUT_FOLDER) or not os.listdir(OUTPUT_FOLDER):
        flash("No outputs to download. Run the pipeline first.", "error")
        return redirect(url_for("index"))

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(OUTPUT_FOLDER):
            for fname in files:
                fpath = os.path.join(root, fname)
                zf.write(fpath, os.path.relpath(fpath, OUTPUT_FOLDER))
    buf.seek(0)
    return send_file(buf, mimetype="application/zip", as_attachment=True, download_name="campaign_output.zip")


def _build_preview_data(products, output_folder: str) -> list[dict]:
    from src.config import ASPECT_RATIOS
    from src.utils import safe_folder_name

    previews = []
    for product in products:
        folder = safe_folder_name(product.name)
        ratios = {}
        for ratio_key in ASPECT_RATIOS:
            abs_path = os.path.join(output_folder, folder, ratio_key, "final.png")
            if os.path.isfile(abs_path):
                rel = os.path.join(folder, ratio_key, "final.png").replace("\\", "/")
                ratios[ratio_key] = f"/output/{rel}"
            else:
                ratios[ratio_key] = None
        previews.append({"name": product.name, "ratios": ratios})
    return previews


def _clear_folder(folder: str):
    if os.path.isdir(folder):
        for item in os.listdir(folder):
            p = os.path.join(folder, item)
            if os.path.isfile(p):
                os.remove(p)
            elif os.path.isdir(p):
                shutil.rmtree(p)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
