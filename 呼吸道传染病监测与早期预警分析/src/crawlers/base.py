import csv
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable

from utils.cache import RawCache
from utils.http_client import AntiCrawlerBlocked, HttpClient
from utils.logger import setup_logger
from utils.paths import CONFIG_DIR, INTERIM_DIR, LOG_DIR, RAW_DIR, ensure_project_dirs
from utils.task_store import TaskStore


class BaseCrawler:
    """官方公开数据爬虫基类，封装下载、缓存、解析和保存流程。"""

    source_key: str = ""
    data_type: str = ""
    raw_default_suffix: str = ".html"

    def __init__(
        self,
        *,
        min_delay: float = 1.0,
        max_delay: float = 3.0,
        max_workers: int = 4,
        force: bool = False,
    ) -> None:
        ensure_project_dirs()
        self.config = self._load_config()[self.source_key]
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_workers = max_workers
        self.force = force
        self.logger = setup_logger(LOG_DIR)
        self.http = HttpClient(min_delay=min_delay, max_delay=max_delay)
        self.cache = RawCache(RAW_DIR)
        self.task_store = TaskStore(LOG_DIR / "crawl_tasks.sqlite")

    @staticmethod
    def _load_config() -> dict:
        config_path = CONFIG_DIR / "sources.json"
        return json.loads(config_path.read_text(encoding="utf-8"))

    @property
    def source_name(self) -> str:
        return self.config["source_name"]

    @property
    def raw_subdir(self) -> str:
        return self.config["raw_subdir"]

    def discover_urls(self, limit: int | None = None) -> list[str]:
        raise NotImplementedError

    def parse_raw_files(self, raw_files: Iterable[Path]) -> list[dict]:
        raise NotImplementedError

    def fetch_urls(self, urls: list[str]) -> list[Path]:
        """下载 URL 列表，复用本地缓存，并记录任务状态。"""
        self.task_store.upsert_pending(self.source_key, self.data_type, urls)
        raw_files: list[Path] = []

        def fetch_one(url: str) -> Path:
            cache_path = self.cache.path_for_url(
                url,
                self.raw_subdir,
                default_suffix=self.raw_default_suffix,
            )
            if not self.force and self.cache.has_file(cache_path):
                self.task_store.mark_success(url, 200, cache_path)
                return cache_path
            result = self.http.fetch(url, referer=self.config.get("base_url"))
            self.cache.write_bytes(cache_path, result.content)
            self.cache.write_url(cache_path, url)
            self.task_store.mark_success(url, result.status_code, cache_path)
            return cache_path

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {executor.submit(fetch_one, url): url for url in urls}
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    raw_file = future.result()
                    raw_files.append(raw_file)
                    self.logger.info("fetched %s -> %s", url, raw_file)
                except AntiCrawlerBlocked as exc:
                    self.task_store.mark_failed(url, str(exc))
                    self.logger.error("anti-crawler signal: %s", exc)
                except Exception as exc:
                    self.task_store.mark_failed(url, str(exc))
                    self.logger.warning("failed %s: %s", url, exc)
        return raw_files

    def save_csv(self, records: list[dict], filename: str) -> Path:
        """按稳定字段顺序保存 CSV 文件，便于后续分析和检查。"""
        output_path = INTERIM_DIR / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if not records:
            output_path.write_text("", encoding="utf-8")
            return output_path

        fieldnames = list(records[0].keys())
        with output_path.open("w", encoding="utf-8-sig", newline="") as fp:
            writer = csv.DictWriter(fp, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
        return output_path

    def run(self, *, limit: int | None = None, parse_only: bool = False) -> Path:
        urls = self.discover_urls(limit=limit)
        self.logger.info("discovered %s urls for %s", len(urls), self.source_key)
        raw_files = [
            self.cache.path_for_url(url, self.raw_subdir, default_suffix=self.raw_default_suffix)
            for url in urls
            if self.cache.has_file(
                self.cache.path_for_url(url, self.raw_subdir, default_suffix=self.raw_default_suffix)
            )
        ]
        if not parse_only:
            raw_files = self.fetch_urls(urls)
        records = self.parse_raw_files(raw_files)
        output_path = self.save_csv(records, f"{self.source_key}.csv")
        self.logger.info("saved %s records -> %s", len(records), output_path)
        return output_path
