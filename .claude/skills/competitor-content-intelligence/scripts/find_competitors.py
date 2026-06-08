#!/usr/bin/env python3
"""Find competitor SKUs on Amazon via SerpApi, with mock fallback.

Usage:
    python find_competitors.py --query "wireless noise cancelling over-ear headphones" --limit 3
"""

import argparse
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

MOCK_PATH = Path(__file__).resolve().parent.parent / "data" / "mock_competitors.json"
SERPAPI_ENDPOINT = "https://serpapi.com/search.json"

SERPAPI_TIMEOUT_SECONDS = 45
RETRY_BACKOFF_SECONDS = [1, 3, 8]  # sleep before attempts 2, 3, 4 (max 4 attempts)


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


def search_serpapi(query: str, limit: int) -> list[dict] | None:
    """Search via SerpApi. Returns None if no key, no requests, or HTTP error."""
    api_key = os.environ.get("SERPAPI_API_KEY")
    if not api_key:
        print("WARN: SERPAPI_API_KEY not set (checked environment and .env); "
              "falling back to mock data", file=sys.stderr)
        return None
    if requests is None:
        print("WARN: 'requests' not installed; falling back to mock data",
              file=sys.stderr)
        return None
    max_attempts = len(RETRY_BACKOFF_SECONDS) + 1
    for attempt in range(1, max_attempts + 1):
        try:
            resp = requests.get(
                SERPAPI_ENDPOINT,
                params={
                    "engine": "amazon",
                    "k": query,
                    "amazon_domain": "amazon.com",
                    "api_key": api_key,
                },
                timeout=SERPAPI_TIMEOUT_SECONDS,
            )
            if 400 <= resp.status_code < 500:
                print(f"WARN: SerpApi returned {resp.status_code} (terminal); "
                      f"falling back to mock data", file=sys.stderr)
                return None
            resp.raise_for_status()
            data = resp.json()
            break
        except Exception as e:
            if attempt < max_attempts:
                sleep_for = RETRY_BACKOFF_SECONDS[attempt - 1]
                print(f"WARN: SerpApi search attempt {attempt}/{max_attempts} "
                      f"failed ({_redact(str(e))}); retrying in {sleep_for}s",
                      file=sys.stderr)
                time.sleep(sleep_for)
                continue
            print(f"WARN: SerpApi search failed after {max_attempts} attempts "
                  f"({_redact(str(e))}); falling back to mock data", file=sys.stderr)
            return None

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

    load_env()
    results = search_serpapi(args.query, args.limit)
    if results is None or len(results) == 0:
        results = search_mock(args.query, args.limit)

    print(json.dumps({"query": args.query, "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
