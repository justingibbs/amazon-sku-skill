# Example runs

Curated outputs from the `competitor-content-intelligence` skill, kept in version control so reviewers can see what a finished audit looks like without running the skill themselves.

These are **examples**, not active output. Live runs land in `output/` (which is `.gitignored`); promising results get copied here by hand.

## Files

| File | SKU | Intent | Notes |
|---|---|---|---|
| `ALY-DASH-SPORT-004_recommendation_20260608.md` | ALY-DASH-SPORT-004 (Ally Dash Sport Earbuds) | #1 Improve search ranking | Stub title (23 chars) and 3 vague bullets rewritten as attribute-stacked copy modeled on 3 live SerpApi competitors. |
| `ALY-STUDIO-50-005_recommendation_20260608.md` | ALY-STUDIO-50-005 (Ally Studio 50 Headphones) | #2 Increase conversion | 25-char title and 3 ultra-terse bullets rewritten into a 135-char spec-rich title and 5 feature-with-benefit bullets ending in an accessories/warranty bullet; modeled on OneOdio, Audio-Technica ATH-M20x, and Philips (all live SerpApi, all A+ Content). |

## Adding a new example

1. Run the skill end-to-end; the final summary lands in `output/`.
2. Copy the file from `output/` into `example_runs/`.
3. Add a row to the table above.
