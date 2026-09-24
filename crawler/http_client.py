import logging
import time
from typing import Optional

import requests

from config import (
    BACKOFF_FACTOR,
    DEFAULT_DELAY,
    DEFAULT_TIMEOUT,
    DEFAULT_USER_AGENT,
    MAX_RETRIES,
)

logger = logging.getLogger(__name__)


class HttpClient:
    """HTTP client for polite, resilient crawling of public web pages."""

    def __init__(
        self,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: int = DEFAULT_TIMEOUT,
        delay: float = DEFAULT_DELAY,
        max_retries: int = MAX_RETRIES,
        backoff_factor: float = BACKOFF_FACTOR,
    ) -> None:
        self.timeout = timeout
        self.delay = delay
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            }
        )
        self._last_request_time: float = 0.0

    def _apply_rate_limit(self) -> None:
        """Enforce delay between consecutive requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.delay:
            sleep_duration = self.delay - elapsed
            logger.debug("Rate limiting: sleeping for %.2f seconds", sleep_duration)
            time.sleep(sleep_duration)

    def fetch_html(self, url: str) -> Optional[str]:
        """
        Fetch HTML content from a public URL with retry logic for transient errors.
        Returns HTML string on success, or None on failure.
        """
        for attempt in range(self.max_retries + 1):
            try:
                self._apply_rate_limit()
                self._last_request_time = time.time()

                logger.info("Requesting URL [attempt %d/%d]: %s", attempt + 1, self.max_retries + 1, url)
                resp = self.session.get(url, timeout=self.timeout)

                if resp.status_code == 200:
                    return resp.text

                # Client error (e.g. 404 Not Found, 403 Forbidden) - do not retry
                if 400 <= resp.status_code < 500:
                    logger.warning(
                        "Client error %d for URL: %s. Skipping retry.",
                        resp.status_code,
                        url,
                    )
                    return None

                # Server error (5xx) - retry if attempts remain
                logger.warning(
                    "Server returned status %d for URL: %s (attempt %d)",
                    resp.status_code,
                    url,
                    attempt + 1,
                )

            except (requests.Timeout, requests.ConnectionError) as exc:
                logger.warning(
                    "Network error on attempt %d for URL %s: %s",
                    attempt + 1,
                    url,
                    exc,
                )
            except requests.RequestException as exc:
                logger.error("Non-retryable request error for URL %s: %s", url, exc)
                return None

            # Exponential backoff before next attempt
            if attempt < self.max_retries:
                backoff = self.backoff_factor * (2**attempt)
                logger.info("Retrying in %.1f seconds...", backoff)
                time.sleep(backoff)

        logger.error("Failed to fetch URL after %d attempts: %s", self.max_retries + 1, url)
        return None
