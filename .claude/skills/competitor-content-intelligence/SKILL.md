---
name: competitor-content-intelligence
description: Use when the user wants to audit, improve, or optimize a BARE PERFORMANCE NUTRITION (BPN) product listing (SKU) by comparing it to live competitor listings on Amazon and generating ready-to-use, guideline-compliant content edits. Trigger phrases include "improve my listing", "audit this SKU", "compare to competitors", "what should I change about <ASIN>", "optimize my Amazon listing".
---

# Competitor Content Intelligence

You help BARE PERFORMANCE NUTRITION (BPN) improve product listings on Amazon by comparing their content to live competitor SKUs and producing recommended edits that comply with Amazon's published content rules.

## Workflow

Follow this flow in order. Pause for the user where noted — do not race ahead.

### Step 1 — Identify the SKU

If the user already named a SKU (an ASIN like `B0DGHN493N`), skip to loading it. Otherwise:

```
uv run .claude/skills/competitor-content-intelligence/scripts/get_sku.py --list
```

Show the user the list and ask which SKU to audit. Once they pick:

```
uv run .claude/skills/competitor-content-intelligence/scripts/get_sku.py --sku-id <ASIN>
```

The returned record exposes content fields (`title`, `bullets`, `description`, `image_urls`, `brand`, `category_node`, `universe`) plus a `ranks` object with CommerceIQ's historical `min/avg_rank_search` and `min/avg_rank_category`. Use the ranks to set context in Step 4 — a SKU ranked #2 in its category needs different framing than one ranked #84.

### Step 2 — Clarify intent

Ask the user (verbatim or close to it):

> What's your goal for this audit?
> 1. **Improve search ranking** — make the listing more discoverable
> 2. **Increase conversion** — make shoppers more likely to buy once they land on the page
> 3. **Ensure Amazon compliance** — fix anything that violates Amazon's content rules
> 4. **All of the above**

Do not proceed until the user picks one. Use the answer to bias later recommendations:
- **#1 Search ranking** → prioritize keyword density in titles, attribute coverage, search-relevant terms in bullets
- **#2 Conversion** → prioritize benefit-first bullet structure, descriptive depth, scannability, social-proof-adjacent specs (servings, electrolyte profile, certifications, included accessories)
- **#3 Compliance** → prioritize rule violations (banned terms, ALL CAPS, special characters, prohibited claims, prohibited promotional language)
- **#4 All** → balance across all three

### Step 3 — Fetch competitors

Construct a search query from the SKU. Use the **product category + key attributes**, NOT BPN's brand name. Example: for `B0DGHN493N` (BPN Electrolytes Hydration Drink Mix), query `"sugar free electrolyte hydration powder"`, not `"BPN Electrolytes"`. Use the SKU's `category_node` breadcrumb (e.g., "Sports Nutrition → Electrolyte Replacements") as a guide for which descriptors to use.

```
uv run .claude/skills/competitor-content-intelligence/scripts/find_competitors.py --query "<query>" --limit 3
```

For each returned ASIN, fetch full details:

```
uv run .claude/skills/competitor-content-intelligence/scripts/fetch_listing.py --asin <ASIN>
```

`fetch_listing.py` always exits 0 and emits a JSON object with a `status` field:
- `"ok"` — fields are populated; `source` is `serpapi`, `serpapi_cache`, or `mock`
- `"no_data"` — the ASIN was not found on SerpApi (live or cached) and isn't in the mock set; `reason` indicates why

If a fetch returns `"no_data"`, retry once (transient SerpApi failures are common; the script already retries 3× internally with backoff, but a second invocation may still help). If a second attempt also returns `"no_data"`, drop that ASIN from the comparison and pull a replacement competitor from the search results instead of using a hollow entry.

You can fetch multiple ASINs in parallel safely — a single failure no longer cancels the other tool calls (each call exits 0 with a structured result).

Track the `source` per ASIN — `serpapi` (live), `serpapi_cache` (served from 7-day local cache), or `mock` (fallback). You will need this in Step 7.

**Live `fetch_listing.py` output is richer than the BPN CSV.** It returns `rating`, `reviews`, `price`, `categories` (breadcrumb), `images`, and `bestsellers_rank` (a **point-in-time** snapshot) on top of the title/bullets/description. Use those extra fields in Step 4.

### Step 4 — Compare

Build a comparison table covering BPN + the 3 competitors:

| Attribute | BPN SKU | Competitor 1 | Competitor 2 | Competitor 3 |
|---|---|---|---|---|
| Title length (chars) | | | | |
| Title keyword coverage | | | | |
| Bullet count | | | | |
| Avg bullet length | | | | |
| Description length | | | | |
| Star rating | n/a (CSV) | | | |
| Review count | n/a (CSV) | | | |
| Price | n/a (CSV) | | | |
| Best Sellers Rank (snapshot) | CIQ avg: `<avg_rank_category>` | | | |
| Notable strengths | | | | |
| Notable gaps | | | | |

Call out the most striking differences in 1–2 sentences after the table.

**Rank-signal caveat — important.** The BPN SKU's rank columns (`min_rank_search`, `avg_rank_search`, `min_rank_category`, `avg_rank_category`) are **CommerceIQ's historical aggregates** across many queries and timepoints. The competitor `bestsellers_rank` field from SerpApi is a **point-in-time snapshot** of Amazon's Best Sellers Rank. These two are not directly comparable. When you mention competitor BSR alongside BPN's avg rank, label them clearly so the reader doesn't compare apples to oranges. If a competitor's BSR is unavailable, write "BSR not surfaced" rather than blanking the cell.

**A+ Content caveat for the description row:** SerpApi returns an empty description for any listing where the seller uses Amazon A+ Content (image-based rich descriptions) instead of a text description. The `description_format` field in each listing distinguishes `"text"`, `"a_plus_content"`, and `"empty"`. When a competitor's `description_format` is `"a_plus_content"`, mark its description row as **"A+ Content (text not extractable)"** rather than "0 chars" — a 0-char reading would falsely inflate BPN's relative description score. Note this caveat in the prose below the table when at least one competitor uses A+ Content.

### Step 5 — Recommend top 3 edits

Generate the **top 3 highest-impact edits** to the BPN SKU. For each edit:

1. **What to change** — title / bullet N / description
2. **Before** — the current BPN content
3. **After** — the proposed rewrite
4. **Why** — tie to the user's stated intent from Step 2
5. **Competitor reference** — "Competitor 2 (Gatorlyte, B0BGR6842K) leads with electrolyte composition in their fourth bullet, which makes the product's hydration claim concrete"
6. **Amazon rule citation** — the specific rule, cited from the guidelines source documents (see "Guidelines sources" below)

**Guidelines sources** — load both before generating recommendations:

- **`<project-root>/data/amazon_styleguide_extracted.md`** — the Amazon Pet Supplies Styleguide CommerceIQ provided for this take-home, extracted page-by-page. Per the assignment, treat its rules as universal (applying across all categories, including sports nutrition). Cite as *Amazon Pet Supplies Styleguide, p. N*.
- **`<project-root>/data/amazon_content_guidelines.md`** — a broader compilation of Amazon's publicly-published content rules with source URLs. Use this when the Pet Supplies styleguide does not cover the specific rule, or when a citation with a clickable URL adds value (e.g., the 2025 200-character title-limit update). Cite as *Amazon — <rule topic> ([source URL])*.

Prefer the Pet Supplies styleguide as the primary citation when it speaks to the rule; reach to the broader compilation when it doesn't. **Do not invent rules from training-data memory.** Every recommendation must trace to one of the two source files.

### Step 6 — Get user approval

Present the 3 edits, then ask:

> Approve these edits as-is? (`approve` / `revise <which one>` / `regenerate all`)

If revising, iterate. Only proceed to Step 7 once the user explicitly approves.

### Step 7 — Produce final Markdown summary

Write to `output/<sku_id>_recommendation_<YYYYMMDD>.md` (create the `output/` directory if missing). The summary contains:

1. **Header** — SKU ID (ASIN), brand, category breadcrumb, audit date, user-stated intent
2. **Current content** — title, bullets, description as they exist today
3. **Approved edits** — for each: before, after, rationale, competitor reference, Amazon rule citation (with URL where available)
4. **Paste-ready section** — final title, final bullets (as a list), final description, formatted so the user can copy each field directly into Seller Central
5. **Sources** — the styleguide page references and any URLs cited
6. **Data provenance** — list each competitor ASIN with its `source` (`serpapi`, `serpapi_cache`, or `mock`), plus its `rating`/`reviews`/`price` snapshot. Flag any ASINs whose `description_format` is `"a_plus_content"` so the reader knows the description-length comparison was adjusted for that. Note explicitly that BPN's rank columns are CIQ historical aggregates while competitor BSR (if shown) is a SerpApi snapshot.

After writing, print the file path and a 2-sentence summary of what changed.

## Hard rules

- **Always cite the Amazon rule** next to each recommendation (page in the styleguide, or URL from the broader compilation). No exceptions.
- **Never invent a competitor.** If `find_competitors.py` returns mock data, say so explicitly.
- **Don't quote Amazon rules from training memory.** Load the two guideline files (above) and cite from them.
- **Don't recommend edits that violate Amazon's rules** (e.g., adding "Free shipping" or "Best Seller" to the title, using ALL CAPS, or including a promotional claim).
- **Don't conflate CIQ historical rank with SerpApi BSR snapshot.** They measure different things.
- **Don't skip Step 2 or Step 6.** Intent and approval are core to the product.

## Reference files

All paths are relative to the project root (`/Users/justingibbs/Projects/commerIQ_skill/`).

- `data/bpn_skus.csv` — BPN's product catalog (input; the 15 BARE PERFORMANCE NUTRITION rows extracted from `data/asin_data_filled.csv`). Schema mirrors the CommerceIQ asin_data export.
- `data/asin_data_filled.csv` — Full CommerceIQ ASIN export (154 rows across multiple brands and universes). Not used directly by the skill; the BPN subset above is the live catalog. Available for reference and as the upstream source.
- `data/amazon_styleguide_extracted.md` — Amazon Pet Supplies Styleguide (the PDF CommerceIQ provided), extracted page-by-page. Primary citation source. Load via Read when generating recommendations.
- `data/amazon_content_guidelines.md` — Broader Amazon content rules with URL citations. Secondary source — use when the styleguide doesn't cover a rule, or when a clickable URL is more useful.
- `.claude/skills/competitor-content-intelligence/data/mock_competitors.json` — Fallback competitor data (real ASINs from sports nutrition / electrolyte brands) used when no SerpApi key is configured.
