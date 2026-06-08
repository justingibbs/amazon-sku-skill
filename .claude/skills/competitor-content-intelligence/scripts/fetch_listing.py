#!/usr/bin/env python3
"""Fetch a single Amazon product listing's title, bullets, and description.

Usage:
    python fetch_listing.py --asin B09XS7JWHH
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

MOCK_PATH = Path(__file__).resolve().parent.parent / "data" / "mock_competitors.json"
SERPAPI_ENDPOINT = "https://serpapi.com/search.json"


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


def fetch_serpapi(asin: str) -> dict | None:
    """Fetch full product details via SerpApi's amazon_product engine."""
    api_key = os.environ.get("SERPAPI_API_KEY")
    if not api_key:
        print("WARN: SERPAPI_API_KEY not set (checked environment and .env); "
              "falling back to mock data", file=sys.stderr)
        return None
    if requests is None:
        print("WARN: 'requests' not installed; falling back to mock data",
              file=sys.stderr)
        return None
    try:
        resp = requests.get(
            SERPAPI_ENDPOINT,
            params={
                "engine": "amazon_product",
                "asin": asin,
                "amazon_domain": "amazon.com",
                "api_key": api_key,
            },
            timeout=20,
        )
        resp.raise_for_status()
    except Exception as e:
        print(
            f"WARN: SerpApi product fetch failed ({_redact(str(e))}); falling back to mock",
            file=sys.stderr,
        )
        return None

    data = resp.json()
    pd = data.get("product_results") or {}
    return {
        "asin": asin,
        "title": pd.get("title"),
        "bullets": pd.get("feature_bullets") or pd.get("about_this_item") or [],
        "description": pd.get("description") or "",
        "brand": pd.get("brand"),
        "rating": pd.get("rating"),
        "reviews": pd.get("reviews"),
        "url": pd.get("link"),
        "source": "serpapi",
    }


def fetch_mock(asin: str) -> dict | None:
    """Look up the ASIN in mock data across all categories."""
    with MOCK_PATH.open() as f:
        mock = json.load(f)
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
    args = parser.parse_args()

    load_env()
    listing = fetch_serpapi(args.asin) or fetch_mock(args.asin)
    if not listing:
        print(f"ERROR: No data found for ASIN {args.asin}", file=sys.stderr)
        return 1
    print(json.dumps(listing, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
