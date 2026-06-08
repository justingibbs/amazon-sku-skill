# Submission Map — Ally Competitor Content Intelligence Skill

A quick-reference map of where every assignment deliverable lives. For setup, design rationale, and the product brief, see [`README.md`](./README.md).

## TL;DR for the evaluator

1. **What to read first:** [`README.md`](./README.md) (overview, setup, design decisions, product brief, assumptions, edge cases)
2. **What to read next:** [`ARCHITECTURE.md`](./ARCHITECTURE.md) (workflow diagram, data-source fallback, file layout, verbatim user-facing prompts)
3. **What to skim for examples:** [`example_runs/`](./example_runs/) (two end-to-end audits with the skill's actual output)
4. **What to read to grade the agent:** [`.claude/skills/competitor-content-intelligence/SKILL.md`](./.claude/skills/competitor-content-intelligence/SKILL.md) (the full prompt that drives Claude)

## Assignment requirements → file map

| Assignment requirement | Where to find it |
|---|---|
| Skill that compares a SKU to competitors and recommends edits | [`.claude/skills/competitor-content-intelligence/SKILL.md`](./.claude/skills/competitor-content-intelligence/SKILL.md) — the agent prompt; defines the 7-step workflow |
| Comparison report (title length, bullets, description, attributes) | Produced in Step 4 of the skill; see Step 4 of either example run |
| Top 3 edits with competitor references and Amazon rule citations | Produced in Step 5; see the "Approved edits" section of either example run |
| Final Markdown summary on user approval | Produced in Step 7 and written to `output/<sku>_recommendation_<date>.md`; promoted examples in `example_runs/` |
| README — setup, assumptions, product brief | [`README.md`](./README.md) (Setup, Assumptions, Product brief sections) |
| Prompts | [`.claude/skills/competitor-content-intelligence/SKILL.md`](./.claude/skills/competitor-content-intelligence/SKILL.md) is the primary prompt. Verbatim user-facing prompts from each pause point are in [`ARCHITECTURE.md`](./ARCHITECTURE.md) §4. |
| Example I/O | [`example_runs/`](./example_runs/) — see its [`README.md`](./example_runs/README.md) for the table of runs |
| Architecture diagram | [`ARCHITECTURE.md`](./ARCHITECTURE.md) — ASCII diagrams of (1) end-to-end workflow, (2) SerpApi → cache → mock fallback, (3) file layout with per-script data flow |
| Edge cases | [`README.md`](./README.md#edge-cases-documented-not-all-solved) |
| Loom walkthrough | (Recorded separately — link delivered with the submission) |

## Example runs

Two end-to-end audits are committed under [`example_runs/`](./example_runs/):

| Run | SKU | Intent | What it demonstrates |
|---|---|---|---|
| [`ALY-DASH-SPORT-004_recommendation_20260608.md`](./example_runs/ALY-DASH-SPORT-004_recommendation_20260608.md) | True Wireless Earbuds | Improve search ranking | Stub title (23 chars) → 144-char attribute-stacked title; vague bullets → 5 keyword-rich bullets |
| [`ALY-STUDIO-50-005_recommendation_20260608.md`](./example_runs/ALY-STUDIO-50-005_recommendation_20260608.md) | Wired Studio Headphones | Increase conversion | 25-char title → 135-char spec-rich title; 3 ultra-terse bullets → 5 feature-with-benefit bullets ending in an accessories/warranty bullet |

Both runs used live SerpApi data. Live `output/` is `.gitignored`; promoted runs are hand-copied into `example_runs/`.

## Agent prompts

The skill's full prompt is [`.claude/skills/competitor-content-intelligence/SKILL.md`](./.claude/skills/competitor-content-intelligence/SKILL.md). It defines:

- **Frontmatter `description`** — trigger conditions (Claude Code uses this to decide when to load the skill)
- **7-step workflow** — identify SKU → clarify intent → fetch competitors → compare → recommend → approve → produce summary
- **Hard rules** — always cite Amazon URLs inline, never invent a competitor, never quote rules from memory, don't recommend rule-violating edits, don't skip intent or approval

The verbatim user-facing question text (the intent menu in Step 2 and the approval prompt in Step 6) is reproduced in [`ARCHITECTURE.md`](./ARCHITECTURE.md) §4 along with how each intent answer biases the recommendations downstream.

## Architecture diagram

[`ARCHITECTURE.md`](./ARCHITECTURE.md) contains three ASCII diagrams:

1. **Workflow** — every step from user prompt to final Markdown, showing which steps are Claude reasoning vs. Python scripts vs. user pauses
2. **Data-source decision** — how `fetch_listing.py` picks between live SerpApi, the 7-day local cache, and the mock JSON fallback (with retry behavior)
3. **File layout** — every file in the repo, with arrows showing which script reads or writes which data

A concise file-tree summary is also embedded in [`README.md`](./README.md#architecture).

## How the Ally SKUs were created

[`data/ally_skus.csv`](./data/ally_skus.csv) is **fully fabricated** — Ally Audio is a fictional brand invented for this take-home; the assignment did not provide a sample catalog. The CSV was synthesized in an iterative Claude Code session with the following product decisions made deliberately:

- **Brand positioning:** mid-market lifestyle audio brand — the gap between budget JLab and premium Bose
- **Catalog size:** 6 SKUs spanning the sub-categories a real multi-product audio brand would own — over-ear ANC, true wireless earbuds, on-ear commuter, sport buds, wired studio monitors, kids' headphones
- **Content quality spread:** deliberately uneven (2 strong, 2 middling, 2 weak) so the skill has both subtle and obvious targets to recommend against. The two weakest SKUs (`ALY-DASH-SPORT-004`, `ALY-STUDIO-50-005`) are the most demo-friendly because the gap between current copy and a guideline-compliant rewrite is dramatic
- **Image URLs:** `picsum.photos/seed/<slug>/800/800` placeholders — deterministic per SKU and actually resolve
- **Multi-value fields** (`bullets`, `image_urls`) use `|` as the in-cell delimiter to keep the CSV single-line per row

No real Amazon catalog data was scraped or referenced. Brand and SKU names are invented.

Full provenance with rationale: [`README.md` → Data Provenance](./README.md#data-provenance).

## How the Amazon guidelines were constructed

[`data/amazon_content_guidelines.md`](./data/amazon_content_guidelines.md) is **compiled from real Amazon-published sources**. A Claude Code research agent ran targeted web searches and fetches, extracted concrete cite-able rules, and compiled them into a single Markdown file with the source URL inline on every rule so the skill can cite them on every recommendation.

**Primary sources** (publicly accessible Amazon PDFs — most rules trace back to these):

- [Amazon Listings — Product Detail Page Guide (PDF)](https://m.media-amazon.com/images/G/35/sp-marketing-toolkit/Sellerfacingguides/Amazon_Listings_Product_Detail_Page_Guide.pdf)
- [Category Style Guide: Consumer Electronics and Camera & Photo (PDF, Feb 2018)](https://images-na.ssl-images-amazon.com/images/G/01/rainier/help/CEStyleGuide.pdf)
- [Amazon Seller Forums — New product title requirements effective Jan 21, 2025](https://sellercentral.amazon.com/seller-forums/discussions/t/b2b15728-0d43-453e-974f-59eb63f73059)
- [Prohibited Seller Activities and Actions Policy (PDF)](https://m.media-amazon.com/images/G/31/rainer/ProhibitedSellerActivitiesandActionsPolicy.pdf)

**Reference sources** (Seller Central pages cited by ID; their full text is JS-rendered or login-gated, so the rule text was mirrored from the PDFs above):

- Product title requirements (`GYTR6SYGFA5E3EQC`), bullet point requirements (`GX5L8BF8GLMML6CX`), product detail page rules (`G200390640`), product image guide (`G1881`), technical image file requirements (`G9FUUH87RBNXGKB7`)

**Editorial choices:**

- **Scope is intentionally narrow** — covers what the skill actually uses (titles, bullets, descriptions, prohibited content, image basics). Not exhaustive.
- **Known conflicts are documented inline** — the 2018 CE Style Guide and the 2025 Seller Central update disagree on title length (150 vs 200 chars). Both versions are listed with their sources and a note to prefer the newer rule.
- **Third-party blogs and SEO summaries were deliberately avoided** (Helium 10, Jungle Scout, etc.) so every cited rule traces back to an Amazon-published URL.

Full provenance with source-quality notes: [`README.md` → Data Provenance](./README.md#data-provenance).

## How to run it yourself

```bash
git clone <repo-url>
cd commerIQ_skill

# Optional: live competitor data via SerpApi
cp .env.example .env
# edit .env → set SERPAPI_API_KEY (100 free searches/month). Without a key,
# the skill falls back to bundled mock competitor data and says so explicitly.
```

Open Claude Code in this directory and ask:

> Audit Ally SKU `ALY-DASH-SPORT-004`

The skill auto-loads from `.claude/skills/`. `uv run` handles Python and dependencies automatically on first invocation — no manual `pip install`.

Live run output lands in `output/` (`.gitignored`). The two committed examples in `example_runs/` are hand-promoted from prior runs.
