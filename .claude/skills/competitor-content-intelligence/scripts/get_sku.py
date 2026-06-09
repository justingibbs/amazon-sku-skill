#!/usr/bin/env python3
"""Load BPN SKUs from the catalog CSV.

The CSV schema mirrors the CommerceIQ asin_data_filled export so this script
also works against any subset of that file (not just BPN).

Usage:
    python get_sku.py --list                    # list all SKUs (summary)
    python get_sku.py --sku-id B0DGHN493N       # load one SKU as JSON
    python get_sku.py --list --csv /path.csv    # point at a different CSV
"""

import argparse
import csv
import json
import sys
from pathlib import Path

DEFAULT_CSV_NAME = "bpn_skus.csv"


def find_csv(explicit: str | None = None) -> Path:
    """Locate the catalog CSV.

    If --csv is given, use it. Otherwise walk up from this script to find
    data/bpn_skus.csv.
    """
    if explicit:
        p = Path(explicit).expanduser().resolve()
        if not p.exists():
            raise FileNotFoundError(f"CSV not found: {p}")
        return p
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        candidate = parent / "data" / DEFAULT_CSV_NAME
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"Could not locate data/{DEFAULT_CSV_NAME} from script location"
    )


def _parse_json_array(raw: str, field: str, sku_id: str) -> list:
    """Parse a JSON-array CSV cell. Empty/whitespace cells become []."""
    raw = (raw or "").strip()
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as e:
        print(
            f"WARN: {field} for {sku_id} is not valid JSON ({e}); treating as empty",
            file=sys.stderr,
        )
        return []
    if not isinstance(value, list):
        print(
            f"WARN: {field} for {sku_id} parsed to {type(value).__name__}, not list; "
            f"treating as empty",
            file=sys.stderr,
        )
        return []
    return value


def _parse_int(raw: str) -> int | None:
    """Parse an integer cell. Empty/blank cells become None."""
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        try:
            return int(float(raw))
        except ValueError:
            return None


def parse_row(row: dict) -> dict:
    """Convert a raw CSV row into a structured record.

    Field names match the downstream prompt's expectations. The legacy
    field names (sku_id, bullets, description, image_urls, brand, category)
    are aliased so SKILL.md and earlier prompts continue to work.
    """
    sku_id = row["product_id"]
    bullets = _parse_json_array(row.get("bullet_points", ""), "bullet_points", sku_id)
    image_urls = _parse_json_array(row.get("image_url", ""), "image_url", sku_id)
    description = (row.get("description_filled") or "").strip()
    title = row.get("title", "")
    brand = (row.get("retailer_brand_name") or "").strip()
    category_node = (row.get("retailer_category_node") or "").strip()
    universe = (row.get("universe") or "").strip()

    return {
        "sku_id": sku_id,
        "product_id": sku_id,
        "title": title,
        "bullets": bullets,
        "description": description,
        "image_urls": image_urls,
        "brand": brand,
        "category": category_node or universe,
        "category_node": category_node,
        "universe": universe,
        "ranks": {
            "min_rank_search": _parse_int(row.get("min_rank_search", "")),
            "avg_rank_search": _parse_int(row.get("avg_rank_search", "")),
            "min_rank_category": _parse_int(row.get("min_rank_category", "")),
            "avg_rank_category": _parse_int(row.get("avg_rank_category", "")),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Load BPN SKUs")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--sku-id", help="Load one SKU by product_id")
    group.add_argument("--list", action="store_true", help="List all SKUs (summary)")
    parser.add_argument(
        "--csv",
        help=f"Path to an alternate CSV (defaults to data/{DEFAULT_CSV_NAME})",
    )
    args = parser.parse_args()

    csv_path = find_csv(args.csv)
    with csv_path.open() as f:
        rows = [parse_row(r) for r in csv.DictReader(f)]

    if args.list:
        summary = [
            {
                "sku_id": r["sku_id"],
                "title": r["title"],
                "category": r["category"],
                "universe": r["universe"],
                "avg_rank_category": r["ranks"]["avg_rank_category"],
                "avg_rank_search": r["ranks"]["avg_rank_search"],
            }
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
