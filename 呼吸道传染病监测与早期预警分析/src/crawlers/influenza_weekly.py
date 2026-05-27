import re
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

from crawlers.base import BaseCrawler
from parsers.html_tables import extract_page_title, soup_from_html
from parsers.normalizers import clean_text, parse_float, parse_int


REPORT_PATTERN = re.compile(r"(?P<year>20\d{2})年第(?P<week>\d{1,2})周第(?P<issue>\d+)期")
DATE_RANGE_PATTERN = re.compile(
    r"(?P<start_year>20\d{2}) 年第 (?P<week>\d{1,2}) 周（"
    r"(?P<start_year2>20\d{2}) 年 (?P<start_month>\d{1,2}) 月 (?P<start_day>\d{1,2}) 日[－—-]"
    r"(?P<end_year>20\d{2}) 年 (?P<end_month>\d{1,2}) 月 (?P<end_day>\d{1,2}) 日"
)
ILI_PATTERN = re.compile(
    r"(?P<region>南方省份|北方省份)哨点医院报告的 ILI%为 (?P<ili>[0-9.]+)%"
)
OUTBREAK_PATTERN = re.compile(r"全国共报告 (?P<count>\d+) 起流感样病例暴发疫情")
LAB_ROW_PATTERN = re.compile(
    r"^(?P<metric>检测数|阳性数\(\%\)|A型|A\(H1N1\)pdm09|A\(H3N2\)|A\(unsubtyped\)|B型|B\s*未分系|Victoria|Yamagata)\s+"
    r"(?P<south>\S+)\s+(?P<north>\S+)\s+(?P<total>\S+)"
)


class InfluenzaWeeklyCrawler(BaseCrawler):
    """中国疾控中心流感监测周报爬虫。"""

    source_key = "influenza_weekly"
    data_type = "influenza_weekly"

    def discover_urls(self, limit: int | None = None) -> list[str]:
        """从流感周报列表页发现详情页链接。"""
        urls: list[str] = []
        seen: set[str] = set()
        start_year = int(self.config.get("start_year", 2023))
        end_year = int(self.config.get("end_year", datetime.now().year))

        for list_url in self._build_list_urls():
            try:
                html = self._read_list_page(list_url)
            except Exception as exc:
                self.logger.warning("读取流感周报列表页失败 %s: %s", list_url, exc)
                continue

            soup = soup_from_html(html)
            for link in soup.find_all("a"):
                title = clean_text(link.get_text(" ", strip=True))
                href = link.get("href")
                if not title or not href or "中国流感监测周报" not in title:
                    continue
                match = REPORT_PATTERN.search(title)
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

    def _build_list_urls(self) -> list[str]:
        """根据配置生成流感周报分页列表地址。"""
        base_url = self.config["base_url"]
        urls = list(self.config.get("list_urls", []))
        max_pages = int(self.config.get("max_list_pages", 0))
        urls.extend(urljoin(base_url, f"index_{page}.html") for page in range(1, max_pages + 1))
        return urls

    def _read_list_page(self, list_url: str) -> str:
        """读取并缓存列表页，避免重复访问官网。"""
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

    def parse_raw_files(self, raw_files: list[Path]) -> list[dict]:
        records: list[dict] = []
        for raw_file in raw_files:
            html = raw_file.read_text(encoding="utf-8", errors="ignore")
            soup = soup_from_html(html)
            page_title = extract_page_title(soup)
            source_url = self.cache.read_url(raw_file)
            report_year, report_week, issue_no = self._parse_report_meta(page_title)
            pdf_url = self._find_pdf_url(soup, source_url)
            pdf_file = self._download_pdf(pdf_url) if pdf_url else Path()
            pdf_text = self._extract_pdf_text(pdf_file) if pdf_file else ""
            records.extend(
                self._parse_pdf_text(
                    pdf_text=pdf_text,
                    page_title=page_title,
                    report_year=report_year,
                    report_week=report_week,
                    issue_no=issue_no,
                    source_url=source_url,
                    pdf_url=pdf_url,
                    pdf_file=pdf_file,
                    raw_file=raw_file,
                )
            )
        return records

    def _base_record(
        self,
        page_title: str,
        report_year: int | None,
        report_week: int | None,
        issue_no: int | None,
        source_url: str,
        pdf_url: str,
        pdf_file: Path,
        raw_file: Path,
    ) -> dict:
        return {
            "source_name": self.source_name,
            "source_url": source_url,
            "pdf_url": pdf_url,
            "report_title": page_title,
            "report_year": report_year,
            "report_week": report_week,
            "issue_no": issue_no,
            "week_start": "",
            "week_end": "",
            "region_group": "",
            "metric_type": "",
            "metric_name": "",
            "metric_value": "",
            "metric_percent": "",
            "dominant_subtype": "",
            "outbreak_count": "",
            "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "raw_file": str(raw_file),
            "pdf_file": str(pdf_file) if pdf_file else "",
        }

    def _parse_pdf_text(
        self,
        *,
        pdf_text: str,
        page_title: str,
        report_year: int | None,
        report_week: int | None,
        issue_no: int | None,
        source_url: str,
        pdf_url: str,
        pdf_file: Path,
        raw_file: Path,
    ) -> list[dict]:
        records: list[dict] = []
        week_start, week_end = self._parse_week_range(pdf_text)
        dominant_subtype = self._parse_dominant_subtype(pdf_text)
        outbreak_count = self._parse_outbreak_count(pdf_text)

        summary = self._base_record(
            page_title, report_year, report_week, issue_no, source_url, pdf_url, pdf_file, raw_file
        )
        summary.update(
            {
                "week_start": week_start,
                "week_end": week_end,
                "metric_type": "summary",
                "metric_name": "dominant_subtype",
                "dominant_subtype": dominant_subtype,
                "outbreak_count": outbreak_count,
            }
        )
        records.append(summary)

        seen_ili_regions: set[str] = set()
        for match in ILI_PATTERN.finditer(pdf_text):
            region = match.group("region")
            if region in seen_ili_regions:
                continue
            seen_ili_regions.add(region)
            record = self._base_record(
                page_title, report_year, report_week, issue_no, source_url, pdf_url, pdf_file, raw_file
            )
            record.update(
                {
                    "week_start": week_start,
                    "week_end": week_end,
                    "region_group": region,
                    "metric_type": "ili_percent",
                    "metric_name": "ILI%",
                    "metric_percent": parse_float(match.group("ili")),
                }
            )
            records.append(record)

        if outbreak_count is not None:
            record = self._base_record(
                page_title, report_year, report_week, issue_no, source_url, pdf_url, pdf_file, raw_file
            )
            record.update(
                {
                    "week_start": week_start,
                    "week_end": week_end,
                    "region_group": "全国",
                    "metric_type": "outbreak_count",
                    "metric_name": "流感样病例暴发疫情",
                    "outbreak_count": outbreak_count,
                    "metric_value": outbreak_count,
                }
            )
            records.append(record)

        records.extend(
            self._parse_lab_rows(
                pdf_text, page_title, report_year, report_week, issue_no, source_url, pdf_url, pdf_file, raw_file,
                week_start, week_end,
            )
        )
        return records

    def _parse_lab_rows(
        self,
        pdf_text: str,
        page_title: str,
        report_year: int | None,
        report_week: int | None,
        issue_no: int | None,
        source_url: str,
        pdf_url: str,
        pdf_file: Path,
        raw_file: Path,
        week_start: str,
        week_end: str,
    ) -> list[dict]:
        records: list[dict] = []
        seen_keys: set[tuple[str, str]] = set()
        for line in pdf_text.splitlines():
            line = clean_text(line)
            match = LAB_ROW_PATTERN.match(line)
            if not match:
                continue
            metric_name = match.group("metric")
            for region_group, token in [
                ("南方省份", match.group("south")),
                ("北方省份", match.group("north")),
                ("合计", match.group("total")),
            ]:
                key = (region_group, metric_name)
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                value, percent = self._parse_count_percent_token(token)
                record = self._base_record(
                    page_title, report_year, report_week, issue_no, source_url, pdf_url, pdf_file, raw_file
                )
                record.update(
                    {
                        "week_start": week_start,
                        "week_end": week_end,
                        "region_group": region_group,
                        "metric_type": "lab_result",
                        "metric_name": metric_name,
                        "metric_value": value,
                        "metric_percent": percent,
                    }
                )
                records.append(record)
        return records

    def _download_pdf(self, pdf_url: str) -> Path:
        """下载并缓存 PDF 附件；已有缓存则直接复用。"""
        cache_path = self.cache.path_for_url(pdf_url, f"{self.raw_subdir}/pdf", default_suffix=".pdf")
        if not self.force and self.cache.has_file(cache_path):
            return cache_path
        result = self.http.fetch(pdf_url, referer=self.config.get("base_url"))
        self.cache.write_bytes(cache_path, result.content)
        self.cache.write_url(cache_path, pdf_url)
        return cache_path

    def _extract_pdf_text(self, pdf_file: Path) -> str:
        """使用系统 pdftotext 提取 PDF 文本，便于解析表格和摘要。"""
        if not pdf_file or not pdf_file.exists():
            return ""
        try:
            result = subprocess.run(
                ["pdftotext", "-layout", str(pdf_file), "-"],
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
            return result.stdout
        except Exception as exc:
            self.logger.warning("PDF 文本提取失败 %s: %s", pdf_file, exc)
            return ""

    def _find_pdf_url(self, soup, source_url: str) -> str:
        for link in soup.find_all("a"):
            href = link.get("href") or ""
            if href.lower().endswith(".pdf"):
                return urljoin(source_url, href)
        return ""

    def _parse_report_meta(self, page_title: str) -> tuple[int | None, int | None, int | None]:
        match = REPORT_PATTERN.search(page_title)
        if not match:
            return None, None, None
        return int(match.group("year")), int(match.group("week")), int(match.group("issue"))

    def _parse_week_range(self, pdf_text: str) -> tuple[str, str]:
        match = DATE_RANGE_PATTERN.search(pdf_text)
        if not match:
            return "", ""
        return (
            f"{int(match.group('start_year2')):04d}-{int(match.group('start_month')):02d}-{int(match.group('start_day')):02d}",
            f"{int(match.group('end_year')):04d}-{int(match.group('end_month')):02d}-{int(match.group('end_day')):02d}",
        )

    def _parse_dominant_subtype(self, pdf_text: str) -> str:
        normalized = re.sub(r"\s+", "", pdf_text)
        if "以B型流感病毒为主" in normalized:
            return "B型"
        if "以A(H3N2)" in normalized:
            return "A(H3N2)"
        if "以A(H1N1)pdm09" in normalized:
            return "A(H1N1)pdm09"
        return ""

    def _parse_outbreak_count(self, pdf_text: str) -> int | None:
        match = OUTBREAK_PATTERN.search(pdf_text)
        if not match:
            return None
        return parse_int(match.group("count"))

    @staticmethod
    def _parse_count_percent_token(token: str) -> tuple[int | str, float | str]:
        token = clean_text(token)
        if not token:
            return "", ""
        if "(" in token and ")" in token:
            count = token.split("(", 1)[0]
            percent = token.split("(", 1)[1].split(")", 1)[0]
            return parse_int(count) or 0, parse_float(percent) or 0.0
        value = parse_int(token)
        return (value if value is not None else "", "")
