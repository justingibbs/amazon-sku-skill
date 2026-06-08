#!/usr/bin/env python3
"""Load Ally SKUs from the catalog CSV.

Usage:
    python get_sku.py --list                  # list all SKUs (summary)
    python get_sku.py --sku-id ALY-AURA-PRO-001   # load one SKU as JSON
"""

import argparse
import csv
import json
import sys
from pathlib import Path


def find_csv() -> Path:
    """Walk up from this script to find data/ally_skus.csv."""
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        candidate = parent / "data" / "ally_skus.csv"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Could not locate data/ally_skus.csv from script location")


def parse_row(row: dict) -> dict:
    """Convert a raw CSV row into structured JSON."""
    return {
        "sku_id": row["sku_id"],
        "title": row["title"],
        "bullets": [b for b in row["bullets"].split("|") if b],
        "description": row["description"],
        "image_urls": [u for u in row["image_urls"].split("|") if u],
        "brand": row["brand"],
        "category": row["category"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Load Ally SKUs")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--sku-id", help="Load one SKU by ID")
    group.add_argument("--list", action="store_true", help="List all SKUs (summary)")
    args = parser.parse_args()

    csv_path = find_csv()
    with csv_path.open() as f:
        rows = [parse_row(r) for r in csv.DictReader(f)]

    if args.list:
        summary = [
            {"sku_id": r["sku_id"], "title": r["title"], "category": r["category"]}
            for r in rows
        ]
        print(json.dumps(summary, indent=2))
        return 0

    matches = [r for r in rows if r["sku_id"] == args.sku_id]
    if not matches:
        available = [r["sku_id"] for r in rows]
        print(
            f"ERROR: SKU '{args.sku_id}' not found. Available: {available}",
            file=sys.stderr,
        )
        return 1
    print(json.dumps(matches[0], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
