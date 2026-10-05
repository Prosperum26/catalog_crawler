import csv
import json
import logging
from pathlib import Path
from typing import Sequence

from crawler.models import Product

logger = logging.getLogger(__name__)

# Separator used to flatten list fields (e.g. image_urls) into a single CSV cell
CSV_LIST_SEPARATOR = " | "

CSV_FIELDNAMES = [
    "name",
    "brand",
    "category",
    "price",
    "unit",
    "product_url",
    "image_url",
    "image_urls",
    "image_paths",
    "source",
    "crawled_at",
]


def save_products_to_json(
    products: Sequence[Product],
    output_path: Path,
    merge_existing: bool = True,
) -> None:
    """Save products to a JSON file, optionally merging with existing entries."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    items_by_url: dict[str, dict] = {}

    if merge_existing and output_path.exists():
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                if isinstance(existing_data, list):
                    for item in existing_data:
                        if isinstance(item, dict) and "product_url" in item:
                            items_by_url[item["product_url"]] = item
        except Exception as e:
            logger.warning("Could not read existing JSON file %s: %s", output_path, e)

    for prod in products:
        items_by_url[prod.product_url] = prod.to_dict()

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(list(items_by_url.values()), f, ensure_ascii=False, indent=2)

    logger.info("Saved %d products to JSON: %s", len(items_by_url), output_path)


def _to_csv_row(product: Product) -> dict:
    """Flatten list fields so they fit in a single CSV cell."""
    row = product.to_dict()
    for key, value in row.items():
        if isinstance(value, list):
            row[key] = CSV_LIST_SEPARATOR.join(str(v) for v in value)
    return row


def save_products_to_csv(
    products: Sequence[Product],
    output_path: Path,
    merge_existing: bool = True,
) -> None:
    """
    Save products to a CSV file using utf-8-sig encoding for seamless Excel/DataGrip compatibility.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    items_by_url: dict[str, dict] = {}

    if merge_existing and output_path.exists():
        try:
            with open(output_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("product_url"):
                        items_by_url[row["product_url"]] = row
        except Exception as e:
            logger.warning("Could not read existing CSV file %s: %s", output_path, e)

    for prod in products:
        items_by_url[prod.product_url] = _to_csv_row(prod)

    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        for item in items_by_url.values():
            writer.writerow(item)

    logger.info("Saved %d products to CSV: %s", len(items_by_url), output_path)
