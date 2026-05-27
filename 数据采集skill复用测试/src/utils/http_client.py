import random
import time
from dataclasses import dataclass
from typing import Optional

import requests


class AntiCrawlerBlocked(RuntimeError):
    """Raised when a public source returns a clear anti-crawler status."""


@dataclass
class FetchResult:
    url: str
    status_code: int
    content: bytes
    content_type: str
    elapsed_seconds: float


class HttpClient:
    """Small HTTP client with retries, polite delay, and reproducible headers."""

    def __init__(
        self,
        *,
        min_delay: float = 0.2,
        max_delay: float = 0.8,
        timeout: float = 25.0,
        max_retries: int = 2,
        user_agent: str = "CourseDataCollectionTest/1.0 contact@example.com",
        trust_env: bool = False,
    ) -> None:
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.timeout = timeout
        self.max_retries = max_retries
        self.last_request_at = 0.0
        self.session = requests.Session()
        self.session.trust_env = trust_env
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "application/json,text/plain,*/*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Connection": "keep-alive",
            }
        )

    def _wait(self) -> None:
        now = time.monotonic()
        sleep_seconds = max(
            0.0,
            random.uniform(self.min_delay, self.max_delay) - (now - self.last_request_at),
        )
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)
        self.last_request_at = time.monotonic()

    def fetch(self, url: str, *, referer: Optional[str] = None) -> FetchResult:
        headers = {"Referer": referer} if referer else None
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            self._wait()
            started_at = time.monotonic()
            try:
                response = self.session.get(url, headers=headers, timeout=self.timeout)
                elapsed = time.monotonic() - started_at
                if response.status_code in {403, 429}:
                    raise AntiCrawlerBlocked(
                        f"blocked by server: status={response.status_code}, url={url}"
                    )
                response.raise_for_status()
                return FetchResult(
                    url=url,
                    status_code=response.status_code,
                    content=response.content,
                    content_type=response.headers.get("Content-Type", ""),
                    elapsed_seconds=elapsed,
                )
            except AntiCrawlerBlocked:
                raise
            except Exception as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"failed to fetch url after retries: {url}") from last_error
