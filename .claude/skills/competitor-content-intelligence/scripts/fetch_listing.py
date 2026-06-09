#!/usr/bin/env python3
"""Fetch a single Amazon product listing's title, bullets, and description.

Always exits 0 and emits a JSON object with a top-level "status" field:
- "ok"      — fields populated; "source" indicates origin
- "no_data" — nothing returned; "reason" indicates why

This lets parallel callers continue when a single fetch fails. Diagnostic
detail goes to stderr.

Usage:
    python fetch_listing.py --asin B09XS7JWHH
    python fetch_listing.py --asin B09XS7JWHH --no-cache
"""

import argparse
import datetime as _dt
import json
import os
import re
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MOCK_PATH = DATA_DIR / "mock_competitors.json"
CACHE_DIR = DATA_DIR / ".cache" / "listings"
SERPAPI_ENDPOINT = "https://serpapi.com/search.json"

SERPAPI_TIMEOUT_SECONDS = 45
RETRY_BACKOFF_SECONDS = [1, 3, 8]  # sleep before attempts 2, 3, 4 (max 4 attempts)
CACHE_TTL_SECONDS = 7 * 24 * 3600


def _redact(text: str) -> str:
    """Strip api_key=... from any text so the key never reaches logs or stderr."""
    return re.sub(r"(api_key=)[^&\s'\"]+", r"\1[REDACTED]", text)


def load_env() -> None:
    """Load KEY=VALUE pairs from the repo-root .env into os.environ.

    Walks upward from this script until it finds a .env file. Existing
    environment variables win; .env only fills in what is missing.
    """
    for parent in Path(__file__).resolve().parents:
        env_path = parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())
            return


def _cache_path(asin: str) -> Path:
    return CACHE_DIR / f"{asin}.json"


def load_cache(asin: str) -> dict | None:
    """Return cached listing if present and fresh, else None.

    Cached entries surface as source="serpapi_cache" so downstream consumers
    can distinguish a cached live fetch from a true live fetch.
    """
    path = _cache_path(asin)
    if not path.exists():
        return None
    try:
        with path.open() as f:
            entry = json.load(f)
        fetched_at = _dt.datetime.fromisoformat(entry["fetched_at"])
        age = (_dt.datetime.now(_dt.timezone.utc) - fetched_at).total_seconds()
        if age > CACHE_TTL_SECONDS:
            return None
        data = dict(entry["data"])
        if data.get("source") == "serpapi":
            data["source"] = "serpapi_cache"
        return data
    except Exception as e:
        print(f"WARN: cache read failed for {asin} ({e})", file=sys.stderr)
        return None


def save_cache(asin: str, data: dict) -> None:
    """Persist successful SerpApi fetches. Failures here are non-fatal."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        entry = {
            "asin": asin,
            "fetched_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "data": data,
        }
        with _cache_path(asin).open("w") as f:
            json.dump(entry, f)
    except Exception as e:
        print(f"WARN: cache write failed for {asin} ({e})", file=sys.stderr)


def fetch_serpapi(asin: str) -> dict | None:
    """Fetch product details via SerpApi with retry-with-backoff.

    Returns parsed listing dict on success, None on permanent failure.
    Retries on timeout, connection error, and 5xx; surfaces 4xx immediately.
    """
    api_key = os.environ.get("SERPAPI_API_KEY")
    if not api_key:
        print("WARN: SERPAPI_API_KEY not set (checked environment and .env); "
              "falling back to cache or mock", file=sys.stderr)
        return None
    if requests is None:
        print("WARN: 'requests' not installed; falling back to cache or mock",
              file=sys.stderr)
        return None

    max_attempts = len(RETRY_BACKOFF_SECONDS) + 1
    for attempt in range(1, max_attempts + 1):
        try:
            resp = requests.get(
                SERPAPI_ENDPOINT,
                params={
                    "engine": "amazon_product",
                    "asin": asin,
                    "amazon_domain": "amazon.com",
                    "api_key": api_key,
                },
                timeout=SERPAPI_TIMEOUT_SECONDS,
            )
            # Treat 4xx as terminal (bad request, auth, quota), 5xx as retryable
            if 400 <= resp.status_code < 500:
                print(f"WARN: SerpApi returned {resp.status_code} for {asin} (terminal); "
                      f"falling back to cache or mock", file=sys.stderr)
                return None
            resp.raise_for_status()
            data = resp.json()
            break
        except Exception as e:
            if attempt < max_attempts:
                sleep_for = RETRY_BACKOFF_SECONDS[attempt - 1]
                print(f"WARN: SerpApi product fetch attempt {attempt}/{max_attempts} "
                      f"failed for {asin} ({_redact(str(e))}); retrying in {sleep_for}s",
                      file=sys.stderr)
                time.sleep(sleep_for)
                continue
            print(f"WARN: SerpApi product fetch failed for {asin} after "
                  f"{max_attempts} attempts ({_redact(str(e))}); falling back to "
                  f"cache or mock", file=sys.stderr)
            return None

    pd = data.get("product_results") or {}
    specs = data.get("item_specifications") or {}
    title = pd.get("title")
    bullets = data.get("about_item") or []
    # SerpApi sometimes returns 200 OK with an empty product_results dict for
    # unknown / dead ASINs. Detect that here so we don't surface a hollow "ok".
    if not title and not bullets:
        print(f"WARN: SerpApi returned 200 but no product fields for {asin}; "
              f"treating as not found", file=sys.stderr)
        return None
    # product_description is sometimes a plain string, sometimes a list of A+ Content
    # card dicts (image-based marketing, no useful text). Only treat strings as the description.
    desc_raw = data.get("product_description")
    description = desc_raw if isinstance(desc_raw, str) else ""
    description_format = "text" if description else (
        "a_plus_content" if isinstance(desc_raw, list) and desc_raw else "empty"
    )
    return {
        "asin": asin,
        "title": title,
        "bullets": bullets,
        "description": description,
        "description_format": description_format,
        "brand": specs.get("brand") or pd.get("brand"),
        "rating": pd.get("rating"),
        "reviews": pd.get("reviews"),
        "url": pd.get("link"),
        "categories": _extract_categories(pd),
        "images": _extract_images(pd),
        "price": _extract_price(pd),
        "bestsellers_rank": _extract_bestsellers_rank(pd),
        "source": "serpapi",
    }


def _extract_categories(pd: dict) -> list[str]:
    """Return the Amazon breadcrumb as a flat list of category names.

    SerpApi exposes the breadcrumb as `categories` (a list of {name, link}
    dicts). Falls back to an empty list if absent or malformed.
    """
    raw = pd.get("categories") or []
    if not isinstance(raw, list):
        return []
    names = []
    for c in raw:
        if isinstance(c, dict) and c.get("name"):
            names.append(c["name"])
        elif isinstance(c, str) and c:
            names.append(c)
    return names


def _extract_images(pd: dict) -> list[str]:
    """Return the listing's image URLs.

    SerpApi shapes vary: sometimes `images` is a list of URL strings, sometimes
    a list of dicts (`{link: "..."}` or `{image: "..."}`). Defensive.
    """
    raw = pd.get("images") or []
    if not isinstance(raw, list):
        return []
    urls = []
    for item in raw:
        if isinstance(item, str) and item:
            urls.append(item)
        elif isinstance(item, dict):
            url = item.get("link") or item.get("image") or item.get("url")
            if url:
                urls.append(url)
    return urls


def _extract_price(pd: dict) -> str | None:
    """Return a display-ready price string (e.g., '$24.99') or None.

    SerpApi sometimes returns `price` as a dict ({raw, value, currency}),
    sometimes as a plain string, sometimes via `prices[0].raw`.
    """
    price = pd.get("price")
    if isinstance(price, dict):
        return price.get("raw") or price.get("value")
    if isinstance(price, str) and price:
        return price
    prices = pd.get("prices")
    if isinstance(prices, list) and prices:
        first = prices[0]
        if isinstance(first, dict):
            return first.get("raw") or first.get("value")
    return None


def _extract_bestsellers_rank(pd: dict) -> list[dict]:
    """Return Amazon's Best Sellers Rank entries when present.

    SerpApi exposes this as `bestsellers_rank` — a list of
    {rank, category, link} dicts. Snapshot only (not min/avg over time).
    """
    raw = pd.get("bestsellers_rank") or []
    if not isinstance(raw, list):
        return []
    entries = []
    for r in raw:
        if not isinstance(r, dict):
            continue
        rank = r.get("rank")
        category = r.get("category") or r.get("name")
        if rank is None and not category:
            continue
        entries.append({"rank": rank, "category": category})
    return entries


def fetch_mock(asin: str) -> dict | None:
    """Look up the ASIN in mock data across all categories."""
    try:
        with MOCK_PATH.open() as f:
            mock = json.load(f)
    except Exception as e:
        print(f"WARN: mock data unreadable ({e})", file=sys.stderr)
        return None
    for items in mock.values():
        for item in items:
            if item.get("asin") == asin:
                out = dict(item)
                out["source"] = "mock"
                return out
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Amazon listing details")
    parser.add_argument("--asin", required=True, help="ASIN to fetch")
    parser.add_argument("--no-cache", action="store_true",
                        help="Skip cache lookup on SerpApi failure (still writes cache on success)")
    args = parser.parse_args()

    load_env()

    listing = fetch_serpapi(args.asin)
    if listing:
        save_cache(args.asin, listing)
    elif not args.no_cache:
        cached = load_cache(args.asin)
        if cached:
            print(f"INFO: serving cached SerpApi data for {args.asin}", file=sys.stderr)
            listing = cached

    if not listing:
        listing = fetch_mock(args.asin)

    if listing:
        output = {"status": "ok", **listing}
    else:
        output = {
            "status": "no_data",
            "asin": args.asin,
            "reason": "asin_not_in_mock_set",
            "source": None,
        }

    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
