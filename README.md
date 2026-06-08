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
