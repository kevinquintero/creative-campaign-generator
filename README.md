# Creative Automation Pipeline

A local proof-of-concept creative automation system for social ad campaigns. Given a campaign brief and optional product images, the pipeline generates final social media creatives in three aspect ratios for every product.

Built as a take-home assessment demonstrating clean architecture, provider abstraction, and a working local demo — no external APIs or paid services required.

---

## Overview

```
Campaign Brief (JSON)  +  Product Images (optional)
           │
           ▼
   ┌───────────────────────────────────────┐
   │  1. Validate brief                    │
   │  2. Match uploaded images to products │
   │  3. Generate mock images (if missing) │
   │  4. Compose final creatives (Pillow)  │
   │  5. Run compliance checks             │
   │  6. Write run_report.json             │
   └───────────────────────────────────────┘
           │
           ▼
   output/
     Product_Name/
       1x1/final.png    (1080×1080)
       9x16/final.png   (1080×1920)
       16x9/final.png   (1920×1080)
     run_report.json
```

---

## Setup

### Requirements

- Python 3.12+
- pip

### Install

```bash
git clone <repo-url>
cd creative-automation-pipeline

python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### Environment (optional)

```bash
cp .env.example .env
# Edit .env if desired — no values are required for local development
```

---

## Run Locally

```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

1. Paste or upload a campaign brief JSON
2. Optionally upload product images
3. Click **Generate Campaign Creatives**
4. View results, download individual PNGs or the full ZIP

---

## Run Tests

```bash
python -m pytest tests/ -v
```

All 16 tests cover: brief parsing, validation, compliance checks, image generation, asset matching, the full end-to-end pipeline, and output verification.

---

## Sample Input

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
| `campaign_name` | string | Name of the campaign |
| `region` | string | Target market/region |
| `target_audience` | string | Audience description |
| `campaign_message` | string | Primary ad copy (overlaid on creatives) |
| `products` | array | At least two items, each with a `name` |
| `brand` | object | Optional; `primary_color`, `secondary_color` (hex) |

---

## Expected Output

After running with `sample_campaign.json`:

```
output/
├── Spark_Energy_Drink/
│   ├── 1x1/final.png      (1080×1080 PNG, ~74 KB)
│   ├── 9x16/final.png     (1080×1920 PNG, ~40 KB)
│   └── 16x9/final.png     (1920×1080 PNG, ~80 KB)
├── Pure_Protein_Bar/
│   ├── 1x1/final.png
│   ├── 9x16/final.png
│   └── 16x9/final.png
└── run_report.json
```

Each creative contains:
- Product image (mock-generated or uploaded)
- Campaign message overlaid in the lower section
- Product name below the message
- Region badge in the top-right corner

---

## Project Structure

```
creative-automation-pipeline/
├── app.py                  # Flask app, routes, pipeline orchestration
├── requirements.txt
├── README.md
├── .env.example
├── sample_campaign.json
├── tests/
│   └── test_pipeline.py    # 16 integration + unit tests
├── templates/
│   ├── index.html          # Upload form
│   └── results.html        # Creative preview + report
├── static/
│   ├── css/style.css
│   ├── js/main.js
│   └── uploads/            # Temporary uploaded assets
├── output/                 # Generated creatives (cleared each run)
└── src/
    ├── config.py           # Constants, paths, aspect ratios
    ├── brief_parser.py     # JSON validation → CampaignBrief dataclass
    ├── asset_manager.py    # Matches uploads to products by normalized name
    ├── image_generator.py  # Provider interface + MockImageProvider
    ├── creative_builder.py # Pillow composition: canvas → product → overlay → text
    ├── compliance.py       # Prohibited word checks, output validation
    ├── reporting.py        # run_report.json writer
    └── utils.py            # Name normalization, file helpers
```

---

## Design Decisions

### Provider abstraction for image generation

`image_generator.py` defines `BaseImageProvider` (abstract) and `MockImageProvider` (default). The mock generates styled PNGs with Pillow — gradient backgrounds, geometric accents, product label — that are visually distinct per product and fully usable in demos.

To swap in a real provider (Adobe Firefly, Stability AI, DALL-E, etc.):
1. Subclass `BaseImageProvider`
2. Implement `generate(product_name, description, width, height, primary_color) → PIL.Image`
3. Pass it: `ImageGenerator(provider=FireflyProvider())`

No other code changes required.

### Asset matching

Product names are normalized (`Spark Energy Drink` → `spark_energy_drink`) and compared against uploaded filenames with the same normalization. This handles common variations (spaces vs underscores, mixed case, different extensions) without requiring exact filename matches.

### Stateless pipeline

Each `/generate` request clears previous uploads and outputs, runs the full pipeline, and returns results in a single response. No database, no sessions, no background jobs. This keeps the architecture explainable and the demo reproducible.

### Creative composition

`CreativeBuilder` composes creatives in four layers:
1. Solid background canvas (brand primary color)
2. Product image, fitted and centered in the top 65% of the canvas
3. Gradient overlay fading the bottom third to the primary color
4. Text layer: campaign message (large, bold), product name, region badge

The same composition logic handles all three aspect ratios — only the canvas dimensions change.

---

## Assumptions

- **One run per session.** Outputs are cleared on each generate request. This is appropriate for a demo pipeline, not a production system with concurrent users.
- **English campaign messages.** The brief and overlaid text are English-only. Localization is out of scope.
- **No logo support.** `logo_required: false` is respected; logo compositing is not implemented.
- **Fonts.** The compositor attempts to load system fonts (`arial.ttf`, `DejaVuSans.ttf`). If none are found, Pillow's built-in bitmap font is used as a fallback.
- **Mock image size.** Product images are generated at 800×800 before being fitted into each creative canvas.

---

## Limitations

- **Mock images are not photorealistic.** They are geometric placeholders sufficient for pipeline demos.
- **No real GenAI API is connected.** Adding one requires implementing `BaseImageProvider` (see above).
- **Single-process.** Flask runs in development mode with a single worker. For concurrent use, add gunicorn.
- **No persistent storage.** Outputs are local files; they are cleared on the next run.
- **No logo compositing.** The `logo_required` field is parsed but not acted on.

---

## How Mock Generation Works

`MockImageProvider.generate()` uses only Pillow (no external API):

1. Derives a base RGB color from `brand.primary_color`
2. Renders a multi-step gradient background
3. Draws decorative geometric elements (circle outline + accent dots) seeded by the product name — so each product looks visually distinct
4. Overlays the product name in a semi-transparent pill at ~72% of the image height

The result is a 800×800 RGB image that the creative builder then fits into each canvas.

---

## How to Connect a Real GenAI Provider

1. Create a new file, e.g. `src/providers/firefly_provider.py`:

```python
from src.image_generator import BaseImageProvider
from PIL import Image
import requests

class FireflyProvider(BaseImageProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def generate(self, product_name, description, width, height, primary_color) -> Image.Image:
        # Call Adobe Firefly (or any image API) here
        response = requests.post(
            "https://firefly-api.adobe.io/v2/images/generate",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"prompt": f"{product_name}: {description}", "size": f"{width}x{height}"},
        )
        response.raise_for_status()
        image_url = response.json()["outputs"][0]["image"]["url"]
        img_bytes = requests.get(image_url).content
        return Image.open(io.BytesIO(img_bytes)).convert("RGB")
```

2. In `app.py`, replace:
```python
image_gen = ImageGenerator()
```
with:
```python
from src.providers.firefly_provider import FireflyProvider
image_gen = ImageGenerator(provider=FireflyProvider(api_key=os.environ["FIREFLY_API_KEY"]))
```

No other code changes needed.

---

## Demo Recording Script

**Duration: ~2.5 minutes**

1. **Open the app** at `http://localhost:5000`. Show the upload form.

2. **Load sample brief.** Click "Load sample brief." Show the JSON in the textarea: two products, a campaign message, brand colors.

3. **Generate.** Click "Generate Campaign Creatives." Wait 2–3 seconds.

4. **Results page.** Walk through:
   - Stats strip: 2 products, 6 creatives, 2 mock-generated
   - Creative grid for Spark Energy Drink: 1:1, 9:16, 16:9 previews side by side
   - Creative grid for Pure Protein Bar: same layout, visually distinct from the first product
   - Point out: campaign message overlaid, product name, region badge

5. **Run report.** Expand "View raw JSON." Show the timestamp, products processed, assets generated.

6. **Download ZIP.** Click "Download ZIP." Show the folder structure in the archive.

7. **Upload an asset.** Go back, upload a product image named `spark_energy_drink.png`. Re-run. Show "Asset reused" badge on Spark Energy Drink and "Mock generated" on Pure Protein Bar.

8. **Compliance.** Briefly mention: edit the message to include "miracle" and show the warning banner on the results page.

---

## Assessment Checklist

| Requirement | Status |
|---|---|
| Accept campaign brief (JSON) | Done |
| At least two products in brief | Done — validated, error if fewer |
| Required fields validated | Done — clear error messages |
| Accept uploaded product assets | Done |
| Reuse uploaded images when matched | Done — normalized name matching |
| Generate missing assets (mock provider) | Done — Pillow-based, visually distinct |
| Provider interface for real API | Done — `BaseImageProvider` ABC |
| 1:1 creative (1080×1080) | Done |
| 9:16 creative (1080×1920) | Done |
| 16:9 creative (1920×1080) | Done |
| Campaign message overlaid on creatives | Done |
| Product name on creatives | Done |
| Correct output folder structure | Done — `output/Product_Name/ratio/final.png` |
| Flask web UI | Done |
| run_report.json | Done |
| Compliance: prohibited word check | Done |
| Compliance: output validation | Done |
| ZIP download | Done |
| Logging | Done — structured logging throughout |
| README with setup/run/design/demo | Done |
| Tests (≥ passing end-to-end + unit) | Done — 16 tests, all passing |
| No hardcoded paid API | Done — mock is default, interface is clean |
| No fake API calls | Done — mock is clearly labelled as mock |
| No database / auth / React | Done — plain Flask + HTML |
| Runs locally from README | Verified |
