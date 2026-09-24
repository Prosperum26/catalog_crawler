import json
import pytest
from bs4 import BeautifulSoup

from crawler.parser import (
    extract_product_json_ld,
    parse_brand,
    parse_category,
    parse_price,
    parse_product_name,
    parse_product_page,
    parse_unit,
)

# Realistic fixture resembling Bach Hoa Xanh production HTML with Schema.org JSON-LD
MOCK_HTML_BHX_JSON_LD = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="utf-8">
    <title>Nước mắm Nam Ngư Phú Quốc đậm đặc 32 độ đạm chai 500ml</title>
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "Product",
      "name": "Nước mắm Nam Ngư Phú Quốc đậm đặc 32 độ đạm chai 500ml",
      "url": "https://www.bachhoaxanh.com/nuoc-mam/nuoc-mam-nam-ngu-phu-quoc-dam-dac-32-do-dam-chai-500ml",
      "category": "Nước mắm",
      "brand": {
        "@type": "Brand",
        "name": "Nam Ngư"
      },
      "offers": {
        "@type": "AggregateOffer",
        "price": "71.000₫",
        "priceCurrency": "VND"
      }
    }
    </script>
</head>
<body>
    <div>Client side rendered shell</div>
</body>
</html>
"""

# Fixture using traditional semantic HTML / DOM tags & meta tags
MOCK_HTML_DOM = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="utf-8">
    <meta property="og:title" content="Dầu đậu nành Simply nguyên chất chai 1 lít">
    <meta property="product:brand" content="Simply">
    <meta property="product:category" content="Dầu ăn">
    <meta property="product:price:amount" content="65000">
</head>
<body>
    <nav>
        <ol class="breadcrumb">
            <li><a href="/">Trang chủ</a></li>
            <li><a href="/dau-an">Dầu ăn</a></li>
            <li>Dầu đậu nành Simply chai 1 lít</li>
        </ol>
    </nav>
    <h1 class="product-name">Dầu đậu nành Simply nguyên chất chai 1 lít</h1>
    <div class="brand">Simply</div>
    <div class="price">65.000 đ</div>
    <div class="unit">chai 1 lít</div>
</body>
</html>
"""

# Fixture with minimal/missing info (no price, no brand)
MOCK_HTML_MINIMAL = """
<!DOCTYPE html>
<html>
<head>
    <title>Rau muống sạch 500g</title>
    <meta property="og:title" content="Rau muống sạch 500g">
</head>
<body>
    <h1>Rau muống sạch 500g</h1>
</body>
</html>
"""


def test_extract_json_ld():
    soup = BeautifulSoup(MOCK_HTML_BHX_JSON_LD, "html.parser")
    json_ld = extract_product_json_ld(soup)
    assert json_ld is not None
    assert json_ld["@type"] == "Product"
    assert "Nam Ngư" in json_ld["name"]


def test_parse_product_name():
    # From JSON-LD
    soup_ld = BeautifulSoup(MOCK_HTML_BHX_JSON_LD, "html.parser")
    json_ld = extract_product_json_ld(soup_ld)
    assert parse_product_name(soup_ld, json_ld) == "Nước mắm Nam Ngư Phú Quốc đậm đặc 32 độ đạm chai 500ml"

    # From DOM
    soup_dom = BeautifulSoup(MOCK_HTML_DOM, "html.parser")
    assert parse_product_name(soup_dom, None) == "Dầu đậu nành Simply nguyên chất chai 1 lít"


def test_parse_brand():
    # With JSON-LD brand object
    soup_ld = BeautifulSoup(MOCK_HTML_BHX_JSON_LD, "html.parser")
    json_ld = extract_product_json_ld(soup_ld)
    assert parse_brand(soup_ld, json_ld) == "Nam Ngư"

    # With DOM / meta tag
    soup_dom = BeautifulSoup(MOCK_HTML_DOM, "html.parser")
    assert parse_brand(soup_dom, None) == "Simply"

    # When brand does not exist -> must be None (no guessing)
    soup_min = BeautifulSoup(MOCK_HTML_MINIMAL, "html.parser")
    assert parse_brand(soup_min, None) is None


def test_parse_category():
    # From JSON-LD
    soup_ld = BeautifulSoup(MOCK_HTML_BHX_JSON_LD, "html.parser")
    json_ld = extract_product_json_ld(soup_ld)
    assert parse_category(soup_ld, json_ld) == "Nước mắm"

    # From DOM / meta
    soup_dom = BeautifulSoup(MOCK_HTML_DOM, "html.parser")
    assert parse_category(soup_dom, None) == "Dầu ăn"

    # When missing
    soup_min = BeautifulSoup(MOCK_HTML_MINIMAL, "html.parser")
    assert parse_category(soup_min, None) is None


def test_parse_price():
    # Clean Vietnamese price with dot separator and currency sign
    soup_ld = BeautifulSoup(MOCK_HTML_BHX_JSON_LD, "html.parser")
    json_ld = extract_product_json_ld(soup_ld)
    assert parse_price(soup_ld, json_ld) == 71000

    # From DOM
    soup_dom = BeautifulSoup(MOCK_HTML_DOM, "html.parser")
    assert parse_price(soup_dom, None) == 65000

    # When missing
    soup_min = BeautifulSoup(MOCK_HTML_MINIMAL, "html.parser")
    assert parse_price(soup_min, None) is None


def test_parse_unit():
    # Extracted from title pattern (chai 500ml)
    soup_ld = BeautifulSoup(MOCK_HTML_BHX_JSON_LD, "html.parser")
    name = "Nước mắm Nam Ngư Phú Quốc đậm đặc 32 độ đạm chai 500ml"
    assert parse_unit(soup_ld, None, name=name) == "chai 500ml"

    # Extracted from DOM .unit
    soup_dom = BeautifulSoup(MOCK_HTML_DOM, "html.parser")
    assert parse_unit(soup_dom, None, name=None) == "chai 1 lít"

    # Extracted from title (500g)
    soup_min = BeautifulSoup(MOCK_HTML_MINIMAL, "html.parser")
    assert parse_unit(soup_min, None, name="Rau muống sạch 500g") == "500g"

    # Unknown unit
    assert parse_unit(soup_min, None, name="Sản phẩm thử nghiệm") is None


def test_parse_product_page_full():
    url = "https://www.bachhoaxanh.com/nuoc-mam/nuoc-mam-nam-ngu-phu-quoc-dam-dac-32-do-dam-chai-500ml"
    product = parse_product_page(MOCK_HTML_BHX_JSON_LD, url)
    assert product is not None
    assert product.name == "Nước mắm Nam Ngư Phú Quốc đậm đặc 32 độ đạm chai 500ml"
    assert product.brand == "Nam Ngư"
    assert product.category == "Nước mắm"
    assert product.price == 71000
    assert product.unit == "chai 500ml"
    assert product.source == "bachhoaxanh"
    assert product.product_url == url
    assert product.crawled_at != ""


def test_parse_product_page_minimal_no_guessing():
    url = "https://www.bachhoaxanh.com/rau/rau-muong-500g"
    product = parse_product_page(MOCK_HTML_MINIMAL, url)
    assert product is not None
    assert product.name == "Rau muống sạch 500g"
    assert product.brand is None
    assert product.category is None
    assert product.price is None
    assert product.unit == "500g"
    assert product.source == "bachhoaxanh"
