# Example runs

Curated outputs from the `competitor-content-intelligence` skill, kept in version control so reviewers can see what a finished audit looks like without running the skill themselves.

These are **examples**, not active output. Live runs land in `output/` (which is `.gitignored`); promising results get copied here by hand.

## Files

| File | SKU | Intent | Notes |
|---|---|---|---|
| `B0DGHN493N_recommendation_20260608.md` | B0DGHN493N (BPN Electrolytes Hydration Drink Mix, Sugar Free, Mango, 50 Servings) | #1 Improve search ranking | Audit of a category-#2 SKU. ALL-CAPS bullet prefixes dropped, title expanded with *Rapid Rehydration / Pink Himalayan Salt / Keto / Non-GMO / Informed Sport Tested*, brand-fluff bullet 5 replaced with use-case keywords (*pre-workout, post-training recovery, endurance training*), boilerplate description replaced with keyword-dense rewrite. Modeled on Ultima Replenisher, Nectar, and TREVI (all live SerpApi, all A+ Content). Current BPN era. |
| `ALY-DASH-SPORT-004_recommendation_20260608.md` | ALY-DASH-SPORT-004 (Ally Dash Sport Earbuds) | #1 Improve search ranking | **Legacy (Ally Audio era).** Stub title (23 chars) and 3 vague bullets rewritten as attribute-stacked copy modeled on 3 live SerpApi competitors. Preserved for workflow reference. |
| `ALY-STUDIO-50-005_recommendation_20260608.md` | ALY-STUDIO-50-005 (Ally Studio 50 Headphones) | #2 Increase conversion | **Legacy (Ally Audio era).** 25-char title and 3 ultra-terse bullets rewritten into a 135-char spec-rich title and 5 feature-with-benefit bullets ending in an accessories/warranty bullet; modeled on OneOdio, Audio-Technica ATH-M20x, and Philips (all live SerpApi, all A+ Content). Preserved for workflow reference. |

## Adding a new example

1. Run the skill end-to-end; the final summary lands in `output/`.
2. Copy the file from `output/` into `example_runs/`.
3. Add a row to the table above.
