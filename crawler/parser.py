import json
import logging
import re
from typing import Any, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from config import DEFAULT_SOURCE
from crawler.models import Product

logger = logging.getLogger(__name__)

# Regex for extracting package unit / weight / volume from product name
# e.g., "chai 500ml", "800ml", "1kg", "500g", "hộp 1l", "lon 330ml"
UNIT_PATTERN = re.compile(
    r"\b(?:chai|lon|hộp|gói|bịch|hũ|túi|khay|vỉ|lốc|thùng)?\s*\d+(?:[\.,]\d+)?\s*(?:ml|lít|lit|l|kg|g|gam|kilogam)\b",
    re.IGNORECASE,
)


def extract_product_json_ld(soup: BeautifulSoup) -> Optional[dict[str, Any]]:
    """Extract Schema.org Product JSON-LD dictionary from the page soup."""
    for script in soup.find_all("script", type="application/ld+json"):
        raw_text = script.string or ""
        if not raw_text.strip():
            continue
        try:
            data = json.loads(raw_text)
            # Direct Product object
            if isinstance(data, dict):
                if data.get("@type") == "Product":
                    return data
                # Check inside @graph if present
                graph = data.get("@graph")
                if isinstance(graph, list):
                    for item in graph:
                        if isinstance(item, dict) and item.get("@type") == "Product":
                            return item
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get("@type") == "Product":
                        return item
        except (json.JSONDecodeError, ValueError) as err:
            logger.debug("Failed to decode JSON-LD script: %s", err)
            continue
    return None


def parse_product_name(
    soup: BeautifulSoup, json_ld: Optional[dict[str, Any]] = None
) -> Optional[str]:
    """Parse product name from JSON-LD, meta tags, or DOM headings."""
    # 1. From JSON-LD
    if json_ld and json_ld.get("name"):
        name = str(json_ld["name"]).strip()
        if name:
            return name

    # 2. From OpenGraph meta tag
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        content = og_title["content"].strip()
        # Avoid generic site titles
        if content and "Cửa hàng Bách hoá XANH" not in content:
            return content

    # 3. From <h1> heading
    h1 = soup.find("h1")
    if h1:
        text = h1.get_text(strip=True)
        if text and "Bách hoá XANH" not in text:
            return text

    # 4. From <title> tag
    title_tag = soup.find("title")
    if title_tag:
        title_text = title_tag.get_text(strip=True)
        if title_text and "Cửa hàng Bách hoá XANH" not in title_text:
            cleaned = re.sub(r"\s*-\s*Bách hoá XANH.*$", "", title_text).strip()
            if cleaned:
                return cleaned

    return None


def parse_brand(
    soup: BeautifulSoup, json_ld: Optional[dict[str, Any]] = None
) -> Optional[str]:
    """Parse brand name if explicitly available."""
    # 1. From JSON-LD
    if json_ld and json_ld.get("brand"):
        brand_val = json_ld["brand"]
        if isinstance(brand_val, dict):
            brand_name = brand_val.get("name")
            if brand_name:
                return str(brand_name).strip()
        elif isinstance(brand_val, str) and brand_val.strip():
            return brand_val.strip()

    # 2. From meta tag
    brand_meta = soup.find("meta", property="product:brand")
    if brand_meta and brand_meta.get("content"):
        val = brand_meta["content"].strip()
        if val:
            return val

    # 3. From DOM element (e.g. .brand, [data-brand])
    brand_el = soup.select_one(".product-brand, .brand, [data-brand]")
    if brand_el:
        val = brand_el.get_text(strip=True)
        if val:
            return val

    return None


def parse_category(
    soup: BeautifulSoup, json_ld: Optional[dict[str, Any]] = None
) -> Optional[str]:
    """Parse product category."""
    # 1. From JSON-LD
    if json_ld and json_ld.get("category"):
        cat_val = json_ld["category"]
        if isinstance(cat_val, str) and cat_val.strip():
            return cat_val.strip()

    # 2. From meta tag
    cat_meta = soup.find("meta", property="product:category")
    if cat_meta and cat_meta.get("content"):
        val = cat_meta["content"].strip()
        if val:
            return val

    # 3. From DOM breadcrumb
    breadcrumbs = soup.select("nav ol li, .breadcrumb li, [aria-label='breadcrumb'] li")
    if breadcrumbs:
        # Category is usually the parent before the current product title
        texts = [b.get_text(strip=True) for b in breadcrumbs if b.get_text(strip=True)]
        if len(texts) >= 2:
            return texts[-2]

    return None


def parse_price(
    soup: BeautifulSoup, json_ld: Optional[dict[str, Any]] = None
) -> Optional[int]:
    """Parse price into integer VND (e.g. '71.000₫' -> 71000)."""

    def clean_price_value(raw: Any) -> Optional[int]:
        if raw is None:
            return None
        if isinstance(raw, (int, float)):
            return int(raw)
        # Extract digits from string (handling Vietnamese dot separators)
        cleaned = re.sub(r"[^\d]", "", str(raw))
        if cleaned:
            try:
                return int(cleaned)
            except ValueError:
                return None
        return None

    # 1. From JSON-LD offers
    if json_ld and json_ld.get("offers"):
        offers = json_ld["offers"]
        if isinstance(offers, dict):
            price_raw = offers.get("price") or offers.get("lowPrice")
            val = clean_price_value(price_raw)
            if val is not None:
                return val
        elif isinstance(offers, list) and offers:
            val = clean_price_value(offers[0].get("price"))
            if val is not None:
                return val

    # 2. From meta tag
    price_meta = soup.find("meta", property="product:price:amount")
    if price_meta and price_meta.get("content"):
        val = clean_price_value(price_meta["content"])
        if val is not None:
            return val

    # 3. From DOM element
    price_el = soup.select_one(".product-price, .price, .current-price, [data-price]")
    if price_el:
        val = clean_price_value(price_el.get_text(strip=True))
        if val is not None:
            return val

    return None


def parse_unit(
    soup: BeautifulSoup,
    json_ld: Optional[dict[str, Any]] = None,
    name: Optional[str] = None,
) -> Optional[str]:
    """Parse unit / weight / volume from DOM, JSON-LD, or product name regex."""
    # 1. From DOM element
    unit_el = soup.select_one(".product-unit, .unit, [data-unit]")
    if unit_el:
        val = unit_el.get_text(strip=True)
        if val:
            return val

    # 2. From product name pattern
    if name:
        match = UNIT_PATTERN.search(name)
        if match:
            return match.group(0).strip()

    return None


def parse_image_urls(
    soup: BeautifulSoup,
    json_ld: Optional[dict[str, Any]] = None,
    base_url: str = "",
) -> list[str]:
    """Parse product image URLs from JSON-LD and og:image, deduplicated in page order."""
    candidates: list[str] = []

    def collect(value: Any) -> None:
        if isinstance(value, str):
            candidates.append(value)
        elif isinstance(value, dict):
            # Schema.org ImageObject
            collect(value.get("url") or value.get("contentUrl"))
        elif isinstance(value, list):
            for item in value:
                collect(item)

    # 1. From JSON-LD (string, list, or ImageObject)
    if json_ld:
        collect(json_ld.get("image"))

    # 2. From OpenGraph meta tags
    for og_image in soup.find_all("meta", property="og:image"):
        collect(og_image.get("content"))

    image_urls: list[str] = []
    for raw in candidates:
        raw = raw.strip()
        if not raw or raw.startswith("data:"):
            continue
        absolute = urljoin(base_url, raw)
        if absolute not in image_urls:
            image_urls.append(absolute)
    return image_urls


def parse_product_page(html: str, url: str) -> Optional[Product]:
    """Parse an HTML document into a Product model."""
    soup = BeautifulSoup(html, "html.parser")
    json_ld = extract_product_json_ld(soup)

    name = parse_product_name(soup, json_ld)
    if not name:
        logger.warning("Could not extract a valid product name from URL: %s", url)
        return None

    brand = parse_brand(soup, json_ld)
    category = parse_category(soup, json_ld)
    price = parse_price(soup, json_ld)
    unit = parse_unit(soup, json_ld, name=name)

    # Use canonical product url from json-ld if available, else provided url
    product_url = url
    if json_ld and json_ld.get("url"):
        product_url = str(json_ld["url"])

    image_urls = parse_image_urls(soup, json_ld, base_url=product_url)

    return Product(
        name=name,
        brand=brand,
        category=category,
        price=price,
        unit=unit,
        product_url=product_url,
        image_url=image_urls[0] if image_urls else None,
        image_urls=image_urls,
        source=DEFAULT_SOURCE,
    )
