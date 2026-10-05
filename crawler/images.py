import logging
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

from crawler.http_client import HttpClient
from crawler.models import Product

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}
DEFAULT_IMAGE_EXTENSION = ".jpg"
# Explicit map: the stdlib mimetypes table is platform dependent (e.g. no webp on some Windows setups)
CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/avif": ".avif",
}


def guess_image_extension(image_url: str, content_type: str = "") -> str:
    """Pick a file extension from the image URL path, falling back to Content-Type."""
    suffix = PurePosixPath(urlparse(image_url).path).suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return suffix
    mime = content_type.split(";")[0].strip().lower()
    return CONTENT_TYPE_EXTENSIONS.get(mime, DEFAULT_IMAGE_EXTENSION)


def image_stem_for_product(product_url: str) -> str:
    """Build a stable, filesystem-safe file stem from the product URL slug."""
    path = urlparse(product_url).path.strip("/")
    return path.replace("/", "_") or "product"


def find_existing_image(images_dir: Path, stem: str) -> Path | None:
    """Return an already downloaded image for this stem, whatever its extension."""
    for ext in IMAGE_EXTENSIONS:
        candidate = images_dir / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    return None


def download_product_images(
    product: Product,
    client: HttpClient,
    images_dir: Path,
    relative_to: Path | None = None,
) -> list[str]:
    """
    Download every image in product.image_urls into images_dir.
    Files already on disk are reused, so re-crawls do not re-download.
    Stores and returns local paths (POSIX style, relative to `relative_to` when given).
    """
    images_dir.mkdir(parents=True, exist_ok=True)
    base_stem = image_stem_for_product(product.product_url)
    saved: list[str] = []

    for index, image_url in enumerate(product.image_urls):
        stem = base_stem if index == 0 else f"{base_stem}_{index}"
        target = find_existing_image(images_dir, stem)

        if target is None:
            result = client.fetch_bytes(image_url)
            if result is None:
                logger.warning("Failed to download image: %s", image_url)
                continue
            content, content_type = result
            target = images_dir / f"{stem}{guess_image_extension(image_url, content_type)}"
            target.write_bytes(content)
            logger.info("Saved image (%d bytes) to %s", len(content), target)
        else:
            logger.debug("Image already exists, skipping download: %s", target)

        if relative_to is not None:
            try:
                saved.append(target.relative_to(relative_to).as_posix())
                continue
            except ValueError:
                pass
        saved.append(target.as_posix())

    product.image_paths = saved
    return saved
