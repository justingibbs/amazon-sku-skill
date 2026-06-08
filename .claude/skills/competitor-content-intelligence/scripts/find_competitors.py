#!/usr/bin/env python3
"""Find competitor SKUs on Amazon via SerpApi, with mock fallback.

Usage:
    python find_competitors.py --query "wireless noise cancelling over-ear headphones" --limit 3
"""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

MOCK_PATH = Path(__file__).resolve().parent.parent / "data" / "mock_competitors.json"
SERPAPI_ENDPOINT = "https://serpapi.com/search.json"


def search_serpapi(query: str, limit: int) -> list[dict] | None:
    """Search via SerpApi. Returns None if no key, no requests, or HTTP error."""
    api_key = os.environ.get("SERPAPI_API_KEY")
    if not api_key or requests is None:
        return None
    try:
        resp = requests.get(
            SERPAPI_ENDPOINT,
            params={
                "engine": "amazon",
                "k": query,
                "amazon_domain": "amazon.com",
                "api_key": api_key,
            },
            timeout=20,
        )
        resp.raise_for_status()
    except Exception as e:
        print(f"WARN: SerpApi failed ({e}); falling back to mock data", file=sys.stderr)
        return None

    data = resp.json()
    organic = data.get("organic_results", []) or []
    results = []
    for item in organic[:limit]:
        price = item.get("price")
        if isinstance(price, dict):
            price = price.get("raw")
        results.append(
            {
                "asin": item.get("asin"),
                "title": item.get("title"),
                "url": item.get("link"),
                "brand": item.get("brand") or item.get("seller"),
                "rating": item.get("rating"),
                "reviews": item.get("reviews"),
                "price": price,
                "source": "serpapi",
            }
        )
    return results


def search_mock(query: str, limit: int) -> list[dict]:
    """Pick the closest matching category from mock data based on query keywords."""
    with MOCK_PATH.open() as f:
        mock = json.load(f)

    q_lower = query.lower()
    best_category = None
    best_score = -1
    for category in mock.keys():
        score = sum(1 for word in category.lower().split() if word in q_lower)
        if score > best_score:
            best_score = score
            best_category = category

    if not best_category:
        best_category = next(iter(mock.keys()))

    results = []
    for item in mock[best_category][:limit]:
        out = dict(item)
        out["source"] = "mock"
        results.append(out)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Find Amazon competitors")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--limit", type=int, default=3, help="Max results (default: 3)")
    args = parser.parse_args()

    results = search_serpapi(args.query, args.limit)
    if results is None or len(results) == 0:
        results = search_mock(args.query, args.limit)

    print(json.dumps({"query": args.query, "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
