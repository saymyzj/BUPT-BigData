import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

from crawlers.base import BaseCrawler
from parsers.html_tables import extract_page_title, extract_tables, soup_from_html
from parsers.normalizers import clean_disease_name, clean_text, infer_disease_category, parse_int


REPORT_DATE_PATTERN = re.compile(r"(?P<year>20\d{2})年(?P<month>\d{1,2})月")


class ChinaCdcMonthlyCrawler(BaseCrawler):
    """中国疾控中心全国法定传染病月报爬虫。"""

    source_key = "chinacdc_monthly"
    data_type = "disease_monthly"

    def discover_urls(self, limit: int | None = None) -> list[str]:
        """从中国疾控列表页发现月报详情页链接。

        中国疾控列表页为静态 HTML。本方法会按较保守的方式读取分页，
        只收集标题符合“传染病疫情概况/情况”的月报详情页。
        """
        urls: list[str] = []
        seen: set[str] = set()
        start_year = int(self.config.get("start_year", 2010))
        end_year = int(self.config.get("end_year", datetime.now().year))
        consecutive_failures = 0

        for list_url in self._build_list_urls():
            try:
                html = self._read_list_page(list_url)
            except Exception as exc:
                self.logger.warning("failed to read list page %s: %s", list_url, exc)
                consecutive_failures += 1
                if urls and consecutive_failures >= 2:
                    self.logger.info("连续分页读取失败，停止继续探测列表页")
                    break
                continue
            consecutive_failures = 0

            soup = soup_from_html(html)
            for link in soup.find_all("a"):
                title = clean_text(link.get_text(" ", strip=True))
                href = link.get("href")
                if not title or not href:
                    continue
                if "传染病疫情概况" not in title and "传染病疫情情况" not in title:
                    continue
                match = REPORT_DATE_PATTERN.search(title)
                if not match:
                    continue
                report_year = int(match.group("year"))
                if not (start_year <= report_year <= end_year):
                    continue
                detail_url = urljoin(list_url, href)
                if detail_url not in seen:
                    seen.add(detail_url)
                    urls.append(detail_url)
                if limit and len(urls) >= limit:
                    return urls
        return urls

    def _read_list_page(self, list_url: str) -> str:
        """读取列表页，并与详情页使用相同的缓存和限速策略。"""
        cache_path = self.cache.path_for_url(
            list_url,
            f"{self.raw_subdir}/list_pages",
            default_suffix=".html",
        )
        if not self.force and self.cache.has_file(cache_path):
            return cache_path.read_text(encoding="utf-8", errors="ignore")

        result = self.http.fetch(list_url, referer=self.config.get("base_url"))
        html = result.content.decode("utf-8", errors="ignore")
        self.cache.write_bytes(cache_path, html.encode("utf-8"))
        self.cache.write_url(cache_path, list_url)
        return html

    def _build_list_urls(self) -> list[str]:
        """生成中国疾控常见分页列表地址。"""
        base_url = self.config["base_url"]
        urls = list(self.config.get("list_urls", []))
        urls.extend(urljoin(base_url, f"index_{page}.html") for page in range(1, 30))
        return urls

    def parse_raw_files(self, raw_files: list[Path]) -> list[dict]:
        records: list[dict] = []
        for raw_file in raw_files:
            html = raw_file.read_text(encoding="utf-8", errors="ignore")
            soup = soup_from_html(html)
            page_title = extract_page_title(soup)
            report_year, report_month = self._parse_report_date(page_title, soup)
            source_url = self._recover_source_url(raw_file)

            for table in extract_tables(soup):
                records.extend(
                    self._parse_disease_table(
                        table=table,
                        page_title=page_title,
                        report_year=report_year,
                        report_month=report_month,
                        source_url=source_url,
                        raw_file=raw_file,
                    )
                )
        return records

    def _parse_report_date(self, page_title: str, soup) -> tuple[int | None, int | None]:
        text = page_title or soup.get_text(" ", strip=True)
        match = REPORT_DATE_PATTERN.search(text)
        if not match:
            return None, None
        return int(match.group("year")), int(match.group("month"))

    def _recover_source_url(self, raw_file: Path) -> str:
        """从原始缓存文件旁边的 .url 文件恢复来源链接。"""
        return self.cache.read_url(raw_file)

    def _parse_disease_table(
        self,
        *,
        table: list[list[str]],
        page_title: str,
        report_year: int | None,
        report_month: int | None,
        source_url: str,
        raw_file: Path,
    ) -> list[dict]:
        if not table:
            return []

        header_index = self._find_header_index(table)
        if header_index is None:
            return []

        rows = table[header_index + 1 :]
        records: list[dict] = []
        current_category = ""
        for row in rows:
            if len(row) < 3:
                continue
            disease_name = clean_disease_name(row[0])
            cases = parse_int(row[1])
            deaths = parse_int(row[2])
            if not disease_name or cases is None or deaths is None:
                continue

            inferred_category = infer_disease_category(disease_name)
            if inferred_category:
                current_category = inferred_category

            records.append(
                {
                    "source_name": self.source_name,
                    "source_url": source_url,
                    "report_title": page_title,
                    "report_year": report_year,
                    "report_month": report_month,
                    "region": "全国",
                    "disease_name": disease_name,
                    "disease_category": current_category,
                    "cases": cases,
                    "deaths": deaths,
                    "incidence_rate": "",
                    "mortality_rate": "",
                    "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "raw_file": str(raw_file),
                }
            )
        return records

    @staticmethod
    def _find_header_index(table: list[list[str]]) -> int | None:
        for index, row in enumerate(table):
            joined = "|".join(row)
            if "病名" in joined and "发病数" in joined and "死亡数" in joined:
                return index
        return None
