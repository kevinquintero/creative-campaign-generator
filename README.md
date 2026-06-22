# Creative Campaign Generator

An app that takes a campaign brief — two products, a message, a target region — and automatically generates polished social media ads in three sizes: square (1:1), vertical story (9:16), and horizontal banner (16:9). It uses AI to create the product photography, then layers in your campaign text, brand colors, and a call-to-action button on top.

No design software. No Photoshop. Just fill in a form and click a button.

---

## Before You Start — What You Need

You need **Python** installed on your computer. That's the only prerequisite.

**Check if Python is already installed:**

Open a terminal (search "Command Prompt" in the Windows Start menu) and type:

```
python --version
```

If you see something like `Python 3.11.2` you're good. If you get an error, download Python here:

**[https://www.python.org/downloads/](https://www.python.org/downloads/)**

Click the big yellow "Download Python" button. Run the installer. On the first screen, **check the box that says "Add Python to PATH"** before clicking Install. That checkbox is easy to miss and important.

---

## How to Run the App

### Step 1 — Download the project

Click the green **Code** button on this GitHub page, then **Download ZIP**. Unzip it somewhere on your computer — your Desktop is fine.

Or if you have Git:
```
git clone https://github.com/kevinquintero/creative-campaign-generator.git
```

### Step 2 — Open a terminal in the project folder

In Windows Explorer, navigate into the folder you just unzipped. You should see files like `app.py`, `run_app.bat`, and `sample_campaign.json`.

Right-click anywhere in that folder and choose **"Open in Terminal"** (or "Open PowerShell window here").

### Step 3 — Install the required libraries (one time only)

In that terminal, paste this and press Enter:

```
pip install -r requirements.txt
```

This downloads all the Python packages the app needs. It takes about 30 seconds. You only ever need to do this once.

### Step 4 — Run the app

**Option A — Double-click (easiest):**

Double-click `run_app.bat` in the project folder. A terminal window opens, and your browser opens automatically to the app. Keep that terminal window open while you use the app. Close it to stop.

**Option B — From the terminal:**

```
python app.py
```

Then open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

---

## Using the App

Once the browser is open:

1. Click **"Load sample JSON"** — this fills in a ready-made campaign brief with two products
2. Click **"Generate Campaign Creatives"**
3. Wait about 5–15 seconds
4. Your six ads appear on screen (two products × three sizes)
5. Click **"Download ZIP"** to save all the images at once

That's it. The sample brief is already set up and works with zero configuration.

---

## AI Image Generation (Optional)

By default the app generates placeholder product images using code — no internet connection, no API key, completely free. These placeholders are good enough to show the pipeline working.

If you want **real AI-generated product photos**, you need a free Google Gemini API key:

1. Go to [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Sign in with a Google account and click **"Create API key"**
3. Copy the key

Then in the project folder:

- Find the file called `.env.example`
- Make a copy of it and rename the copy to `.env` (just `.env`, no "example")
- Open `.env` in Notepad
- Change these two lines:

```
IMAGE_PROVIDER=gemini
GEMINI_API_KEY=paste-your-key-here
```

Save the file and restart the app. Now when you generate, it calls Gemini to create real product photography.

**If you skip this step, the app still works fine** — it just uses illustrated placeholders instead of AI photos.

> **Note:** `.env` is never uploaded to GitHub. Your API key stays on your machine only.

---

## What the Output Looks Like

After generating, your files are saved here:

```
output/
├── Spark_Energy_Drink/
│   ├── 1x1/final.png       Square — 1080 × 1080 px  (Instagram feed)
│   ├── 9x16/final.png      Vertical — 1080 × 1920 px  (Stories, Reels)
│   └── 16x9/final.png      Horizontal — 1920 × 1080 px  (YouTube, banners)
├── Pure_Protein_Bar/
│   ├── 1x1/final.png
│   ├── 9x16/final.png
│   └── 16x9/final.png
└── run_report.json         Log of what ran, what was generated, any warnings
```

Each image has:
- The product photo filling the entire frame
- Campaign message in large bold text
- Product name beneath it
- Region badge in the corner
- A call-to-action button in the brand color

---

## Sample Campaign Brief

The file `sample_campaign.json` is already in the repo. Click "Load sample JSON" in the app and it fills in automatically. Here's what it looks like:

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

You can paste in your own brief or upload a `.json` file. The only hard requirements are: at least two products, a campaign message, and a region.

---

## Uploading Your Own Product Images

If you have product photos you want to use instead of AI-generated ones:

1. Name the file the same as the product, with underscores instead of spaces — e.g. `spark_energy_drink.png`
2. Use the **"Upload product images"** section on the form before clicking Generate
3. The app will use your image instead of generating one

The UI will show an "Asset reused" badge next to that product in the results.

---

## How It Works (for the technical reviewers)

```
Campaign Brief (JSON)  +  Product Images (optional)
          │
          ▼
┌─────────────────────────────────────────────────┐
│ app.py — Flask routes, pipeline orchestration   │
└─────────────────────────────────────────────────┘
          │
          ├─▶ brief_parser.py       Validate JSON → CampaignBrief dataclass
          ├─▶ asset_manager.py      Match uploaded files to products by name
          ├─▶ image_generator.py    ImageGenerator → provider (Mock / Gemini / OpenAI)
          ├─▶ creative_builder.py   Orchestrate composition per product × ratio
          ├─▶ design_system.py      Palette, Spacing, TypeScale, draw primitives
          ├─▶ creative_templates.py 4 templates × 3 ratios = 12 layout variants
          ├─▶ compliance.py         Prohibited word checks + output validation
          └─▶ reporting.py          run_report.json writer
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

Rather than hard-coding pixel offsets, every template receives a `Palette`, `Spacing`, and `TypeScale` derived from the canvas dimensions. Layout proportions hold correctly across 1080×1080, 1080×1920, and 1920×1080 without separate implementations per ratio.

Four named templates (`Minimal`, `Bold`, `Premium`, `Editorial`) are selected deterministically by MD5-hashing `(product_name + brand_primary)`. Same campaign always produces the same template assignments.

### Full-bleed composition

Every creative uses the product image as a full-bleed hero: `cover_crop()` fills the canvas (CSS `object-fit: cover` equivalent), a `vignette()` adds depth, and `gradient_overlay()` fades toward the brand color so text remains legible regardless of image content.

### Stateless pipeline

Each `/generate` request clears previous outputs, runs the full pipeline, and returns results in a single response. No database, no sessions, no background jobs. This keeps the architecture simple and the demo reproducible.

### Crash safety

The app catches all brief validation errors and provider failures, showing user-facing messages rather than crashing. The Flask reloader is disabled (`use_reloader=False`) to prevent Werkzeug's watchdog from killing in-flight requests on Python 3.12+.

### AI generates photography only — layout is programmatic

AI providers (Gemini, OpenAI) generate product photography. All text, buttons, gradients, badges, and brand lockups are drawn in Python from the campaign brief data. This guarantees that the campaign message, product name, and region in the output exactly match what was specified — a compliance requirement for advertising automation.

---

## Assumptions and Limitations

- **English only.** Campaign message text is English. Localization is not implemented.
- **One run per session.** Outputs are cleared on each generate request — appropriate for a demo, not a multi-user production system.
- **No logo compositing.** `logo_required: false` is parsed and respected; actual logo placement is not implemented.
- **Mock images are illustrations, not photos.** They demonstrate the pipeline but are not photorealistic. Use Gemini or OpenAI for realistic hero images.
- **Single-process Flask.** Suitable for local demo. For concurrent use, add gunicorn with multiple workers.

---

## Running Tests

```
python -m pytest tests/ -v
```

**23 tests, all passing.** Covers brief parsing, asset matching, compliance checks, mock generation, provider fallback, template selection, the full end-to-end pipeline, and output verification.

---

## Demo Video Script (~2.5 minutes)

1. Show the project folder: `run_app.bat`, `sample_campaign.json`
2. Double-click `run_app.bat` — browser opens automatically
3. Click **Load sample JSON** — show the brief: two products, campaign message, brand color
4. Click **Generate Campaign Creatives** — wait for results
5. Walk the results page: stats strip, creative grid per product, point out message/badge/CTA
6. Expand **Run Report** — show provider used, compliance status
7. Click **Download ZIP** — show folder structure

---

## Future Improvements

- **Localization** — translate campaign message based on `region` using a translation API
- **Logo compositing** — place brand logo in a consistent corner when `logo_required: true`
- **A/B variant generation** — multiple layout variants per product for split testing
- **Adobe Firefly integration** — brand-safe image generation with style consistency
- **Approval workflow** — lightweight approve/reject flags on the results page
- **Persistent storage** — save past runs to local SQLite or cloud bucket for comparison

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
