import csv
import json

from crawler.models import Product
from crawler.storage import save_products_to_csv, save_products_to_json


def make_product():
    return Product(
        name="Nước mắm",
        product_url="https://www.bachhoaxanh.com/nuoc-mam/x",
        image_url="https://cdn.example.com/a.jpg",
        image_urls=["https://cdn.example.com/a.jpg", "https://cdn.example.com/b.jpg"],
        image_paths=["data/images/x.jpg"],
    )


def test_json_keeps_image_lists(tmp_path):
    out = tmp_path / "products.json"
    save_products_to_json([make_product()], out)
    item = json.loads(out.read_text(encoding="utf-8"))[0]
    assert item["image_url"] == "https://cdn.example.com/a.jpg"
    assert item["image_urls"] == ["https://cdn.example.com/a.jpg", "https://cdn.example.com/b.jpg"]
    assert item["image_paths"] == ["data/images/x.jpg"]


def test_csv_flattens_image_lists(tmp_path):
    out = tmp_path / "products.csv"
    save_products_to_csv([make_product()], out)
    with open(out, encoding="utf-8-sig") as f:
        row = next(csv.DictReader(f))
    assert row["image_url"] == "https://cdn.example.com/a.jpg"
    assert row["image_urls"] == "https://cdn.example.com/a.jpg | https://cdn.example.com/b.jpg"
    assert row["image_paths"] == "data/images/x.jpg"
