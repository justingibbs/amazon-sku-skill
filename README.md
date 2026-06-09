# BPN — Competitor Content Intelligence Skill

A Claude Code skill that audits a BARE PERFORMANCE NUTRITION (BPN) Amazon listing against live competitor SKUs and generates ready-to-use, guideline-compliant content edits.

Built as a take-home for CommerceIQ's Ally interview assignment. The skill is generic — point its `--csv` flag at any subset of the CommerceIQ `asin_data_filled.csv` export and the workflow still applies.

## What it does

Given a BPN SKU (an Amazon ASIN), the skill:

1. Loads the SKU from `data/bpn_skus.csv` (a subset of CommerceIQ's `asin_data_filled.csv`, filtered to the 15 `retailer_brand_name = "BARE PERFORMANCE NUTRITION"` rows)
2. Asks the user what they're optimizing for (search ranking, conversion, compliance, or all)
3. Searches Amazon for 3 similar competitor listings (live via SerpApi, or mock fallback)
4. Compares title, bullets, description, rating, reviews, price, and Best Sellers Rank across all four products
5. Recommends the top 3 highest-impact edits, each cited to a specific competitor and a specific Amazon content rule (Pet Supplies styleguide page, or a Seller Central URL from the broader compilation)
6. Waits for user approval (with a revision loop)
7. Produces a paste-ready Markdown summary the user can copy directly into Seller Central

## Setup

Requirements:

- [uv](https://docs.astral.sh/uv/) (`brew install uv` on macOS, or see the [install docs](https://docs.astral.sh/uv/getting-started/installation/))
- [Claude Code](https://claude.com/claude-code)

```bash
git clone https://github.com/justingibbs/amazon-sku-skill.git
cd amazon-sku-skill

# Optional: live Amazon data via SerpApi (100 free searches/month)
cp .env.example .env
# then edit .env and add your SERPAPI_API_KEY

# One-time: extract the styleguide PDF into a citable MD file
uv run .claude/skills/competitor-content-intelligence/scripts/extract_styleguide.py
```

`uv run` handles Python + dependencies automatically (resolves from `pyproject.toml` and `uv.lock`, caches the venv in `.venv/`). No manual `pip install`.

To invoke: start Claude Code in this directory and ask it to audit one of the BPN SKUs (e.g., *"Audit BPN SKU `B0DGHN493N`"* or *"Improve `B0DGHN493N`"*). The skill auto-loads from `.claude/skills/` and runs the Python helpers via `uv run`.

## Architecture

For ASCII diagrams of the end-to-end workflow, the data-source fallback (SerpApi → cache → mock), and the file layout with per-script data flow, see [`ARCHITECTURE.md`](./ARCHITECTURE.md).

```
amazon-sku-skill/
├── .claude/skills/competitor-content-intelligence/
│   ├── SKILL.md                       # Instructions for Claude (the prompt)
│   ├── scripts/
│   │   ├── get_sku.py                 # Load SKU from BPN CSV
│   │   ├── find_competitors.py        # Search Amazon (SerpApi → mock fallback)
│   │   ├── fetch_listing.py           # Pull title/bullets/desc/rating/BSR by ASIN
│   │   └── extract_styleguide.py      # One-shot: PDF styleguide → Markdown
│   └── data/
│       └── mock_competitors.json      # Fallback (sports-nutrition ASINs from the CSV)
├── data/
│   ├── bpn_skus.csv                   # BPN catalog — the "client data" (15 rows)
│   ├── asin_data_filled.csv           # Upstream CIQ export (154 rows; read-only reference)
│   ├── PetSupplies_PetFood_Styleguide_EN_AE.pdf  # Source PDF from CIQ
│   ├── amazon_styleguide_extracted.md # PDF→MD output, primary citation source
│   └── amazon_content_guidelines.md   # Broader Amazon rules w/ source URLs (secondary)
├── output/                            # Generated recommendation summaries (gitignored)
├── pyproject.toml
├── .env.example
└── README.md
```

**Division of labor:**
- **Claude** (via `SKILL.md`) handles all reasoning: clarifying questions, comparison analysis, recommendation generation, approval flow, markdown summarization.
- **Python scripts** handle deterministic work: CSV parsing, PDF extraction, HTTP calls, JSON serialization.
- **Reference data** (the two guideline files) is loaded by Claude on demand so it can cite specific rules in every recommendation.

## Data Provenance

The reference files in `data/` come from different sources — be aware of what's provided vs derived.

### `data/asin_data_filled.csv` — provided by CommerceIQ

The CIQ-provided ASIN export. 154 rows across multiple brands and four "universes" (beverages, snacks & sweets, breakfast cereal, pantry staples). The columns include real Amazon ASINs, titles, JSON-array bullet points and image URLs, descriptions, retailer category breadcrumb, retailer brand name, and CommerceIQ's historical rank columns (`min_rank_search`, `avg_rank_search`, `min_rank_category`, `avg_rank_category`).

Read-only. The skill does not modify it.

### `data/bpn_skus.csv` — derived from `asin_data_filled.csv`

The 15 rows from `asin_data_filled.csv` where `retailer_brand_name = "BARE PERFORMANCE NUTRITION"`. Same schema as the upstream file. The skill loads from this file by default; pointing `--csv` at the upstream file (or any other subset) also works.

BPN was chosen as the client stand-in because it is the brand with the largest contiguous SKU footprint in the export (15 ASINs spanning three universes and one category node — Sports Nutrition → Electrolyte Replacements). This gives the skill enough breadth to demonstrate within-catalog variety while keeping all recommendations grounded in one product space.

### `data/PetSupplies_PetFood_Styleguide_EN_AE._CB1198675309_.pdf` — provided by CommerceIQ

Amazon's official Pet Supplies styleguide for the UAE marketplace (13 pages, December 2018). Per the take-home brief: *"Assume the same content guidelines apply to all categories (e.g., Pet supplies, Beverages, etc)."* The skill treats this as the universal source of truth and cites it as *Amazon Pet Supplies Styleguide, p. N*.

### `data/amazon_styleguide_extracted.md` — derived from the PDF

A one-shot script (`scripts/extract_styleguide.py`) uses `pypdf` to extract the PDF text page-by-page into Markdown so Claude can load it via Read and cite specific pages. Re-run the script if the source PDF changes.

### `data/amazon_content_guidelines.md` — compiled from real Amazon sources (secondary)

A broader Markdown compilation of Amazon's publicly accessible content rules with source URLs inline. Used as a secondary citation source when the Pet Supplies styleguide does not cover a specific rule, or when a clickable URL is more useful than a page reference.

**Primary sources** (Amazon-published, publicly accessible — most rules come from these):

- [Amazon Listings — Product Detail Page Guide (PDF)](https://m.media-amazon.com/images/G/35/sp-marketing-toolkit/Sellerfacingguides/Amazon_Listings_Product_Detail_Page_Guide.pdf)
- [Category Style Guide: Consumer Electronics and Camera & Photo (PDF, Feb 2018)](https://images-na.ssl-images-amazon.com/images/G/01/rainier/help/CEStyleGuide.pdf)
- [Amazon Seller Forums — New product title requirements effective Jan 21, 2025](https://sellercentral.amazon.com/seller-forums/discussions/t/b2b15728-0d43-453e-974f-59eb63f73059)
- [Prohibited Seller Activities and Actions Policy (PDF)](https://m.media-amazon.com/images/G/31/rainer/ProhibitedSellerActivitiesandActionsPolicy.pdf)

**Reference sources** (cited by ID; full text behind Seller Central login or JS-rendered, so text was mirrored from the PDFs above):

- [Product title requirements (GYTR6SYGFA5E3EQC)](https://sellercentral.amazon.com/help/hub/reference/external/GYTR6SYGFA5E3EQC?locale=en-US)
- [Product bullet point requirements (GX5L8BF8GLMML6CX)](https://sellercentral.amazon.com/help/hub/reference/external/GX5L8BF8GLMML6CX?locale=en-US)
- [Product detail page rules (G200390640)](https://sellercentral.amazon.com/help/hub/reference/external/G200390640?locale=en-US)
- [Product image guide (G1881)](https://sellercentral.amazon.com/help/hub/reference/external/G1881?locale=en-US)
- [Technical image file requirements (G9FUUH87RBNXGKB7)](https://sellercentral.amazon.com/help/hub/reference/external/G9FUUH87RBNXGKB7?locale=en-US)

**Known conflicts:** the 2018 CE Style Guide and the 2025 Seller Central update disagree on title character limits (150 vs 200). Both are documented inline in `data/amazon_content_guidelines.md` with a note to prefer the newer rule. Third-party blogs and SEO summaries (Helium 10, Jungle Scout) were intentionally avoided as sources so every cited rule traces back to an Amazon-published URL.

## Design Decisions

Key choices made during scaffolding, each with the one-line "why":

1. **Claude Code skill at project level** (`.claude/skills/`) — ships with the repo so a reviewer can `git clone` and run it.
2. **Python for deterministic work, Claude for reasoning** — scripts handle CSV/PDF parsing and HTTP; Claude handles intent capture, comparison, recommendation generation, summarization.
3. **SerpApi for live competitors with mock fallback** — real Amazon results when `SERPAPI_API_KEY` is set, bundled mock JSON (built from real ASINs in the CIQ export) when not. Live data sells the demo; mocks make it reproducible offline.
4. **Fixed intent menu, not free-text** — the skill asks "search ranking / conversion / compliance / all" before recommending. Each intent biases the output differently.
5. **Read-only CSV; recommendations emitted to `output/`** — the skill never mutates `data/bpn_skus.csv`.
6. **Inline rule citations on every recommendation** — Claude loads `data/amazon_styleguide_extracted.md` (primary) and `data/amazon_content_guidelines.md` (secondary) on demand and cites specific rules. Prevents Claude from quoting rules from training memory.
7. **CIQ historical rank ≠ SerpApi BSR snapshot** — the CSV's `min/avg_rank_*` columns are CommerceIQ's historical aggregates; SerpApi only returns a point-in-time `bestsellers_rank`. The skill is required to label both clearly and never silently conflate them.

## Product brief

**Who:** BPN listing managers (or the Ally AI teammate acting on their behalf) who own product detail pages in Amazon Seller Central.

**Pain:** Writing competitive, compliant listings is part copywriting, part conversion optimization, part Amazon-rule expertise. Most teams don't have time to manually compare against the top 3 competitors before every relaunch — so listings drift away from the patterns the top sellers in the category use.

**Solution:** A skill that does the comparison and generates ready-to-use edits in under a minute, with every recommendation backed by both a competitor reference and an Amazon rule citation.

**Value:**
- **For search ranking:** edits surface high-intent keywords competitors are ranking on
- **For conversion:** edits adopt structural patterns proven to convert (benefit-first bullets, scannable specs, certifications and warranty in the last bullet per Amazon's styleguide guidance)
- **For compliance:** every edit is checked against Amazon's published rules so listings don't get suppressed for banned terms, ALL CAPS, or prohibited promotional language

## Assumptions

1. **One set of content rules applies across all categories.** Per the assignment, the Pet Supplies styleguide is the universal source even though BPN sells sports nutrition. Real-world deployment would layer category-specific rules.
2. **SerpApi is the production data source.** Direct Amazon scraping is unreliable and ToS-questionable; SerpApi is the cheapest reliable third-party. Mock data lets the skill demo work without an API key.
3. **The user is the authority on intent.** The skill always asks "what's the goal" before recommending. Without intent, recommendations default to a balanced "all of the above" mode.
4. **Approvals happen per-bundle, not per-edit.** The skill produces all 3 recommendations in one shot; the user approves or asks for revisions on the bundle. Per-edit approval would be a v2 feature.
5. **Recommendations target Seller Central content fields only.** Image-related rules are documented in the guidelines but the skill doesn't generate new images.
6. **The BPN CSV is the source of truth for current listing content.** The skill does not re-fetch BPN's live Amazon page; it trusts the CSV.
7. **CIQ rank columns and SerpApi BSR are not interchangeable.** The skill labels which is which on every comparison; it never silently mixes them.

## Edge cases (documented, not all solved)

- SerpApi returns fewer than 3 results — fall back to mock for the gap
- Competitor data is malformed or empty — surface to user, skip that competitor
- User-selected SKU is in a category with no mock data — the mock loader picks the closest by query keywords; if that produces unrelated brands, the skill should flag and ask the user whether to proceed
- User asks for revisions indefinitely — no current cap; could add one
- Recommendation conflicts with an Amazon rule — should never happen by design, but a final validation pass before approval would catch it
- Two Amazon rules conflict (e.g., the 2018 vs 2025 title length update, or the Pet Supplies styleguide's 50-character title cap vs the 200-character Seller Central limit) — both source files document conflicts inline; skill should prefer the newer Seller Central rule and call out the discrepancy
- Mocked competitor data is presented without flag — guarded against in SKILL.md ("Never invent a competitor; if `find_competitors.py` returns mock data, say so explicitly")
- A competitor's `bestsellers_rank` is empty in SerpApi's response — render "BSR not surfaced" rather than blanking the cell
- BPN's selected SKU has blank rank columns — skip the rank context in Step 4 rather than emitting "null"

## Prompts and example I/O

- **The prompt** that drives the skill is `.claude/skills/competitor-content-intelligence/SKILL.md`. The frontmatter `description` field is how Claude decides when to invoke the skill; the body is the full workflow.
- **Example I/O** lives in [`example_runs/`](./example_runs/):
  - [`B0DGHN493N_recommendation_20260608.md`](./example_runs/B0DGHN493N_recommendation_20260608.md) — current BPN-era audit of the flagship Sugar Free Mango Hydration Drink Mix (50 servings). Search-ranking intent. Demonstrates ALL-CAPS bullet-prefix removal, keyword-gap-closing title rewrite, and a keyword-dense description rewrite against 3 live SerpApi competitors (Ultima, Nectar, TREVI — all A+ Content).
  - Two prior Ally Audio runs are preserved as legacy references — they predate the BPN reframe but demonstrate the same 7-step workflow and paste-ready output format.

## License

MIT (placeholder — adjust as appropriate).
