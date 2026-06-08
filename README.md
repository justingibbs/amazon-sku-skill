# Ally Audio — Competitor Content Intelligence Skill

A Claude Code skill that audits an Ally Audio Amazon listing against live competitor SKUs and generates ready-to-use, guideline-compliant content edits.

Built as a take-home for CommerceIQ's Ally interview assignment.

## What it does

Given an Ally SKU, the skill:

1. Loads the SKU from the Ally catalog
2. Asks the user what they're optimizing for (search ranking, conversion, compliance, or all)
3. Searches Amazon for 3 similar competitor listings (live via SerpApi, or mock fallback)
4. Compares title, bullets, and description across all four products
5. Recommends the top 3 highest-impact edits, each cited to a specific competitor and a specific Amazon content rule
6. Waits for user approval (with a revision loop)
7. Produces a paste-ready Markdown summary the user can copy directly into Seller Central

## Setup

Requirements: Python 3.10+, [Claude Code](https://claude.com/claude-code) installed.

```bash
git clone https://github.com/justingibbs/amazon-sku-skill.git
cd amazon-sku-skill
pip install -r requirements.txt

# Optional: live Amazon data via SerpApi (100 free searches/month)
cp .env.example .env
# then edit .env and add your SERPAPI_API_KEY
```

To invoke: start Claude Code in this directory and ask it to audit one of the SKUs (e.g., *"Audit Ally SKU `ALY-AURA-PRO-001` against competitors"*). The skill auto-loads from `.claude/skills/`.

## Architecture

```
amazon-sku-skill/
├── .claude/skills/competitor-content-intelligence/
│   ├── SKILL.md                       # Instructions for Claude (the prompt)
│   ├── scripts/
│   │   ├── get_sku.py                 # Load SKU from Ally CSV
│   │   ├── find_competitors.py        # Search Amazon (SerpApi → mock fallback)
│   │   └── fetch_listing.py           # Pull title/bullets/description by ASIN
│   └── data/
│       └── mock_competitors.json      # Fallback when no SerpApi key
├── data/
│   ├── ally_skus.csv                  # Ally's catalog (the "client data")
│   └── amazon_content_guidelines.md   # Compiled Amazon rules with cite-able URLs
├── output/                            # Generated recommendation summaries (gitignored)
├── requirements.txt
├── .env.example
└── README.md
```

**Division of labor:**
- **Claude** (via `SKILL.md`) handles all reasoning: clarifying questions, comparison analysis, recommendation generation, approval flow, markdown summarization.
- **Python scripts** handle deterministic work: CSV parsing, HTTP calls, JSON serialization.
- **Reference data** (`data/amazon_content_guidelines.md`) is loaded by Claude on demand so it can cite specific rule URLs in every recommendation.

## Data Provenance

The two reference files in `data/` were generated differently — be aware of what's fabricated vs sourced.

### `data/ally_skus.csv` — fully fabricated

Ally Audio is a fictional brand invented for this take-home; the assignment didn't provide a sample SKU catalog, so one was synthesized in an iterative Claude Code session with the product decisions made by me:

- **Brand positioning:** mid-market lifestyle headphones — the gap between budget JLab and premium Bose
- **Catalog size:** 6 SKUs across the sub-categories a real multi-product audio brand would realistically own — over-ear ANC, true wireless earbuds, on-ear commuter, sport buds, wired studio monitors, kids' headphones
- **Content quality spread:** deliberately uneven (2 strong, 2 middling, 2 weak) so the skill has both subtle and obvious improvement targets to recommend against. The weak SKUs (`ALY-DASH-SPORT-004`, `ALY-STUDIO-50-005`) are the most useful for showing recommendation depth in a Loom demo
- **Image URLs:** `picsum.photos/seed/<slug>/800/800` placeholders that actually resolve and are deterministic per SKU
- **Multi-value fields** (`bullets`, `image_urls`) use `|` as the in-cell delimiter so the CSV stays single-line per row

No real Amazon catalog data was scraped, transferred, or referenced. The brand and SKU names are invented.

### `data/amazon_content_guidelines.md` — compiled from real Amazon sources

The guidelines doc is built from Amazon's own publicly accessible documentation. A Claude Code research agent ran web searches and fetches to extract concrete, citable rules, then compiled them into a single markdown file with source URLs inline so the skill can cite them on every recommendation. Scope is intentionally focused on what the skill actually uses (titles, bullets, descriptions, prohibited content, image basics) — not exhaustive.

**Primary sources** (Amazon-published, publicly accessible — most rules come from these):

- [Amazon Listings — Product Detail Page Guide (PDF)](https://m.media-amazon.com/images/G/35/sp-marketing-toolkit/Sellerfacingguides/Amazon_Listings_Product_Detail_Page_Guide.pdf)
- [Category Style Guide: Consumer Electronics and Camera & Photo (PDF, Feb 2018)](https://images-na.ssl-images-amazon.com/images/G/01/rainier/help/CEStyleGuide.pdf)
- [Amazon Seller Forums — New product title requirements effective Jan 21, 2025](https://sellercentral.amazon.com/seller-forums/discussions/t/b2b15728-0d43-453e-974f-59eb63f73059)
- [Prohibited Seller Activities and Actions Policy (PDF)](https://m.media-amazon.com/images/G/31/rainer/ProhibitedSellerActivitiesandActionsPolicy.pdf)

**Reference sources** (cited by ID; full text behind Seller Central login or JS-rendered, so text was mirrored from the PDFs above):

- [Product title requirements and guidelines (GYTR6SYGFA5E3EQC)](https://sellercentral.amazon.com/help/hub/reference/external/GYTR6SYGFA5E3EQC?locale=en-US)
- [Product bullet point requirements (GX5L8BF8GLMML6CX)](https://sellercentral.amazon.com/help/hub/reference/external/GX5L8BF8GLMML6CX?locale=en-US)
- [Product detail page rules (G200390640)](https://sellercentral.amazon.com/help/hub/reference/external/G200390640?locale=en-US)
- [Product image guide (G1881)](https://sellercentral.amazon.com/help/hub/reference/external/G1881?locale=en-US)
- [Technical image file requirements (G9FUUH87RBNXGKB7)](https://sellercentral.amazon.com/help/hub/reference/external/G9FUUH87RBNXGKB7?locale=en-US)

**Known conflicts:** the 2018 CE Style Guide and the 2025 Seller Central update disagree on title character limits (150 vs 200). Both are documented inline in `data/amazon_content_guidelines.md` with a note to prefer the newer rule. Third-party blogs and SEO summaries (Helium 10, Jungle Scout) were intentionally avoided as sources so every cited rule traces back to an Amazon-published URL.

## Design Decisions

Key choices made during scaffolding, each with the one-line "why":

1. **Claude Code skill at project level** (`.claude/skills/`) — ships with the repo so a reviewer can `git clone` and run it; user-level (`~/.claude/skills/`) would have been more portable but awkward as a take-home deliverable.
2. **Python for deterministic work, Claude for reasoning** — scripts handle CSV parsing and HTTP; Claude handles intent capture, comparison, recommendation generation, summarization. Plays to each tool's strengths and keeps the prompt (SKILL.md) focused on judgement rather than plumbing.
3. **SerpApi for live data with mock fallback** — real Amazon results when `SERPAPI_API_KEY` is set, bundled mock JSON when not. Live data sells the demo; mocks make it reproducible (and work offline on the reviewer's machine without requiring them to sign up for an API key).
4. **Fixed intent menu, not free-text** — the skill asks "search ranking / conversion / compliance / all" before recommending. Each intent biases the output differently. Free-text was considered but felt less predictable for a 3–6 minute Loom demo.
5. **Read-only CSV; recommendations emitted to `output/`** — the skill never mutates `data/ally_skus.csv`. Cleaner separation, and treats Ally's catalog as a snapshot of Seller Central rather than a working file the skill owns. A write-through mode could be added later.
6. **Inline rule citations with URLs on every recommendation** — the skill loads `data/amazon_content_guidelines.md` on demand and cites specific rules with their source URLs. This prevents Claude from quoting Amazon rules from training memory, which could be stale or wrong.

## Product brief

**Who:** Ally Audio listing managers (or the Ally AI teammate acting on their behalf) who own product detail pages in Amazon Seller Central.

**Pain:** Writing competitive, compliant listings is part copywriting, part conversion optimization, part Amazon-rule expertise. Most teams don't have time to manually compare against the top 3 competitors before every relaunch — so listings drift away from the patterns the top sellers in the category use.

**Solution:** A skill that does the comparison and generates ready-to-use edits in under a minute, with every recommendation backed by both a competitor reference and an Amazon rule citation.

**Value:**
- **For search ranking:** edits surface high-intent keywords competitors are ranking on
- **For conversion:** edits adopt structural patterns proven to convert (benefit-first bullets, scannable specs, warranty/inclusions in the last bullet per Amazon's CE Style Guide)
- **For compliance:** every edit is checked against Amazon's published rules so listings don't get suppressed for banned terms, ALL CAPS, or prohibited promotional language

## Assumptions

1. **One set of content rules applies across all categories.** Per the assignment, the skill uses the same Amazon content guidelines regardless of headphone sub-type. Real-world deployment would layer category-specific rules.
2. **SerpApi is the production data source.** Direct Amazon scraping is unreliable and ToS-questionable; SerpApi is the cheapest reliable third-party. Mock data lets the skill demo work without an API key.
3. **The user is the authority on intent.** The skill always asks "what's the goal" before recommending. Without intent, recommendations default to a balanced "all of the above" mode.
4. **Approvals happen per-bundle, not per-edit.** The skill produces all 3 recommendations in one shot; the user approves or asks for revisions on the bundle. Per-edit approval would be a v2 feature.
5. **Recommendations target Seller Central content fields only.** Image-related rules are documented in `data/amazon_content_guidelines.md` but the skill doesn't generate new images.
6. **The Ally CSV is the source of truth for current listing content.** The skill does not re-fetch Ally's live Amazon page; it trusts the CSV.

## Edge cases (documented, not all solved)

- SerpApi returns fewer than 3 results — fall back to mock for the gap
- Competitor data is malformed or empty — surface to user, skip that competitor
- User-selected SKU is in a category with no mock data — error gracefully
- User asks for revisions indefinitely — no current cap; could add one
- Recommendation conflicts with an Amazon rule — should never happen by design, but a final validation pass before approval would catch it
- Two Amazon rules conflict (e.g., the 2018 vs 2025 title length update) — guidelines doc flags conflicts; skill should prefer the newer rule
- Mocked competitor data is presented without flag — guarded against in SKILL.md ("Never invent a competitor; if `find_competitors.py` returns mock data, say so explicitly")

## Prompts and example I/O

- **The prompt** that drives the skill is `.claude/skills/competitor-content-intelligence/SKILL.md`. The frontmatter `description` field is how Claude decides when to invoke the skill; the body is the full workflow.
- **Example I/O** will be added under `examples/` after the first end-to-end run.

## License

MIT (placeholder — adjust as appropriate).
