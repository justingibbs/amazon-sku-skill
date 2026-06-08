# Architecture

Three diagrams. Read top-to-bottom.

1. **Workflow** — what happens from the moment a user types an "audit" prompt
2. **Data-source decision** — how `fetch_listing.py` chooses between live SerpApi, local cache, and mock
3. **File layout** — where every file lives and which script touches it

Legend: `[Claude]` = LLM reasoning, `[Python: <script>]` = deterministic script, `[USER]` = pauses for user input.

---

## 1. Workflow

```
                              USER
                                │
                                │  "Audit ALY-DASH-SPORT-004"
                                │  (any prompt with "audit" / "improve listing"
                                │   / "compare to competitors" matches the
                                │   skill's frontmatter description)
                                ▼
            ┌───────────────────────────────────────┐
            │  Claude Code matches the trigger and  │
            │  loads .claude/skills/competitor-     │
            │  content-intelligence/SKILL.md        │
            └───────────────────────────────────────┘
                                │
                                ▼
   ┌──────────────────────────────────────────────────────────┐
   │ Step 1 — Identify SKU             [Python: get_sku.py]   │
   │   reads:  data/ally_skus.csv                             │
   │   emits:  title, bullets, description, brand, category   │
   └──────────────────────────────────────────────────────────┘
                                │
                                ▼
   ┌──────────────────────────────────────────────────────────┐
   │ Step 2 — Clarify intent              [Claude + USER]     │
   │   asks: ranking / conversion / compliance / all          │
   │   PAUSES for user answer                                 │
   │   biases Steps 4-5 toward the chosen lens                │
   └──────────────────────────────────────────────────────────┘
                                │
                                ▼
   ┌──────────────────────────────────────────────────────────┐
   │ Step 3 — Fetch competitors      [Python: 2 scripts]      │
   │                                                          │
   │   (a) find_competitors.py --query "<category words>"     │
   │       calls: SerpApi amazon search engine                │
   │       emits: 3 ASINs with titles + ratings + price       │
   │                                                          │
   │   (b) fetch_listing.py --asin <ASIN>   × 3 (parallel)    │
   │       calls: SerpApi amazon_product engine               │
   │              → cache → mock (see Diagram 2)              │
   │       emits: full title/bullets/description + source     │
   │              + description_format flag                   │
   └──────────────────────────────────────────────────────────┘
                                │
                                ▼
   ┌──────────────────────────────────────────────────────────┐
   │ Step 4 — Compare                            [Claude]     │
   │   builds attribute table: Ally vs Comp 1 / 2 / 3         │
   │   adjusts the description row for competitors whose      │
   │     description_format is "a_plus_content"               │
   │     (renders "A+ Content (text not extractable)" instead │
   │      of misleadingly counting 0 chars)                   │
   └──────────────────────────────────────────────────────────┘
                                │
                                ▼
   ┌──────────────────────────────────────────────────────────┐
   │ Step 5 — Recommend top 3 edits              [Claude]     │
   │   reads:  data/amazon_content_guidelines.md              │
   │   each edit ties to:                                     │
   │     · user intent (from Step 2)                          │
   │     · a specific competitor with their ASIN              │
   │     · a specific Amazon rule with its source URL         │
   └──────────────────────────────────────────────────────────┘
                                │
                                ▼
   ┌──────────────────────────────────────────────────────────┐
   │ Step 6 — Approval                    [Claude + USER]     │
   │   user replies: approve / revise N / regenerate all      │
   │   PAUSES until "approve"                                 │
   │   on "revise N", iterates on that edit only              │
   └──────────────────────────────────────────────────────────┘
                                │
                                ▼
   ┌──────────────────────────────────────────────────────────┐
   │ Step 7 — Write summary                      [Claude]     │
   │   writes: output/<SKU>_recommendation_<YYYYMMDD>.md      │
   │   sections:                                              │
   │     · header (SKU, brand, audit date, user intent)       │
   │     · current content                                    │
   │     · approved edits (before/after/why/competitor/rule)  │
   │     · paste-ready fields (drop into Seller Central)      │
   │     · sources (all rule URLs)                            │
   │     · data provenance (per-ASIN source)                  │
   └──────────────────────────────────────────────────────────┘
                                │
                                ▼
                              USER
                       (copies paste-ready
                        fields into Seller
                        Central)
```

---

## 2. Data-source decision (per ASIN)

Used by `fetch_listing.py` for every competitor ASIN in Step 3. Three tiers, each falls through to the next on failure. The script always exits 0 with a structured JSON result so a single failure can't cascade-cancel sibling parallel fetches.

```
    fetch_listing.py --asin <ASIN>
              │
              ▼
   ┌─────────────────────────────────────────────────────────┐
   │ Tier 1 — SerpApi (live)                                 │
   │   up to 4 attempts · 45s timeout each                   │
   │   backoff: sleep 1s, 3s, 8s between retries             │
   ├─────────────────────────────────────────────────────────┤
   │ success (200 + non-empty product fields)                │
   │   → source = "serpapi"                                  │
   │   → write data/.cache/listings/<ASIN>.json              │
   │   → return status "ok"                                  │
   │                                                         │
   │ retry-eligible failure (timeout, 5xx, network error)    │
   │   → exhausts attempts, falls through                    │
   │                                                         │
   │ terminal failure (4xx, no API key, no `requests` lib,   │
   │ or 200 with empty fields = ASIN not found)              │
   │   → no retry, falls through immediately                 │
   └─────────────────────────────────────────────────────────┘
              │
              ▼
   ┌─────────────────────────────────────────────────────────┐
   │ Tier 2 — Local cache (7-day TTL)                        │
   │   data/.cache/listings/<ASIN>.json                      │
   ├─────────────────────────────────────────────────────────┤
   │ fresh hit (file exists, fetched_at within 7 days)       │
   │   → source = "serpapi_cache"                            │
   │   → return status "ok"                                  │
   │                                                         │
   │ miss (no file, stale, or malformed)                     │
   │   → falls through                                       │
   │                                                         │
   │ skipped if --no-cache flag is set                       │
   └─────────────────────────────────────────────────────────┘
              │
              ▼
   ┌─────────────────────────────────────────────────────────┐
   │ Tier 3 — Mock data                                      │
   │   .claude/skills/.../data/mock_competitors.json         │
   ├─────────────────────────────────────────────────────────┤
   │ ASIN present in mock                                    │
   │   → source = "mock"                                     │
   │   → return status "ok"                                  │
   │                                                         │
   │ ASIN not in mock set                                    │
   │   → return status "no_data"                             │
   │   → reason "asin_not_in_mock_set"                       │
   │   → source: null                                        │
   └─────────────────────────────────────────────────────────┘

   Script always exits 0 → parallel callers in Step 3 won't
   cascade-cancel. The Step 4 comparison surfaces the per-ASIN
   source label so the user knows whether data is live, cached,
   or mocked.
```

`find_competitors.py` uses the same retry-with-backoff against SerpApi's search engine, then falls back to mock data scoped to the closest matching category. It does not use the cache because search queries vary per audit; the cache only makes sense for ASIN-keyed lookups.

---

## 3. File layout

```
amazon-sku-skill/
│
├── .claude/skills/competitor-content-intelligence/
│   ├── SKILL.md ──────────────────────► [read by] Claude (the prompt)
│   │
│   ├── scripts/
│   │   ├── get_sku.py ────────────────► reads:  data/ally_skus.csv
│   │   │
│   │   ├── find_competitors.py ───────► calls:  SerpApi search engine
│   │   │                                 falls back to:
│   │   │                                   data/mock_competitors.json
│   │   │
│   │   └── fetch_listing.py ──────────► calls:  SerpApi product engine
│   │                                     writes/reads:
│   │                                       data/.cache/listings/
│   │                                     falls back to:
│   │                                       data/mock_competitors.json
│   │
│   └── data/
│       ├── mock_competitors.json ─────► fallback competitor catalog
│       └── .cache/listings/ ──────────► per-ASIN JSON cache
│                                          7-day TTL, gitignored
│
├── data/
│   ├── ally_skus.csv ─────────────────► Ally catalog (read-only)
│   │                                     consumed in Step 1
│   │
│   └── amazon_content_guidelines.md ──► [read by] Claude in Step 5
│                                          to cite rule URLs
│
├── output/                             ► generated recommendations
│   └── <SKU>_recommendation_           (gitignored)
│       <YYYYMMDD>.md
│
├── .env ──────────────────────────────► SERPAPI_API_KEY (gitignored)
├── .env.example
├── pyproject.toml ────────────────────► uv resolves these on first
├── uv.lock                                run; no manual pip install
└── README.md
```

**Read-only inputs:** `data/ally_skus.csv`, `data/amazon_content_guidelines.md`, `data/mock_competitors.json` (inside the skill dir).

**Generated artifacts:** `output/*.md` (recommendation summaries), `data/.cache/listings/*.json` (SerpApi cache). Both gitignored.

**Secrets:** `.env` holds `SERPAPI_API_KEY` and is gitignored; `.env.example` documents the variable without the value.
