import argparse
import hashlib
import logging
import sys
from pathlib import Path
from urllib.parse import urlparse

from config import (
    DEFAULT_DELAY,
    DEFAULT_DISCOVERY_LIMIT,
    DEFAULT_TIMEOUT,
    DEFAULT_URLS_OUTPUT_PATH,
    OUTPUT_CSV_PATH,
    OUTPUT_JSON_PATH,
    RAW_DATA_DIR,
)
from crawler.discovery import SitemapDiscoverer
from crawler.http_client import HttpClient
from crawler.models import Product
from crawler.parser import parse_product_page
from crawler.storage import save_products_to_csv, save_products_to_json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def generate_filename_from_url(url: str) -> str:
    """Create a safe filename from a product URL for raw HTML storage."""
    path = urlparse(url).path.strip("/").replace("/", "_")
    if not path:
        path = hashlib.md5(url.encode("utf-8")).hexdigest()[:12]
    return f"{path}.html"


def load_urls_from_file(file_path: Path) -> list[str]:
    """Read a list of product URLs from a text file, ignoring empty lines and comments."""
    if not file_path.exists():
        logger.error("URLs file not found: %s", file_path)
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        urls = [
            line.strip()
            for line in f
            if line.strip() and not line.strip().startswith("#")
        ]
    return urls


def crawl_urls(
    urls: list[str],
    delay: float = DEFAULT_DELAY,
    save_raw: bool = False,
    merge_existing: bool = True,
) -> list[Product]:
    """Crawl and parse product details from a list of URLs."""
    client = HttpClient(delay=delay, timeout=DEFAULT_TIMEOUT)
    successful_products: list[Product] = []

    total = len(urls)
    logger.info("Starting crawl of %d product URL(s)...", total)

    for index, url in enumerate(urls, start=1):
        logger.info("[%d/%d] Processing: %s", index, total, url)
        html = client.fetch_html(url)
        if not html:
            logger.warning("[%d/%d] Failed to retrieve HTML for %s", index, total, url)
            continue

        if save_raw:
            RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
            raw_file = RAW_DATA_DIR / generate_filename_from_url(url)
            with open(raw_file, "w", encoding="utf-8") as rf:
                rf.write(html)
            logger.debug("Saved raw HTML to %s", raw_file)

        product = parse_product_page(html, url)
        if product:
            successful_products.append(product)
            logger.info(
                "Parsed: '%s' | Category: %s | Price: %s VND | Unit: %s",
                product.name,
                product.category or "N/A",
                f"{product.price:,}" if product.price is not None else "N/A",
                product.unit or "N/A",
            )
        else:
            logger.warning(
                "[%d/%d] Could not extract product information from %s (page might be client-rendered or out of stock)",
                index,
                total,
                url,
            )

    if successful_products:
        save_products_to_json(
            successful_products, OUTPUT_JSON_PATH, merge_existing=merge_existing
        )
        save_products_to_csv(
            successful_products, OUTPUT_CSV_PATH, merge_existing=merge_existing
        )

    logger.info(
        "Crawl completed. Extracted %d/%d product(s).", len(successful_products), total
    )
    return successful_products


def handle_discovery(args: argparse.Namespace) -> list[str]:
    """Execute automated URL discovery from sitemaps."""
    client = HttpClient(delay=args.delay, timeout=DEFAULT_TIMEOUT)
    discoverer = SitemapDiscoverer(http_client=client)

    logger.info(
        "Starting automated URL discovery (limit=%s, category=%s, food_only=%s)...",
        args.limit if not args.all_urls else "unlimited",
        args.category or "all",
        not args.all_categories,
    )
    discovered_urls = discoverer.discover(
        limit=None if args.all_urls else args.limit,
        category_filter=args.category,
        food_only=not args.all_categories,
    )

    output_path = Path(args.output_urls)
    discoverer.save_urls_to_file(discovered_urls, output_path)
    logger.info("Saved %d discovered URL(s) to %s", len(discovered_urls), output_path)
    return discovered_urls


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bach Hoa Xanh Product Catalog Crawler & Discovery"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", type=str, help="Single public product page URL to crawl")
    group.add_argument(
        "--urls", type=str, help="Path to text file containing list of product URLs"
    )
    group.add_argument(
        "--discover",
        action="store_true",
        help="Automatically discover product URLs from sitemaps",
    )

    # General / Crawl settings
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY,
        help=f"Polite delay between requests in seconds (default: {DEFAULT_DELAY})",
    )
    parser.add_argument(
        "--save-raw",
        action="store_true",
        help="Save raw HTML files to data/raw/ directory",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite output files instead of merging with existing data",
    )

    # Discovery-specific settings
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_DISCOVERY_LIMIT,
        help=f"Maximum URLs to discover (default: {DEFAULT_DISCOVERY_LIMIT})",
    )
    parser.add_argument(
        "--all-urls",
        action="store_true",
        help="Discover all matching product URLs from every sitemap",
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="Filter discovery by category slug (e.g. 'nuoc-mam', 'dau-an', 'sua-tuoi')",
    )
    parser.add_argument(
        "--output-urls",
        type=str,
        default=str(DEFAULT_URLS_OUTPUT_PATH),
        help=f"File path to save discovered URLs (default: {DEFAULT_URLS_OUTPUT_PATH})",
    )
    parser.add_argument(
        "--crawl",
        action="store_true",
        help="If used with --discover, immediately crawl products after discovery",
    )
    parser.add_argument(
        "--all-categories",
        action="store_true",
        help="Include non-food categories during discovery (default is food only)",
    )

    args = parser.parse_args()

    # 1. Discovery mode
    if args.discover:
        discovered = handle_discovery(args)
        if args.crawl and discovered:
            logger.info("Proceeding to crawl %d discovered URLs...", len(discovered))
            crawl_urls(
                urls=discovered,
                delay=args.delay,
                save_raw=args.save_raw,
                merge_existing=not args.overwrite,
            )
        return

    # 2. Direct crawling mode
    urls_to_crawl: list[str] = []
    if args.url:
        urls_to_crawl = [args.url.strip()]
    elif args.urls:
        urls_to_crawl = load_urls_from_file(Path(args.urls))

    if not urls_to_crawl:
        logger.error("No valid URLs to crawl. Exiting.")
        sys.exit(1)

    crawl_urls(
        urls=urls_to_crawl,
        delay=args.delay,
        save_raw=args.save_raw,
        merge_existing=not args.overwrite,
    )


if __name__ == "__main__":
    main()
