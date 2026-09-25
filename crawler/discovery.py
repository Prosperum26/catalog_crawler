import logging
import re
from pathlib import Path
from typing import Optional, Sequence
from urllib.parse import urlparse

from config import SITEMAP_INDEX_URL
from crawler.http_client import HttpClient

logger = logging.getLogger(__name__)

# Categories of non-food items commonly sold at Bach Hoa Xanh
NON_FOOD_CATEGORIES = {
    "ban-chai-danh-rang",
    "bang-ve-sinh",
    "binh-dun-sieu-toc",
    "bo-noi",
    "bot-giat",
    "cham-soc-ca-nhan",
    "chao-chong-dinh",
    "dao-cao-rau",
    "dau-goi",
    "dau-xa",
    "do-dung-gia-dinh",
    "dung-cu-nha-bep",
    "giay-ve-sinh",
    "kem-chong-nang",
    "kem-danh-rang",
    "khan-giay",
    "lau-dien",
    "noi-com-dien",
    "nuoc-giat",
    "nuoc-rua-chen",
    "nuoc-tay-rua",
    "nuoc-xa",
    "nuoc-xit-phong",
    "pin-tieu",
    "sap-thom",
    "sua-rua-mat",
    "sua-tam",
    "ta-bim",
    "tui-rac",
    "ve-sinh-nha-cua",
    "ve-sinh-toilet",
    "ve-sinh-mieng",
}


def extract_locs_from_xml(xml_content: str) -> list[str]:
    """Extract all URL strings within <loc> tags in an XML sitemap."""
    pattern = re.compile(r"<loc>\s*(https?://[^\s<]+)\s*</loc>", re.IGNORECASE)
    return pattern.findall(xml_content)


def extract_category_slug(product_url: str) -> str:
    """Extract category slug from a Bach Hoa Xanh URL path."""
    parsed = urlparse(product_url)
    segments = [s for s in parsed.path.strip("/").split("/") if s]
    if segments:
        return segments[0].lower()
    return ""


def is_food_category(category_slug: str) -> bool:
    """Check if a category slug represents food rather than non-food household goods."""
    slug = category_slug.lower().strip()
    if not slug:
        return False
    return slug not in NON_FOOD_CATEGORIES


class SitemapDiscoverer:
    """Discovers product URLs automatically from Bach Hoa Xanh XML sitemaps."""

    def __init__(
        self,
        http_client: Optional[HttpClient] = None,
        sitemap_index_url: str = SITEMAP_INDEX_URL,
    ) -> None:
        self.http_client = http_client or HttpClient()
        self.sitemap_index_url = sitemap_index_url

    def discover(
        self,
        limit: Optional[int] = 50,
        category_filter: Optional[str] = None,
        food_only: bool = True,
        max_sub_sitemaps: Optional[int] = None,
    ) -> list[str]:
        """
        Discover product URLs from the sitemap hierarchy.

        Args:
            limit: Maximum number of product URLs to collect. Use None to
                collect all matching URLs.
            category_filter: Optional slug to filter by specific category (e.g. 'nuoc-mam').
            food_only: If True, exclude household/non-food categories.
            max_sub_sitemaps: Optional limit on number of sub-sitemaps to traverse.

        Returns:
            List of unique product URLs.
        """
        logger.info("Fetching sitemap index from: %s", self.sitemap_index_url)
        index_xml = self.http_client.fetch_html(self.sitemap_index_url)
        if not index_xml:
            logger.error("Failed to retrieve sitemap index XML.")
            return []

        sub_sitemaps = extract_locs_from_xml(index_xml)
        logger.info("Found %d sub-sitemaps in index.", len(sub_sitemaps))

        if max_sub_sitemaps:
            sub_sitemaps = sub_sitemaps[:max_sub_sitemaps]

        discovered_urls: list[str] = []
        seen_urls: set[str] = set()

        for idx, sub_url in enumerate(sub_sitemaps, start=1):
            if limit is not None and len(discovered_urls) >= limit:
                break

            logger.info(
                "Scanning sub-sitemap [%d/%d]: %s",
                idx,
                len(sub_sitemaps),
                sub_url,
            )
            sub_xml = self.http_client.fetch_html(sub_url)
            if not sub_xml:
                logger.warning("Could not fetch sub-sitemap: %s", sub_url)
                continue

            product_urls = extract_locs_from_xml(sub_xml)
            for prod_url in product_urls:
                if prod_url in seen_urls:
                    continue

                category = extract_category_slug(prod_url)

                # Filter by specific category if requested
                if category_filter and category != category_filter.lower().strip():
                    continue

                # Filter food only if enabled
                if food_only and not is_food_category(category):
                    continue

                seen_urls.add(prod_url)
                discovered_urls.append(prod_url)

                if limit is not None and len(discovered_urls) >= limit:
                    break

        logger.info(
            "Discovery finished. Collected %d product URLs (limit was %s).",
            len(discovered_urls),
            limit if limit is not None else "unlimited",
        )
        return discovered_urls

    @staticmethod
    def save_urls_to_file(
        urls: Sequence[str], file_path: Path, append: bool = False
    ) -> None:
        """Write product URLs to a text file (one URL per line)."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"

        existing_urls: set[str] = set()
        if append and file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                existing_urls = {line.strip() for line in f if line.strip()}

        with open(file_path, mode, encoding="utf-8") as f:
            for url in urls:
                clean_url = url.strip()
                if clean_url and clean_url not in existing_urls:
                    f.write(f"{clean_url}\n")
                    existing_urls.add(clean_url)

        logger.info("Saved %d URL(s) to: %s", len(urls), file_path)
