---
name: competitor-content-intelligence
description: Use when the user wants to audit, improve, or optimize an Ally Audio product listing (SKU) by comparing it to live competitor listings on Amazon and generating ready-to-use, guideline-compliant content edits. Trigger phrases include "improve my listing", "audit this SKU", "compare to competitors", "what should I change about <SKU>", "optimize my Amazon listing".
---

# Competitor Content Intelligence

You help Ally Audio improve product listings on Amazon by comparing their content to live competitor SKUs and producing recommended edits that comply with Amazon's published content rules.

## Workflow

Follow this flow in order. Pause for the user where noted — do not race ahead.

### Step 1 — Identify the SKU

If the user already named a SKU, skip to loading it. Otherwise:

```
uv run .claude/skills/competitor-content-intelligence/scripts/get_sku.py --list
```

Show the user the list and ask which SKU to audit. Once they pick:

```
uv run .claude/skills/competitor-content-intelligence/scripts/get_sku.py --sku-id <ID>
```

### Step 2 — Clarify intent

Ask the user (verbatim or close to it):

> What's your goal for this audit?
> 1. **Improve search ranking** — make the listing more discoverable
> 2. **Increase conversion** — make shoppers more likely to buy once they land on the page
> 3. **Ensure Amazon compliance** — fix anything that violates Amazon's content rules
> 4. **All of the above**

Do not proceed until the user picks one. Use the answer to bias later recommendations:
- **#1 Search ranking** → prioritize keyword density in titles, attribute coverage, search-relevant terms in bullets
- **#2 Conversion** → prioritize benefit-first bullet structure, descriptive depth, scannability, social-proof-adjacent specs (battery hours, warranty, included items)
- **#3 Compliance** → prioritize rule violations (banned terms, ALL CAPS, special characters, prohibited claims)
- **#4 All** → balance across all three

### Step 3 — Fetch competitors

Construct a search query from the SKU. Use the **product category + key attributes**, NOT Ally's brand name. Example: for the Aura Pro, query `"wireless noise cancelling over-ear headphones"`, not `"Ally Aura Pro"`.

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

### Step 4 — Compare

Build a comparison table covering Ally + the 3 competitors:

| Attribute | Ally SKU | Competitor 1 | Competitor 2 | Competitor 3 |
|---|---|---|---|---|
| Title length (chars) | | | | |
| Title keyword coverage | | | | |
| Bullet count | | | | |
| Avg bullet length | | | | |
| Description length | | | | |
| Notable strengths | | | | |
| Notable gaps | | | | |

Call out the most striking differences in 1–2 sentences after the table.

**A+ Content caveat for the description row:** SerpApi returns an empty description for any listing where the seller uses Amazon A+ Content (image-based rich descriptions) instead of a text description. The new `description_format` field in each listing distinguishes `"text"`, `"a_plus_content"`, and `"empty"`. When a competitor's `description_format` is `"a_plus_content"`, mark its description row as **"A+ Content (text not extractable)"** rather than "0 chars" — a 0-char reading would falsely inflate Ally's relative description score. Note this caveat in the prose below the table when at least one competitor uses A+ Content.

### Step 5 — Recommend top 3 edits

Generate the **top 3 highest-impact edits** to the Ally SKU. For each edit:

1. **What to change** — title / bullet N / description
2. **Before** — the current Ally content
3. **After** — the proposed rewrite
4. **Why** — tie to the user's stated intent from Step 2
5. **Competitor reference** — "Competitor 2 (Sony WH-1000XM5) leads with battery life as their second bullet, which their reviewers cite repeatedly"
6. **Amazon rule citation** — the specific rule from `<project-root>/data/amazon_content_guidelines.md` with its source URL

Use Read to load `<project-root>/data/amazon_content_guidelines.md` (i.e. the `data/` directory at the project root, NOT the skill's own `data/` subdirectory) before generating recommendations so you can cite specific rules with their URLs. Do **not** invent rules from training-data memory.

### Step 6 — Get user approval

Present the 3 edits, then ask:

> Approve these edits as-is? (`approve` / `revise <which one>` / `regenerate all`)

If revising, iterate. Only proceed to Step 7 once the user explicitly approves.

### Step 7 — Produce final Markdown summary

Write to `output/<sku_id>_recommendation_<YYYYMMDD>.md` (create the `output/` directory if missing). The summary contains:

1. **Header** — SKU ID, brand, category, audit date, user-stated intent
2. **Current content** — title, bullets, description as they exist today
3. **Approved edits** — for each: before, after, rationale, competitor reference, Amazon rule citation (with URL)
4. **Paste-ready section** — final title, final bullets (as a list), final description, formatted so the user can copy each field directly into Seller Central
5. **Sources** — links to all Amazon rule URLs cited
6. **Data provenance** — list each competitor ASIN with its `source` (`serpapi`, `serpapi_cache`, or `mock`), not just an aggregate note. Flag any ASINs whose `description_format` is `"a_plus_content"` so the reader knows the description-length comparison was adjusted for that.

After writing, print the file path and a 2-sentence summary of what changed.

## Hard rules

- **Always cite the Amazon rule URL inline** next to each recommendation. No exceptions.
- **Never invent a competitor.** If `find_competitors.py` returns mock data, say so explicitly.
- **Don't quote Amazon rules from training memory.** Load `<project-root>/data/amazon_content_guidelines.md` and cite from there.
- **Don't recommend edits that violate Amazon's rules** (e.g., adding "Free shipping" or "Best Seller" to the title).
- **Don't skip Step 2 or Step 6.** Intent and approval are core to the product.

## Reference files

All paths are relative to the project root (`/Users/justingibbs/Projects/commerIQ_skill/`).

- `data/ally_skus.csv` — Ally's product catalog (input; lives in the project-root `data/`)
- `data/amazon_content_guidelines.md` — Compiled Amazon rules with source URLs (lives in the project-root `data/`; load via Read when generating recommendations)
- `.claude/skills/competitor-content-intelligence/data/mock_competitors.json` — Fallback competitor data when no SerpApi key is configured (lives in the skill's own `data/` subdirectory — distinct from the project-root `data/`)
