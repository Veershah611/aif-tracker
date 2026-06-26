"""
HTTP client utilities with anti-bot evasion.

Provides:
  - NSESession: handles cookie/CSRF initialization for NSE API calls
  - BSESession: session wrapper for BSE API endpoints
  - create_session: generic session factory with proxy + UA rotation
  - Exponential backoff and retry logic
"""

import random
import time
from typing import Optional, Dict
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.core.config import (
    settings,
    USER_AGENTS,
    NSE_HOMEPAGE,
    BSE_HOMEPAGE,
)
from app.core.logger import get_logger

logger = get_logger(__name__)


def _random_ua() -> str:
    """Return a random User-Agent string."""
    return random.choice(USER_AGENTS)


def _random_proxy() -> Optional[Dict[str, str]]:
    """Return a random proxy from the pool, or None if pool is empty."""
    if not settings.PROXY_POOL:
        return None
    proxy = random.choice(settings.get_proxy_pool)
    return {"http": proxy, "https": proxy}


def random_delay():
    """Sleep for a random duration between configured min and max."""
    delay = random.uniform(settings.REQUEST_DELAY_MIN, settings.REQUEST_DELAY_MAX)
    time.sleep(delay)


def create_session(proxy: Optional[Dict[str, str]] = None) -> requests.Session:
    """
    Create a requests.Session with retry logic and realistic headers.
    """
    session = requests.Session()

    # Retry strategy with exponential backoff
    retry_strategy = Retry(
        total=settings.MAX_RETRIES,
        backoff_factor=settings.BACKOFF_FACTOR,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    # Set default headers matching nse_pipeline.py to bypass bot protection
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    })

    # Apply proxy
    if proxy:
        session.proxies.update(proxy)
    elif settings.PROXY_POOL:
        session.proxies.update(_random_proxy())

    return session


class NSESession:
    """
    Manages an authenticated session for the NSE API.

    Per document §6.1:
    1. GET the NSE homepage to capture session cookies + CSRF tokens
    2. Attach cookies and headers to subsequent API requests
    3. Handle rate limiting with exponential backoff
    """

    def __init__(self):
        self.session = create_session()
        self._initialized = False

    def _initialize(self):
        """
        Perform session initialization by visiting the NSE homepage.
        NSE often returns 403 to automated requests. We accept whatever
        cookies we get and proceed — the API endpoint may still work.
        """
        logger.info("Initializing NSE session (visiting homepage for cookies)...")
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })

        try:
            response = self.session.get(NSE_HOMEPAGE, timeout=15)
            logger.info(
                "NSE homepage returned %d. Cookies captured: %d",
                response.status_code, len(self.session.cookies)
            )
        except requests.RequestException as e:
            logger.warning("NSE homepage request failed: %s (proceeding anyway)", e)

        self._initialized = True

        # Brief pause to mimic human behavior
        random_delay()

    def get(self, url: str, **kwargs) -> requests.Response:
        """
        Make an authenticated GET request to the NSE API.
        Auto-initializes on first call.
        Retries with new session on 403/401.
        """
        if not self._initialized:
            self._initialize()

        kwargs.setdefault("timeout", 15)

        for attempt in range(settings.MAX_RETRIES):
            try:
                response = self.session.get(url, **kwargs)

                if response.status_code == 403:
                    logger.warning(
                        "NSE returned 403 on attempt %d. Re-initializing session...",
                        attempt + 1
                    )
                    wait_time = settings.BACKOFF_FACTOR ** attempt
                    time.sleep(wait_time)
                    self.session = create_session()
                    self._initialized = False
                    self._initialize()
                    continue

                if response.status_code == 429:
                    wait_time = settings.BACKOFF_FACTOR ** (attempt + 2)
                    logger.warning(
                        "NSE rate limit hit. Backing off for %ds...", wait_time
                    )
                    time.sleep(wait_time)
                    continue

                response.raise_for_status()
                return response

            except requests.RequestException as e:
                logger.error("NSE request error (attempt %d): %s", attempt + 1, e)
                if attempt == settings.MAX_RETRIES - 1:
                    raise
                time.sleep(settings.BACKOFF_FACTOR ** attempt)

        raise requests.RequestException(f"Failed after {settings.MAX_RETRIES} retries: {url}")


class BSESession:
    """
    Session wrapper for BSE API endpoints.
    BSE is less aggressive with anti-bot measures but still needs proper headers.
    """

    def __init__(self):
        self.session = create_session()
        self.session.headers.update({
            "Referer": BSE_HOMEPAGE,
            "Origin": BSE_HOMEPAGE,
            "Accept": "application/json, text/plain, */*",
        })

    def get(self, url: str, **kwargs) -> requests.Response:
        """Make a GET request to BSE API with proper headers."""
        kwargs.setdefault("timeout", 15)

        for attempt in range(settings.MAX_RETRIES):
            try:
                random_delay()
                response = self.session.get(url, **kwargs)
                response.raise_for_status()
                return response

            except requests.RequestException as e:
                logger.error("BSE request error (attempt %d): %s", attempt + 1, e)
                if attempt == settings.MAX_RETRIES - 1:
                    raise
                wait_time = settings.BACKOFF_FACTOR ** attempt
                time.sleep(wait_time)
                # Rotate UA on retry
                self.session.headers["User-Agent"] = _random_ua()

        raise requests.RequestException(f"Failed after {settings.MAX_RETRIES} retries: {url}")
