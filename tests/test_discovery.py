from pathlib import Path
from unittest.mock import MagicMock

from crawler.discovery import (
    SitemapDiscoverer,
    extract_category_slug,
    extract_locs_from_xml,
    is_food_category,
)

MOCK_INDEX_XML = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <sitemap>
        <loc>https://www.bachhoaxanh.com/sitemapnew/sitemap-product-1001-1</loc>
    </sitemap>
    <sitemap>
        <loc>https://www.bachhoaxanh.com/sitemapnew/sitemap-product-1002-1</loc>
    </sitemap>
</sitemapindex>
"""

MOCK_FOOD_SUB_SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://www.bachhoaxanh.com/nuoc-mam/nuoc-mam-nam-ngu-500ml</loc>
    </url>
    <url>
        <loc>https://www.bachhoaxanh.com/nuoc-mam/nuoc-mam-thuan-phat-490ml</loc>
    </url>
    <url>
        <loc>https://www.bachhoaxanh.com/dau-an/dau-dau-nanh-orchid-1l</loc>
    </url>
</urlset>
"""

MOCK_NON_FOOD_SUB_SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://www.bachhoaxanh.com/bot-giat/bot-giat-omo-6kg</loc>
    </url>
    <url>
        <loc>https://www.bachhoaxanh.com/sua-tam/sua-tam-lifebuoy-850g</loc>
    </url>
</urlset>
"""


def test_extract_locs_from_xml():
    urls = extract_locs_from_xml(MOCK_INDEX_XML)
    assert len(urls) == 2
    assert urls[0] == "https://www.bachhoaxanh.com/sitemapnew/sitemap-product-1001-1"
    assert urls[1] == "https://www.bachhoaxanh.com/sitemapnew/sitemap-product-1002-1"


def test_extract_category_slug():
    assert (
        extract_category_slug(
            "https://www.bachhoaxanh.com/nuoc-mam/nuoc-mam-nam-ngu-500ml"
        )
        == "nuoc-mam"
    )
    assert (
        extract_category_slug(
            "https://www.bachhoaxanh.com/dau-an/dau-dau-nanh-orchid-1l"
        )
        == "dau-an"
    )
    assert extract_category_slug("https://www.bachhoaxanh.com/") == ""


def test_is_food_category():
    # Food categories
    assert is_food_category("nuoc-mam") is True
    assert is_food_category("dau-an") is True
    assert is_food_category("thit-heo") is True
    assert is_food_category("gao") is True

    # Non-food categories
    assert is_food_category("bot-giat") is False
    assert is_food_category("sua-tam") is False
    assert is_food_category("pin-tieu") is False
    assert is_food_category("chao-chong-dinh") is False
    assert is_food_category("") is False


def test_sitemap_discoverer_food_filtering():
    mock_client = MagicMock()

    def mock_fetch(url: str):
        if "sitemap-product" in url and "-1" not in url:
            return MOCK_INDEX_XML
        if "1001-1" in url:
            return MOCK_FOOD_SUB_SITEMAP
        if "1002-1" in url:
            return MOCK_NON_FOOD_SUB_SITEMAP
        return None

    mock_client.fetch_html.side_effect = mock_fetch

    discoverer = SitemapDiscoverer(
        http_client=mock_client,
        sitemap_index_url="https://www.bachhoaxanh.com/sitemapnew/sitemap-product",
    )

    # 1. Discover all food items (limit = 10)
    urls = discoverer.discover(limit=10, food_only=True)
    assert len(urls) == 3
    assert all("bot-giat" not in u and "sua-tam" not in u for u in urls)

    # 2. Discover with limit = 2
    urls_limited = discoverer.discover(limit=2, food_only=True)
    assert len(urls_limited) == 2

    # 3. Discover with category filter
    urls_nuoc_mam = discoverer.discover(limit=10, category_filter="nuoc-mam")
    assert len(urls_nuoc_mam) == 2
    assert all("nuoc-mam" in u for u in urls_nuoc_mam)


def test_save_urls_to_file(tmp_path: Path):
    target_file = tmp_path / "urls_test.txt"
    urls = [
        "https://www.bachhoaxanh.com/nuoc-mam/url-1",
        "https://www.bachhoaxanh.com/nuoc-mam/url-2",
    ]

    # First write
    SitemapDiscoverer.save_urls_to_file(urls, target_file)
    assert target_file.exists()
    lines = target_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2

    # Append new URLs
    more_urls = [
        "https://www.bachhoaxanh.com/nuoc-mam/url-2",  # Duplicate
        "https://www.bachhoaxanh.com/dau-an/url-3",
    ]
    SitemapDiscoverer.save_urls_to_file(more_urls, target_file, append=True)
    lines_after = target_file.read_text(encoding="utf-8").splitlines()
    assert len(lines_after) == 3
    assert lines_after[2] == "https://www.bachhoaxanh.com/dau-an/url-3"
