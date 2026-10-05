from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Product:
    """Represents a product item in the catalog."""

    name: str
    brand: Optional[str] = None
    category: Optional[str] = None
    price: Optional[int] = None
    unit: Optional[str] = None
    product_url: str = ""
    image_url: Optional[str] = None
    image_urls: list[str] = field(default_factory=list)
    image_paths: list[str] = field(default_factory=list)
    source: str = "bachhoaxanh"
    crawled_at: str = ""

    def __post_init__(self) -> None:
        if not self.crawled_at:
            self.crawled_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        """Convert the product object to a clean dictionary."""
        return asdict(self)
