# Submission Map — BPN Competitor Content Intelligence Skill

A quick-reference map of where every assignment deliverable lives. For setup, design rationale, and the product brief, see [`README.md`](./README.md).

## TL;DR for the evaluator

1. **What to read first:** [`README.md`](./README.md) (overview, setup, design decisions, product brief, assumptions, edge cases)
2. **What to read next:** [`ARCHITECTURE.md`](./ARCHITECTURE.md) (workflow diagram, data-source fallback, file layout, verbatim user-facing prompts)
3. **What to skim for examples:** [`example_runs/`](./example_runs/) — start with [`B0DGHN493N_recommendation_20260608.md`](./example_runs/B0DGHN493N_recommendation_20260608.md) (current BPN-era audit); two prior Ally Audio runs are preserved as legacy references
4. **What to read to grade the agent:** [`.claude/skills/competitor-content-intelligence/SKILL.md`](./.claude/skills/competitor-content-intelligence/SKILL.md) (the full prompt that drives Claude)

## Assignment requirements → file map

| Assignment requirement | Where to find it |
|---|---|
| Skill that compares a SKU to competitors and recommends edits | [`.claude/skills/competitor-content-intelligence/SKILL.md`](./.claude/skills/competitor-content-intelligence/SKILL.md) — the agent prompt; defines the 7-step workflow |
| Comparison report (title length, bullets, description, attributes) | Produced in Step 4 of the skill; comparison table also includes rating, reviews, price, BSR snapshot, and a labeled CIQ-historical rank row |
| Top 3 edits with competitor references and Amazon rule citations | Produced in Step 5; citations come from the Pet Supplies styleguide (primary) and the broader Amazon rule compilation (secondary, URL-cite-able) |
| Final Markdown summary on user approval | Produced in Step 7 and written to `output/<ASIN>_recommendation_<date>.md` |
| README — setup, assumptions, product brief | [`README.md`](./README.md) (Setup, Assumptions, Product brief sections) |
| Prompts | [`.claude/skills/competitor-content-intelligence/SKILL.md`](./.claude/skills/competitor-content-intelligence/SKILL.md) is the primary prompt. Verbatim user-facing prompts from each pause point are in [`ARCHITECTURE.md`](./ARCHITECTURE.md) §4. |
| Example I/O | [`example_runs/`](./example_runs/) — one current BPN-era audit (`B0DGHN493N`) + two legacy Ally Audio runs preserved for workflow reference |
| Architecture diagram | [`ARCHITECTURE.md`](./ARCHITECTURE.md) — ASCII diagrams of (1) end-to-end workflow, (2) SerpApi → cache → mock fallback, (3) file layout with per-script data flow |
| Edge cases | [`README.md`](./README.md#edge-cases-documented-not-all-solved) |
| Loom walkthrough | (Recorded separately — link delivered with the submission) |

## Inputs the skill consumes

The two files CIQ provides for the assignment are both honored:

| CIQ-provided input | How the skill uses it |
|---|---|
| `data/asin_data_filled.csv` (154 rows, multi-brand, multi-universe) | Treated as the upstream catalog. The 15 `BARE PERFORMANCE NUTRITION` rows are extracted into `data/bpn_skus.csv` and used as the client SKU catalog. The skill's `--csv` flag can also point at the full file or any other subset. |
| `data/PetSupplies_PetFood_Styleguide_EN_AE._CB1198675309_.pdf` | Extracted page-by-page into `data/amazon_styleguide_extracted.md` by `scripts/extract_styleguide.py`. Used as the **primary** Amazon-rule citation source. Treated as universal across categories per the assignment's explicit instruction ("Assume the same content guidelines apply to all categories"). |

## Why BPN as the client

The new CSV CIQ supplied does not designate an "Ally" client. `BARE PERFORMANCE NUTRITION` was chosen as the client stand-in because:

- It is the brand with the largest contiguous footprint in the export (15 ASINs across 3 universes — beverages, snacks & sweets, breakfast cereal — all within one Amazon category node: *Sports Nutrition → Electrolyte Replacements*)
- The catalog is real (real ASINs the evaluator can verify on amazon.com) and reasonably diverse (different flavors, pack sizes, and a sister product line — `G.1.M Go One More Sport`)
- The category has many recognizable competitors (Gatorade, Liquid I.V., Nuun, Gatorlyte, LMNT) for the live-search step to surface

Any other brand subset would also work — the skill's `--csv` flag accepts arbitrary catalog files in the same schema.

## Example runs

End-to-end audits committed under [`example_runs/`](./example_runs/). The BPN-era run is the current reference; the two Ally Audio runs are preserved as legacy workflow examples (same 7-step flow, different client / different category).

| Run | SKU | Intent | What it demonstrates |
|---|---|---|---|
| [`B0DGHN493N_recommendation_20260608.md`](./example_runs/B0DGHN493N_recommendation_20260608.md) | BPN Electrolytes Hydration Drink Mix, Sugar Free, Mango, 50 Servings (current BPN era) | Improve search ranking | Audit of a category-#2 SKU. ALL-CAPS bullet prefixes dropped, title expanded with *Rapid Rehydration / Pink Himalayan Salt / Keto / Non-GMO / Informed Sport Tested*, brand-fluff bullet 5 replaced with use-case keywords (*pre-workout, post-training recovery, endurance training*), boilerplate description replaced with keyword-dense rewrite. Modeled on Ultima Replenisher, Nectar, and TREVI (all live SerpApi, all A+ Content). |
| [`ALY-DASH-SPORT-004_recommendation_20260608.md`](./example_runs/ALY-DASH-SPORT-004_recommendation_20260608.md) | True Wireless Earbuds (legacy Ally Audio) | Improve search ranking | Stub title (23 chars) → 144-char attribute-stacked title; vague bullets → 5 keyword-rich bullets |
| [`ALY-STUDIO-50-005_recommendation_20260608.md`](./example_runs/ALY-STUDIO-50-005_recommendation_20260608.md) | Wired Studio Headphones (legacy Ally Audio) | Increase conversion | 25-char title → 135-char spec-rich title; 3 ultra-terse bullets → 5 feature-with-benefit bullets ending in an accessories/warranty bullet |

All three runs used live SerpApi data. Live `output/` is `.gitignored`; promoted runs are hand-copied into `example_runs/`.

## Agent prompts

The skill's full prompt is [`.claude/skills/competitor-content-intelligence/SKILL.md`](./.claude/skills/competitor-content-intelligence/SKILL.md). It defines:

- **Frontmatter `description`** — trigger conditions (Claude Code uses this to decide when to load the skill)
- **7-step workflow** — identify SKU → clarify intent → fetch competitors → compare → recommend → approve → produce summary
- **Hard rules** — always cite Amazon page/URL inline, never invent a competitor, never quote rules from memory, don't recommend rule-violating edits, never silently mix CIQ historical rank with SerpApi BSR snapshot, don't skip intent or approval

The verbatim user-facing question text (the intent menu in Step 2 and the approval prompt in Step 6) is reproduced in [`ARCHITECTURE.md`](./ARCHITECTURE.md) §4 along with how each intent answer biases the recommendations downstream.

## Architecture diagram

[`ARCHITECTURE.md`](./ARCHITECTURE.md) contains three ASCII diagrams:

1. **Workflow** — every step from user prompt to final Markdown, showing which steps are Claude reasoning vs. Python scripts vs. user pauses
2. **Data-source decision** — how `fetch_listing.py` picks between live SerpApi, the 7-day local cache, and the mock JSON fallback (with retry behavior)
3. **File layout** — every file in the repo, with arrows showing which script reads or writes which data

A concise file-tree summary is also embedded in [`README.md`](./README.md#architecture).

## How the BPN catalog was built

[`data/bpn_skus.csv`](./data/bpn_skus.csv) is the 15 rows from CIQ's [`data/asin_data_filled.csv`](./data/asin_data_filled.csv) where `retailer_brand_name = "BARE PERFORMANCE NUTRITION"`, preserving the upstream schema verbatim. Generated with a few lines of Python (see Git history for the exact filter). The skill's `--csv` flag can point at any other subset of the same schema, so this file is conceptually just the default.

Full provenance: [`README.md` → Data Provenance](./README.md#data-provenance).

## How the Amazon guidelines were constructed

Two sources, in priority order:

**Primary — [`data/amazon_styleguide_extracted.md`](./data/amazon_styleguide_extracted.md)**: A page-by-page Markdown extraction of CIQ's provided PDF (`PetSupplies_PetFood_Styleguide_EN_AE._CB1198675309_.pdf`), produced by `scripts/extract_styleguide.py`. Citations reference the page number (e.g., *Amazon Pet Supplies Styleguide, p. 12*). Per the assignment, treated as universal across categories.

**Secondary — [`data/amazon_content_guidelines.md`](./data/amazon_content_guidelines.md)**: A broader Markdown compilation of Amazon's publicly accessible content rules, with source URLs inline. Used when the styleguide does not cover a specific rule, or when a clickable URL is more useful.

The secondary compilation was built by a Claude Code research agent. Source quality, conflict notes, and editorial choices are documented in [`README.md` → Data Provenance](./README.md#data-provenance).

## How to run it yourself

```bash
git clone <repo-url>
cd commerIQ_skill

# Optional: live competitor data via SerpApi
cp .env.example .env
# edit .env → set SERPAPI_API_KEY (100 free searches/month). Without a key,
# the skill falls back to bundled mock competitor data and says so explicitly.

# One-time: extract the styleguide PDF into a citable MD file
uv run .claude/skills/competitor-content-intelligence/scripts/extract_styleguide.py
```

Open Claude Code in this directory and ask:

> Audit BPN SKU `B0DGHN493N`

The skill auto-loads from `.claude/skills/`. `uv run` handles Python and dependencies automatically on first invocation — no manual `pip install`.

Live run output lands in `output/` (`.gitignored`). Promoted examples are hand-copied into `example_runs/`.
