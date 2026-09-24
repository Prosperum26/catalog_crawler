from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

OUTPUT_JSON_PATH = PROCESSED_DATA_DIR / "products.json"
OUTPUT_CSV_PATH = PROCESSED_DATA_DIR / "products.csv"

# Network & Crawler Settings
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

DEFAULT_TIMEOUT = 10  # seconds
DEFAULT_DELAY = 1.5   # polite delay between requests in seconds
MAX_RETRIES = 2
BACKOFF_FACTOR = 1.0

# Product source identifier
DEFAULT_SOURCE = "bachhoaxanh"

# Sitemap Discovery Settings
SITEMAP_INDEX_URL = "https://www.bachhoaxanh.com/sitemapnew/sitemap-product"
DEFAULT_DISCOVERY_LIMIT = 50
DEFAULT_URLS_OUTPUT_PATH = BASE_DIR / "urls.txt"
