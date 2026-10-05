from unittest.mock import MagicMock

from crawler.images import (
    download_product_images,
    guess_image_extension,
    image_stem_for_product,
)
from crawler.models import Product

PRODUCT_URL = "https://www.bachhoaxanh.com/nuoc-mam/nuoc-mam-nam-ngu-500ml"


def make_product(image_urls):
    return Product(
        name="Nước mắm",
        product_url=PRODUCT_URL,
        image_url=image_urls[0] if image_urls else None,
        image_urls=image_urls,
    )


def test_guess_image_extension():
    assert guess_image_extension("https://cdn.example.com/a/b.PNG") == ".png"
    assert guess_image_extension("https://cdn.example.com/a/b.jpg?w=300") == ".jpg"
    assert guess_image_extension("https://cdn.example.com/img", "image/webp") == ".webp"
    assert guess_image_extension("https://cdn.example.com/img", "image/jpeg") == ".jpg"
    assert guess_image_extension("https://cdn.example.com/img", "") == ".jpg"


def test_image_stem_for_product():
    assert image_stem_for_product(PRODUCT_URL) == "nuoc-mam_nuoc-mam-nam-ngu-500ml"


def test_download_product_images_saves_files(tmp_path):
    client = MagicMock()
    client.fetch_bytes.side_effect = [(b"img-1", "image/jpeg"), (b"img-2", "image/png")]
    product = make_product(["https://cdn.example.com/1.jpg", "https://cdn.example.com/2"])

    paths = download_product_images(product, client, tmp_path / "images", relative_to=tmp_path)

    assert paths == [
        "images/nuoc-mam_nuoc-mam-nam-ngu-500ml.jpg",
        "images/nuoc-mam_nuoc-mam-nam-ngu-500ml_1.png",
    ]
    assert product.image_paths == paths
    assert (tmp_path / paths[0]).read_bytes() == b"img-1"
    assert (tmp_path / paths[1]).read_bytes() == b"img-2"


def test_download_product_images_skips_existing(tmp_path):
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    existing = images_dir / "nuoc-mam_nuoc-mam-nam-ngu-500ml.jpg"
    existing.write_bytes(b"old")
    client = MagicMock()
    product = make_product(["https://cdn.example.com/1.jpg"])

    paths = download_product_images(product, client, images_dir, relative_to=tmp_path)

    client.fetch_bytes.assert_not_called()
    assert paths == ["images/nuoc-mam_nuoc-mam-nam-ngu-500ml.jpg"]
    assert existing.read_bytes() == b"old"


def test_download_product_images_skips_failures(tmp_path):
    client = MagicMock()
    client.fetch_bytes.return_value = None
    product = make_product(["https://cdn.example.com/1.jpg"])

    assert download_product_images(product, client, tmp_path) == []
    assert list(tmp_path.iterdir()) == []
