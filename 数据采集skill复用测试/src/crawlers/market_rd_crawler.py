import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import pandas as pd

from utils.cache import RawCache
from utils.http_client import HttpClient


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
INTERIM_DIR = PROJECT_ROOT / "data" / "interim"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CONFIG_DIR = PROJECT_ROOT / "src" / "config"
LOG_DIR = PROJECT_ROOT / "logs"


@dataclass
class Company:
    ticker: str
    company_name: str
    industry_group: str
    cik: str | None = None


class MarketRdCrawler:
    """Collect Yahoo daily market data and SEC XBRL annual R&D data."""

    def __init__(
        self,
        *,
        start_date: str = "2024-01-01",
        end_date: str = "2024-12-31",
        min_delay: float = 0.2,
        max_delay: float = 0.8,
        force: bool = False,
    ) -> None:
        self.start_date = start_date
        self.end_date = end_date
        self.force = force
        self.cache = RawCache(RAW_DIR)
        self.http = HttpClient(min_delay=min_delay, max_delay=max_delay)
        self.crawl_time = datetime.now(timezone.utc).isoformat()
        self.failures: list[dict[str, str]] = []

    def load_companies(self, limit: int | None = None) -> list[Company]:
        data = json.loads((CONFIG_DIR / "company_universe.json").read_text(encoding="utf-8"))
        if limit:
            data = data[:limit]
        return [Company(**item) for item in data]

    def discover_urls(self, companies: list[Company]) -> dict[str, list[str] | str]:
        return {
            "company_tickers": "https://www.sec.gov/files/company_tickers.json",
            "yahoo_chart": [self._yahoo_url(company.ticker) for company in companies],
            "sec_companyfacts": [],
        }

    def fetch_urls(self, companies: list[Company]) -> tuple[dict[str, Path], dict[str, Path]]:
        ticker_index_path = self._fetch_json(
            "https://www.sec.gov/files/company_tickers.json",
            "sec_companyfacts",
            default_name="company_tickers.json",
        )
        cik_map = self._parse_cik_map(ticker_index_path)

        chart_files: dict[str, Path] = {}
        sec_files: dict[str, Path] = {}
        for company in companies:
            company.cik = cik_map.get(company.ticker.upper())
            chart_url = self._yahoo_url(company.ticker)
            chart_path = self._fetch_json(chart_url, "yahoo_chart", required=False)
            if chart_path:
                chart_files[company.ticker] = chart_path
            if company.cik:
                facts_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{company.cik}.json"
                facts_path = self._fetch_json(facts_url, "sec_companyfacts", required=False)
                if facts_path:
                    sec_files[company.ticker] = facts_path
        self._write_failures()
        return chart_files, sec_files

    def parse_raw_files(
        self,
        companies: list[Company],
        chart_files: dict[str, Path],
        sec_files: dict[str, Path],
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        stock_frames = [
            self._parse_yahoo_chart(company, chart_files[company.ticker])
            for company in companies
            if company.ticker in chart_files
        ]
        rd_frames = [
            self._parse_sec_companyfacts(company, sec_files[company.ticker])
            for company in companies
            if company.ticker in sec_files
        ]
        stock_daily = pd.concat(stock_frames, ignore_index=True) if stock_frames else pd.DataFrame()
        rd_annual = pd.concat(rd_frames, ignore_index=True) if rd_frames else pd.DataFrame()
        return stock_daily, rd_annual

    def save_csv(self, stock_daily: pd.DataFrame, rd_annual: pd.DataFrame) -> dict[str, Path]:
        INTERIM_DIR.mkdir(parents=True, exist_ok=True)
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        stock_path = INTERIM_DIR / "stock_daily_market.csv"
        rd_path = INTERIM_DIR / "rd_annual_sec.csv"
        merged_path = PROCESSED_DIR / "market_rd_daily_merged.csv"

        stock_daily.to_csv(stock_path, index=False, encoding="utf-8-sig")
        rd_annual.to_csv(rd_path, index=False, encoding="utf-8-sig")
        merged = self._merge_market_rd(stock_daily, rd_annual)
        merged.to_csv(merged_path, index=False, encoding="utf-8-sig")

        return {
            "stock_daily": stock_path,
            "rd_annual": rd_path,
            "merged": merged_path,
        }

    def run(self, *, limit: int | None = None, parse_only: bool = False) -> dict[str, Path]:
        companies = self.load_companies(limit=limit)
        if parse_only:
            chart_files = self._existing_files("yahoo_chart", companies)
            sec_files = self._existing_files("sec_companyfacts", companies)
        else:
            chart_files, sec_files = self.fetch_urls(companies)
        stock_daily, rd_annual = self.parse_raw_files(companies, chart_files, sec_files)
        return self.save_csv(stock_daily, rd_annual)

    def _fetch_json(
        self,
        url: str,
        subdir: str,
        *,
        default_name: str | None = None,
        required: bool = True,
    ) -> Path | None:
        path = self.cache.path_for_url(url, subdir, default_suffix=".json")
        if default_name:
            path = path.parent / default_name
        if self.cache.has_file(path) and not self.force:
            return path
        try:
            result = self.http.fetch(url)
            self.cache.write_bytes(path, result.content)
            self.cache.write_url(path, url)
            return path
        except Exception as exc:
            self.failures.append({"url": url, "subdir": subdir, "error": str(exc)})
            if required:
                raise
            return None

    def _write_failures(self) -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        failure_path = LOG_DIR / "failed_urls.json"
        failure_path.write_text(
            json.dumps(self.failures, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _existing_files(self, subdir: str, companies: list[Company]) -> dict[str, Path]:
        files: dict[str, Path] = {}
        for company in companies:
            pattern = f"*{company.ticker.lower()}*"
            candidates = list((RAW_DIR / subdir).glob(pattern))
            if candidates:
                files[company.ticker] = candidates[0]
        return files

    def _parse_cik_map(self, path: Path) -> dict[str, str]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        cik_map: dict[str, str] = {}
        for item in payload.values():
            ticker = item.get("ticker")
            cik = item.get("cik_str")
            if ticker and cik:
                cik_map[ticker.upper()] = str(cik).zfill(10)
        return cik_map

    def _yahoo_url(self, ticker: str) -> str:
        start_ts = int(pd.Timestamp(self.start_date, tz="UTC").timestamp())
        end_ts = int((pd.Timestamp(self.end_date, tz="UTC") + pd.Timedelta(days=1)).timestamp())
        params = urlencode(
            {
                "period1": start_ts,
                "period2": end_ts,
                "interval": "1d",
                "events": "history",
                "includeAdjustedClose": "true",
            }
        )
        return f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?{params}"

    def _parse_yahoo_chart(self, company: Company, path: Path) -> pd.DataFrame:
        payload = json.loads(path.read_text(encoding="utf-8"))
        result = payload.get("chart", {}).get("result", [])
        if not result:
            return pd.DataFrame()
        chart = result[0]
        timestamps = chart.get("timestamp", [])
        quote = chart.get("indicators", {}).get("quote", [{}])[0]
        adjclose = chart.get("indicators", {}).get("adjclose", [{}])[0].get("adjclose", [])
        source_url = path.with_suffix(path.suffix + ".url").read_text(encoding="utf-8").strip()

        rows = []
        for index, ts in enumerate(timestamps):
            close = self._value_at(quote.get("close", []), index)
            open_price = self._value_at(quote.get("open", []), index)
            high = self._value_at(quote.get("high", []), index)
            low = self._value_at(quote.get("low", []), index)
            volume = self._value_at(quote.get("volume", []), index)
            adj_close = self._value_at(adjclose, index)
            if close is None:
                continue
            rows.append(
                {
                    "ticker": company.ticker,
                    "company_name": company.company_name,
                    "industry_group": company.industry_group,
                    "trade_date": datetime.fromtimestamp(ts, timezone.utc).date().isoformat(),
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close,
                    "adj_close": adj_close,
                    "volume": volume,
                    "daily_return": None,
                    "source_url": source_url,
                    "crawl_time": self.crawl_time,
                    "raw_file": str(path.relative_to(PROJECT_ROOT)),
                }
            )

        frame = pd.DataFrame(rows)
        if not frame.empty:
            frame["daily_return"] = frame.sort_values("trade_date")["adj_close"].pct_change()
        return frame

    def _parse_sec_companyfacts(self, company: Company, path: Path) -> pd.DataFrame:
        payload = json.loads(path.read_text(encoding="utf-8"))
        facts = payload.get("facts", {}).get("us-gaap", {})
        source_url = path.with_suffix(path.suffix + ".url").read_text(encoding="utf-8").strip()
        tag_priority = [
            "ResearchAndDevelopmentExpense",
            "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost",
            "ResearchAndDevelopmentExpenseSoftwareExcludingAcquiredInProcessCost",
        ]

        rows = []
        for tag in tag_priority:
            fact = facts.get(tag, {})
            units = fact.get("units", {}).get("USD", [])
            for item in units:
                form = item.get("form")
                fiscal_year = item.get("fy")
                value = item.get("val")
                filed = item.get("filed")
                frame = item.get("frame")
                if form not in {"10-K", "20-F"} or fiscal_year is None or value is None:
                    continue
                if frame and not str(frame).startswith("CY"):
                    continue
                rows.append(
                    {
                        "ticker": company.ticker,
                        "company_name": company.company_name,
                        "industry_group": company.industry_group,
                        "cik": company.cik,
                        "fiscal_year": int(fiscal_year),
                        "rd_expense_usd": float(value),
                        "rd_expense_musd": float(value) / 1_000_000,
                        "sec_fact_tag": tag,
                        "form": form,
                        "filed_date": filed,
                        "source_url": source_url,
                        "crawl_time": self.crawl_time,
                        "raw_file": str(path.relative_to(PROJECT_ROOT)),
                    }
                )
            if rows:
                break

        frame = pd.DataFrame(rows)
        if frame.empty:
            return frame
        frame = frame.sort_values(["ticker", "fiscal_year", "filed_date"])
        return frame.drop_duplicates(["ticker", "fiscal_year"], keep="last")

    def _merge_market_rd(self, stock_daily: pd.DataFrame, rd_annual: pd.DataFrame) -> pd.DataFrame:
        if stock_daily.empty:
            return stock_daily
        stock = stock_daily.copy()
        stock["trade_year"] = pd.to_datetime(stock["trade_date"]).dt.year
        if rd_annual.empty:
            stock["matched_fiscal_year"] = math.nan
            stock["rd_expense_usd"] = math.nan
            stock["rd_expense_musd"] = math.nan
            return stock

        rd_latest = rd_annual.sort_values("fiscal_year").copy()
        rows = []
        for ticker, group in stock.groupby("ticker", sort=False):
            ticker_rd = rd_latest[rd_latest["ticker"] == ticker]
            if ticker_rd.empty:
                merged = group.copy()
                merged["matched_fiscal_year"] = math.nan
                merged["rd_expense_usd"] = math.nan
                merged["rd_expense_musd"] = math.nan
                rows.append(merged)
                continue
            candidate = ticker_rd[ticker_rd["fiscal_year"] <= group["trade_year"].max()]
            if candidate.empty:
                candidate = ticker_rd
            chosen = candidate.sort_values("fiscal_year").iloc[-1]
            merged = group.copy()
            merged["matched_fiscal_year"] = int(chosen["fiscal_year"])
            merged["rd_expense_usd"] = chosen["rd_expense_usd"]
            merged["rd_expense_musd"] = chosen["rd_expense_musd"]
            merged["rd_source_url"] = chosen["source_url"]
            merged["rd_raw_file"] = chosen["raw_file"]
            rows.append(merged)
        return pd.concat(rows, ignore_index=True)

    @staticmethod
    def _value_at(values: list, index: int):
        if index >= len(values):
            return None
        value = values[index]
        if value is None:
            return None
        return value
