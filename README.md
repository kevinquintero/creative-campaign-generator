# Creative Automation Pipeline

A local proof-of-concept that automates creative asset generation for social ad campaigns. Given a campaign brief and optional product images, the pipeline generates polished social media creatives in three aspect ratios for every product in the brief.

Built as a take-home exercise demonstrating GenAI integration, provider abstraction, composited image output, and clean local tooling — no cloud deployment required.

---

## Problem Being Solved

Marketing teams launching localized campaigns must manually produce multiple ad variants per product, per region, per format. This is slow, error-prone, and doesn't scale. This pipeline automates that:

- Accept a structured campaign brief (JSON)
- Reuse existing product assets when available
- Generate missing product hero images via GenAI (or a realistic mock)
- Compose final creatives — complete with campaign message, brand colors, and region badge — for every standard social format
- Output organized files ready for download and review

---

## Quick Start (Windows)

### Option A — Double-click launcher (recommended)

```
Double-click run_app.bat
```

The launcher checks for Python, starts Flask, waits 3 seconds, then opens `http://127.0.0.1:5000` in your default browser. Keep the terminal window open; close it to stop the server.

### Option B — Terminal

```bat
cd "path\to\creative-automation-pipeline"
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then open [http://127.0.0.1:5000](http://127.0.0.1:5000).

---

## Setup

### Requirements

- Python 3.10 or higher
- pip
- No cloud account or paid API key required to run the demo

### Install dependencies

```bat
pip install -r requirements.txt
```

### Environment variables (optional)

```bat
copy .env.example .env
```

Edit `.env` if you want to use a real GenAI provider. Without it, the app runs in mock mode automatically.

---

## API Keys

The app has three operating modes, selected by the `IMAGE_PROVIDER` variable in `.env`:

| Mode | `IMAGE_PROVIDER` | Key needed |
|---|---|---|
| Mock (default) | `mock` or unset | None — runs fully offline |
| Google Gemini | `gemini` | `GEMINI_API_KEY` |
| OpenAI DALL-E 3 | `openai` | `OPENAI_API_KEY` |

### Where to set keys

In `.env` (copy from `.env.example`):

```env
IMAGE_PROVIDER=gemini
GEMINI_API_KEY=your-key-here
```

Get a Gemini key at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) — free tier available.

### Mock fallback

If no key is set (or the configured provider fails), the pipeline automatically falls back to `MockImageProvider`. Mock images are styled Pillow-rendered product illustrations — a can shape for beverages, a bar shape for snacks, etc. — with brand colors and studio-style shading. They are clearly labelled as mock in the UI and run report.

**The app never crashes due to a missing API key.** All provider errors are caught and logged.

---

## Using the App

1. Open [http://127.0.0.1:5000](http://127.0.0.1:5000)
2. Click **Load sample JSON** to pre-fill the brief, or paste/upload your own
3. Optionally upload product images (PNG/JPG) — they will be matched to products by filename
4. Click **Generate Campaign Creatives**
5. View the creative grid: three aspect ratios per product, campaign message overlaid
6. Expand **Run Report** to see asset provenance and compliance flags
7. Click **Download ZIP** to get all outputs in one archive

---

## Sample Campaign Brief

`sample_campaign.json` is included in the repo:

```json
{
  "campaign_name": "Summer Launch",
  "region": "United States",
  "target_audience": "Young adults interested in fitness and convenience",
  "campaign_message": "Fuel your day anywhere",
  "products": [
    {
      "name": "Spark Energy Drink",
      "description": "A citrus energy drink for busy active consumers"
    },
    {
      "name": "Pure Protein Bar",
      "description": "A high protein snack bar for post workout recovery"
    }
  ],
  "brand": {
    "name": "Acme Consumer Goods",
    "primary_color": "#1E3A5F",
    "secondary_color": "#FFFFFF",
    "logo_required": false
  }
}
```

### Required fields

| Field | Type | Description |
|---|---|---|
| `campaign_name` | string | Display name for the campaign |
| `region` | string | Target market/region (shown as badge on creatives) |
| `target_audience` | string | Audience description (passed to GenAI prompt) |
| `campaign_message` | string | Primary ad copy, overlaid on every creative |
| `products` | array | At least two items; each needs `name`, optionally `description` |
| `brand.primary_color` | hex string | Drives palette, gradients, CTA color |
| `brand.secondary_color` | hex string | Text and badge accent |

---

## Output Structure

```
output/
├── Spark_Energy_Drink/
│   ├── 1x1/final.png       1080 × 1080 px
│   ├── 9x16/final.png      1080 × 1920 px
│   └── 16x9/final.png      1920 × 1080 px
├── Pure_Protein_Bar/
│   ├── 1x1/final.png
│   ├── 9x16/final.png
│   └── 16x9/final.png
└── run_report.json
```

Each creative contains:
- Product hero image (full-bleed, cover-cropped, with gradient scrim)
- Campaign message in large bold type
- Product name below the headline
- Region badge in the top-right corner
- Brand-colored CTA button

---

## Architecture

```
Campaign Brief (JSON)  +  Product Images (optional)
          │
          ▼
┌─────────────────────────────────────────────────┐
│ app.py — Flask routes, pipeline orchestration   │
└─────────────────────────────────────────────────┘
          │
          ├─▶ brief_parser.py      Validate JSON → CampaignBrief dataclass
          ├─▶ asset_manager.py     Match uploaded files to products by name
          ├─▶ image_generator.py   ImageGenerator → provider (Mock / Gemini / OpenAI)
          ├─▶ creative_builder.py  Orchestrate composition per product × ratio
          ├─▶ design_system.py     Palette, Spacing, TypeScale, draw primitives
          ├─▶ creative_templates.py  4 templates × 3 ratios = 12 layout variants
          ├─▶ compliance.py        Prohibited word checks + output validation
          └─▶ reporting.py         run_report.json writer
```

### Module responsibilities

| File | Responsibility |
|---|---|
| `app.py` | Flask routes; orchestrates the full pipeline per request |
| `src/brief_parser.py` | Parses and validates JSON → typed `CampaignBrief` |
| `src/asset_manager.py` | Normalized name matching: `Spark Energy Drink` → `spark_energy_drink` |
| `src/image_generator.py` | `BaseImageProvider` ABC; Mock, OpenAI, and Gemini subclasses |
| `src/design_system.py` | `Palette` / `Spacing` / `TypeScale` derived from canvas size; drawing primitives |
| `src/creative_templates.py` | 4 templates (`Minimal`, `Bold`, `Premium`, `Editorial`) × 3 ratios |
| `src/creative_builder.py` | Hashes product+brand to select a template deterministically |
| `src/compliance.py` | Flags prohibited words in campaign messages; validates output files exist |
| `src/reporting.py` | Writes `run_report.json` with timing, provenance, and warnings |
| `src/config.py` | Canvas sizes, prohibited words list, folder paths |

---

## Key Design Decisions

### Provider abstraction

`BaseImageProvider` is an abstract class with a single `generate()` method returning a `PIL.Image`. `MockImageProvider`, `OpenAIImageProvider`, and `GeminiImageProvider` all implement it. `ImageGenerator.from_env()` reads `IMAGE_PROVIDER` and constructs the right provider, with automatic fallback to mock on any error.

Adding a new provider (e.g. Adobe Firefly) means subclassing `BaseImageProvider` and registering it in `from_env()` — no other changes required.

### Template and design system

Rather than hard-coding pixel offsets, every template receives a `Palette`, `Spacing`, and `TypeScale` derived from the canvas dimensions. This means layout proportions hold correctly across 1080×1080, 1080×1920, and 1920×1080 without separate implementations per ratio.

Four named templates (`Minimal`, `Bold`, `Premium`, `Editorial`) are selected deterministically by MD5-hashing `(product_name + brand_primary)`. Same campaign always produces the same template assignments.

### Full-bleed composition

Every creative uses the product image as a full-bleed hero: `cover_crop()` fills the canvas (CSS `object-fit: cover` equivalent), a `vignette()` adds depth, and `gradient_overlay()` fades toward the brand color so text remains legible regardless of image content.

### Stateless pipeline

Each `/generate` request clears previous outputs, runs the full pipeline, and returns results in a single response. No database, no sessions, no background jobs. This keeps the architecture simple and the demo reproducible.

### Crash safety

The app catches all brief validation errors (`BriefValidationError`) and provider failures, showing user-facing messages rather than crashing. The Flask reloader is disabled (`use_reloader=False`) to prevent Werkzeug's watchdog from killing in-flight requests on Python 3.12+.

---

## Assumptions and Limitations

- **English only.** Campaign message text is English. Localization is not implemented.
- **One run per session.** Outputs are cleared on each generate request — appropriate for a demo, not a multi-user production system.
- **No logo compositing.** `logo_required: false` is parsed and respected; actual logo placement is not implemented.
- **No persistent storage.** Generated files live in `output/` and are cleared on the next run.
- **Mock images are illustrations, not photos.** They demonstrate the pipeline but are not photorealistic. Use Gemini or OpenAI for realistic hero images.
- **Single-process Flask.** Suitable for local demo. For concurrent use, add gunicorn with multiple workers.

---

## Running Tests

```bat
python -m pytest tests/ -v
```

**23 tests, all passing.** Coverage includes:

- Brief parsing and field validation
- Asset matching (normalized filenames, case/extension variations)
- Compliance checks (prohibited words, output validation)
- Mock image generation (correct dimensions, RGB mode)
- Provider fallback chain
- Template selection (deterministic, covers all 4 templates)
- Design system (palette, spacing, type scale)
- Full end-to-end pipeline (builds all 6 output files)
- Output verification (correct paths, file size > 0)
- ZIP download route

---

## Demo Video Notes

**Suggested script (~2.5 minutes):**

1. Show the project root: `run_app.bat`, `sample_campaign.json`, `src/` folder
2. Double-click `run_app.bat` — browser opens automatically
3. Click **Load sample JSON** — show the brief: two products, region, message, brand color
4. Click **Generate Campaign Creatives** — wait ~5s (mock) or ~15s (Gemini)
5. Walk the results page:
   - Stats strip: 2 products, 6 creatives generated
   - Spark Energy Drink grid: 1:1 square, 9:16 story, 16:9 landscape
   - Pure Protein Bar grid: same layout, visually distinct template
   - Point out: campaign message overlaid, region badge, CTA button
6. Expand **Run Report** — show timestamp, provider used, compliance warnings
7. Click **Download ZIP** — show `output/` folder structure in the archive
8. *(Optional)* Upload a product image named `spark_energy_drink.png`, re-run — show "Asset reused" badge

---

## Future Improvements

- **Localization** — translate campaign message based on `region` field using a translation API
- **Logo compositing** — place brand logo in a consistent corner slot when `logo_required: true`
- **A/B variant generation** — produce multiple layout variants per product for split testing
- **Adobe Firefly integration** — brand-safe image generation with logo/style consistency
- **Approval workflow** — lightweight status flags on the results page (Approve / Request changes)
- **Persistent storage** — save past runs to local SQLite or cloud bucket for comparison
- **Performance** — async generation with progress streaming for large campaigns

---

## Assignment Checklist

| Requirement | Status | Notes |
|---|---|---|
| Campaign brief input (JSON) | Done | `brief_parser.py` validates all fields |
| Two or more products | Done | Validated — error if fewer than 2 |
| Target region/market | Done | Shown as badge on every creative |
| Target audience | Done | Passed to GenAI prompt for image context |
| Campaign message visible on posts | Done | Overlaid in every template, all 3 ratios |
| Input asset reuse | Done | Normalized name match; "Asset reused" badge in UI |
| GenAI asset generation when missing | Done | Gemini / OpenAI / Mock — automatic fallback chain |
| Three aspect ratios (1:1, 9:16, 16:9) | Done | 1080×1080 / 1080×1920 / 1920×1080 |
| Output organized by product and ratio | Done | `output/Product_Name/ratio/final.png` |
| Run locally | Done | `run_app.bat` double-click or `python app.py` |
| README with run / input / output / decisions | Done | This file |
| Brand compliance checks | Done (bonus) | Brand color palette enforced in design system |
| Legal content checks | Done (bonus) | Prohibited word list in `compliance.py` |
| Logging and reporting | Done (bonus) | Structured logging + `run_report.json` per run |
