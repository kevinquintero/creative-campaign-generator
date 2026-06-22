# Project Status

Creative Automation Pipeline — Adobe Forward Deployed AI Engineer take-home.

Built with Python 3.12, Flask, Pillow, python-dotenv. No database, no auth, no cloud deployment.

---

## Architecture Decisions (Do Not Change)

These decisions are intentional. Each one was chosen to solve a specific problem and should not be reverted without understanding the full downstream impact.

### Multi-provider image generation (Gemini, OpenAI, Mock)

`src/image_generator.py` supports three interchangeable providers behind a shared `BaseImageProvider` ABC. The active provider is selected at startup via the `IMAGE_PROVIDER` environment variable.

**Why:** The project must demonstrate AI integration without requiring a specific API key from the evaluator. Mock mode makes the pipeline fully runnable without any credentials. OpenAI and Gemini show real provider breadth. All three providers produce identical outputs as far as the rest of the pipeline is concerned.

### Provider abstraction (`BaseImageProvider` ABC)

Every provider implements the same interface: `generate(product_name, description, width, height, primary_color, ...) -> PIL.Image`. `ImageGenerator` calls whichever provider is configured and the rest of the pipeline never touches provider logic directly.

**Why:** Changing providers or adding a new one (e.g., Stability AI, Adobe Firefly) requires zero changes to Flask routes, the creative builder, or tests. The pipeline is decoupled from the generation mechanism.

### Graceful fallback to Mock on provider failure

`ImageGenerator.generate_product_image()` catches all exceptions from the configured provider and re-runs generation through `MockImageProvider`, returning `"mock (fallback)"` as the provider name. The Flask route and report both record which provider was actually used.

**Why:** API failures (network errors, quota limits, model 404s) must not crash the pipeline mid-run. The fallback ensures the user always receives complete creative output even when the AI backend is unavailable.

### Design system as a standalone Python module (`src/design_system.py`)

All color math, spacing tokens, typography scale, font loading, drawing primitives, and gradient utilities live in one module. Template classes import from it. No layout value is hardcoded anywhere outside this file.

**Why:** With four templates × three aspect ratios = 12 different compositions, duplicating sizing logic would cause drift. A single source of truth means changing a spacing multiplier or font scale affects all templates uniformly.

### Creative template architecture (`src/creative_templates.py`)

Each template is a class (`PremiumTemplate`, `MinimalTemplate`, `BoldTemplate`, `EditorialTemplate`) that subclasses `BaseTemplate`. Each class implements `_square`, `_story`, and `_landscape` methods. The registry `_REGISTRY` maps name strings to classes. `auto_select_template()` picks deterministically from the registry using an MD5 hash of the product name + brand color.

**Why:** Separation of "which layout?" from "how to draw it?" means templates are independently testable, the registry makes adding a new template a one-class operation with no changes required elsewhere, and deterministic selection means the same brief always produces the same creative family (reproducible output for evaluation).

### Pillow used only for creative composition, not image generation

`MockImageProvider` draws product placeholder images with Pillow. All other providers (OpenAI, Gemini) return real photographs. `CreativeBuilder` and all template classes use Pillow to composite those images into final ad layouts with gradients, text, CTA buttons, and brand lockups.

**Why:** AI image generation and layout composition are fundamentally different concerns. Keeping them separate means the composition layer works identically regardless of whether the product image came from DALL-E, Gemini, or Pillow. Composition logic does not need to know anything about how the source image was produced.

### AI used only for product photography, not for compositing entire advertisements

AI providers generate one product photograph per product. All headline text, CTA buttons, brand lockups, gradients, and layout are drawn programmatically by `creative_templates.py` using campaign data from the brief.

**Why:** AI-generated text is unreliable (hallucinated copy, incorrect product names, inconsistent brand voice). Programmatic composition guarantees that the campaign message, product name, region, and brand colors in the output exactly match what was specified in the brief — a compliance and quality requirement for advertising automation.

### JSON-first pipeline

`src/brief_parser.py` parses a campaign JSON brief into typed dataclasses (`CampaignBrief`, `Product`, `Brand`). Every downstream component receives typed objects, not raw dicts or form fields. The Flask route is responsible only for calling `parse_brief()` and passing the result to pipeline components.

**Why:** Typed dataclasses enforce schema at parse time, produce readable `BriefValidationError` messages for bad input, and make the pipeline trivially testable without an HTTP context. Dataclasses also make future schema changes safe — adding a field is one edit in one file.

### Flask architecture with no database

`app.py` is a thin HTTP wrapper over the pipeline. It handles file I/O (saving uploads, reading outputs), calls the pipeline in order, renders templates, and serves files. There is no ORM, no session storage, no background task queue.

**Why:** The take-home scope is a local proof-of-concept. Adding a database would introduce setup friction for the evaluator and add components that provide no value for a single-user, single-run tool. Pipeline state is passed through function arguments and stored in the output folder.

### Modular project structure under `src/`

Each concern lives in its own module: `brief_parser`, `asset_manager`, `image_generator`, `creative_builder`, `creative_templates`, `design_system`, `compliance`, `reporting`, `config`, `utils`. Flask imports from these; they do not import from Flask.

**Why:** The pipeline modules are independently importable and testable without starting the Flask app. `tests/test_pipeline.py` imports directly from `src/` and runs the entire pipeline without HTTP. This is also the architecture pattern Adobe uses internally for automation tooling where the core logic must be reusable across different surfaces (CLI, API, scheduled jobs).

---

## Things That Were Tried But Rejected

These approaches were explored and deliberately abandoned. Do not re-introduce them.

### Gemini model `imagen-3.0-generate-002`

The first Gemini integration attempt used Imagen 3 via the `google-genai` SDK. Every call returned `404: models/imagen-3.0-generate-002 is not found`.

**Why rejected:** The model is not accessible on the standard Gemini API key tier. It requires a separate Vertex AI project with explicit Imagen access provisioned by Google. Using it would make the Gemini provider non-functional for most API keys.

### Gemini model `gemini-2.0-flash-preview-image-generation`

Second attempt. Same result: `404: models/gemini-2.0-flash-preview-image-generation is not found`. This preview model was either renamed or access-gated after its announcement.

**Why rejected:** Preview model names are not stable. The current implementation uses `gemini-2.5-flash-image` with a diagnostic fallback that lists all available image-capable models to the terminal if a 404 occurs, making future model name changes self-diagnosable.

### Generating entire advertisement layouts with AI (text, buttons, brand elements via DALL-E or Gemini)

Early concept: pass the full campaign brief to an image model and ask it to produce a finished ad including headline, CTA, product name, and brand colors.

**Why rejected:** AI image generators hallucinate copy (wrong product names, fabricated campaign messages, invented CTAs). They cannot reliably match exact brand hex colors. They produce inconsistent visual styles across products within the same campaign. There is no reliable way to enforce compliance rules (prohibited words, region accuracy) on AI-generated text inside an image. The current architecture solves all of these: AI generates photography only, Pillow composites everything else from the verified campaign data.

### Flat creative layout (image thumbnail over solid brand color background)

The original `creative_builder.py` placed a thumbnail of the product image in the top 67% of the canvas and drew campaign text below it on a flat brand-colored background. All three aspect ratios used the same layout.

**Why rejected:** Output looked like a technical demo, not an advertisement. There was no differentiation between ratios, no full-bleed imagery, no gradient depth, no CTA button, no brand lockup, and no visual hierarchy. Every creative looked identical regardless of product or brand.

### Single creative template for all products and ratios

The original creative builder had one code path for all compositions. A single `_compose()` method handled all three aspect ratios with conditional height math.

**Why rejected:** 1:1, 9:16, and 16:9 placements have fundamentally different viewing contexts and composition requirements (Instagram square, Story/Reel vertical, YouTube/banner horizontal). Forcing one layout into all three produced awkward cropping and unreadable text at different ratios. The template architecture replaced this with per-ratio layout methods inside each template class.

### Hardcoded typography sizes

Early creative builder used fixed pixel values: `font_size = max(52, w // 20)` with hardcoded scale ratios.

**Why rejected:** The same pixel value produces very different visual weight at 1080×1080 vs 1920×1080. Hardcoded values required per-ratio adjustments spread across multiple functions, making changes fragile. `design_system.py` replaces this with a `TypeScale` derived from `min(canvas_w, canvas_h)` so all fonts scale proportionally with the canvas.

### Hardcoded brand colors in layout logic

Early versions passed raw hex strings into composition functions and re-derived dark/light variants inline in multiple places.

**Why rejected:** Color derivation logic was duplicated across gradient generation, text color selection, and CTA button coloring, with slightly different math in each place. `design_system.py` centralizes this into `build_palette()`, which derives the full 10-color palette once and passes it to template methods.

### `textwrap.fill()` for text layout

The original text wrapping used Python's `textwrap.fill(text, width=cols)` where `cols` was estimated from `max_px_width / (font_size * 0.52)`.

**Why rejected:** Column estimation by character width is inaccurate — proportional fonts have variable character widths. Wide characters like `W` and `M` overflow their estimated columns; narrow characters like `i` and `l` waste space. `design_system.wrap_to_width()` replaces this with pixel-accurate measurement using `draw.textbbox()` on each candidate line before committing to a wrap point.

---

## Guardrails For Future Development

These are project constraints. They are not style suggestions. Future changes that violate these rules will break the architecture.

### Do not remove provider abstraction

All image generation must go through a class that subclasses `BaseImageProvider` and implements `generate() -> PIL.Image`. Do not call OpenAI or Gemini APIs directly from Flask routes or template methods.

### Do not replace Pillow composition with AI generation

The composition layer (templates, gradients, text, buttons, brand lockups) must remain Pillow-based and data-driven. AI providers supply product photography only. This is the compliance boundary: every word and color in the final creative must be traceable to the campaign brief.

### Do not tightly couple providers to Flask routes

`app.py` must not contain provider-specific logic. It calls `ImageGenerator.from_env()` and receives an image. Which provider ran, and whether fallback occurred, is recorded in `generation_providers` and passed to `write_report()`. Route code must remain provider-agnostic.

### Do not duplicate design constants

All spacing, typography, color derivation, font loading, and drawing utilities belong in `src/design_system.py`. Template classes import from it. Inline pixel values inside template methods are a bug, not a shortcut.

### Do not hardcode layout values

All dimensions in template methods must be expressed as fractions of `canvas_w` / `canvas_h`, or as multiples of `Spacing` / `TypeScale` values from the design system. The templates must render correctly at any canvas resolution, not just the current three.

### Keep template architecture modular

Adding a new creative template must require only: (1) create a class that subclasses `BaseTemplate`, (2) implement `_square`, `_story`, `_landscape`, (3) add it to `_REGISTRY` in `creative_templates.py`. No other file should need changes.

### Preserve deterministic template selection

`auto_select_template(product_name, brand_primary)` uses MD5 of the combined string to pick a template index. The same brief must always produce the same template family. Do not introduce random selection — reproducible output is a requirement for advertising automation QA.

### Keep all providers interchangeable

`MockImageProvider`, `OpenAIImageProvider`, and `GeminiImageProvider` must all accept the same arguments and return `PIL.Image`. `ImageGenerator.generate_product_image()` must remain the only call site. Do not add provider-specific parameters to the public interface.

### Keep tests passing at all times

`tests/test_pipeline.py` contains 23 tests covering the full pipeline from brief parsing through image generation, creative composition, compliance, and reporting. All 23 must pass before any change is merged. Tests run without any API keys (all generation uses mock). Do not add test dependencies on external services.

### Never remove mock mode

`MockImageProvider` must always work with zero environment variables and zero network access. It is the default provider, the CI provider, the fallback provider, and the evaluator-safety provider. Removing it breaks every path that does not have a live API key.

### Preserve graceful fallback behavior

`ImageGenerator.generate_product_image()` must catch all exceptions from the configured provider and fall back to `MockImageProvider`. The fallback must be transparent to the creative builder — it receives a `PIL.Image` either way. The provider name returned (`"mock (fallback)"`) is surfaced in the UI badge and run report so the fallback is visible but not blocking.

### Preserve clean separation between image generation and creative composition

`src/image_generator.py` knows nothing about aspect ratios, campaign messages, or layout. `src/creative_templates.py` knows nothing about how the product image was generated. The handoff is a `PIL.Image` object. This boundary must not be blurred.

### Do not add a database, authentication, or cloud deployment

The project is explicitly scoped as a local proof-of-concept. Pipeline state is passed through function arguments and persisted in the output folder. Adding a database, user sessions, or cloud infrastructure is out of scope and would misrepresent the project's design intent to evaluators.
