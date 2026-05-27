import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

from crawlers.base import BaseCrawler
from parsers.html_tables import extract_page_title, extract_tables, soup_from_html
from parsers.normalizers import clean_ranked_pathogen, clean_text, parse_float


REPORT_WEEK_PATTERN = re.compile(r"(?P<year>20\d{2})年第(?P<week>\d{1,2})周")
DATE_RANGE_PATTERN = re.compile(
    r"(?P<start_year>20\d{2})年(?P<start_month>\d{1,2})月(?P<start_day>\d{1,2})日[—-]"
    r"(?:(?P<end_year>20\d{2})年)?(?P<end_month>\d{1,2})月(?P<end_day>\d{1,2})日"
)


class RespiratoryWeeklyCrawler(BaseCrawler):
    """中国疾控中心急性呼吸道传染病哨点监测周报爬虫。"""

    source_key = "respiratory_weekly"
    data_type = "respiratory_weekly"

    def discover_urls(self, limit: int | None = None) -> list[str]:
        """从周报列表页发现详情页链接。"""
        urls: list[str] = []
        seen: set[str] = set()
        start_year = int(self.config.get("start_year", 2023))
        end_year = int(self.config.get("end_year", datetime.now().year))

        for list_url in self._build_list_urls():
            try:
                html = self._read_list_page(list_url)
            except Exception as exc:
                self.logger.warning("读取周报列表页失败 %s: %s", list_url, exc)
                continue

            soup = soup_from_html(html)
            for link in soup.find_all("a"):
                title = clean_text(link.get_text(" ", strip=True))
                href = link.get("href")
                if not title or not href or "急性呼吸道传染病哨点监测" not in title:
                    continue
                match = REPORT_WEEK_PATTERN.search(title)
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
        """根据配置生成周报分页列表地址。"""
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
            report_year, report_week = self._parse_report_week(page_title, soup)
            week_start, week_end = self._parse_week_range(soup)
            source_url = self.cache.read_url(raw_file)
            tables = extract_tables(soup)

            if len(tables) >= 1:
                records.extend(
                    self._parse_pathogen_positive_rates(
                        tables[0], page_title, report_year, report_week, week_start, week_end, source_url, raw_file
                    )
                )
            if len(tables) >= 2:
                records.extend(
                    self._parse_region_rankings(
                        tables[1], page_title, report_year, report_week, week_start, week_end, source_url, raw_file
                    )
                )
            if len(tables) >= 3:
                records.extend(
                    self._parse_age_rankings(
                        tables[2], page_title, report_year, report_week, week_start, week_end, source_url, raw_file
                    )
                )
        return records

    def _base_record(
        self,
        page_title: str,
        report_year: int | None,
        report_week: int | None,
        week_start: str,
        week_end: str,
        source_url: str,
        raw_file: Path,
    ) -> dict:
        return {
            "source_name": self.source_name,
            "source_url": source_url,
            "report_title": page_title,
            "report_year": report_year,
            "report_week": report_week,
            "week_start": week_start,
            "week_end": week_end,
            "region_group": "全国",
            "age_group": "",
            "surveillance_scene": "",
            "metric_type": "",
            "pathogen_name": "",
            "positive_rate": "",
            "week_over_week_change": "",
            "rank": "",
            "ranked_pathogen": "",
            "ili_percent": "",
            "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "raw_file": str(raw_file),
        }

    def _parse_pathogen_positive_rates(
        self,
        table: list[list[str]],
        page_title: str,
        report_year: int | None,
        report_week: int | None,
        week_start: str,
        week_end: str,
        source_url: str,
        raw_file: Path,
    ) -> list[dict]:
        """解析表1：各病原体在门急诊和住院样本中的阳性率。"""
        records: list[dict] = []
        for row in table[2:]:
            if len(row) < 6:
                continue
            pathogen = clean_text(row[0])
            if not pathogen or pathogen == "病原体":
                continue
            for scene, rate_index, change_index in [
                ("门急诊流感样病例", 1, 2),
                ("住院严重急性呼吸道感染病例", 4, 5),
            ]:
                record = self._base_record(
                    page_title, report_year, report_week, week_start, week_end, source_url, raw_file
                )
                record.update(
                    {
                        "surveillance_scene": scene,
                        "metric_type": "pathogen_positive_rate",
                        "pathogen_name": pathogen,
                        "positive_rate": parse_float(row[rate_index]),
                        "week_over_week_change": parse_float(row[change_index]),
                    }
                )
                records.append(record)
        return records

    def _parse_region_rankings(
        self,
        table: list[list[str]],
        page_title: str,
        report_year: int | None,
        report_week: int | None,
        week_start: str,
        week_end: str,
        source_url: str,
        raw_file: Path,
    ) -> list[dict]:
        """解析表2：南北方省份主要病原体前三位。"""
        records: list[dict] = []
        for row in table[2:]:
            if len(row) < 8:
                continue
            region_group = clean_text(row[0])
            if not region_group:
                continue
            scenes = [
                ("门急诊流感样病例", row[1:4]),
                ("住院严重急性呼吸道感染病例", row[5:8]),
            ]
            for scene, pathogens in scenes:
                for rank, pathogen in enumerate(pathogens, start=1):
                    ranked_pathogen = clean_ranked_pathogen(pathogen)
                    if not ranked_pathogen:
                        continue
                    record = self._base_record(
                        page_title, report_year, report_week, week_start, week_end, source_url, raw_file
                    )
                    record.update(
                        {
                            "region_group": region_group,
                            "surveillance_scene": scene,
                            "metric_type": "region_top_pathogen",
                            "rank": rank,
                            "ranked_pathogen": ranked_pathogen,
                        }
                    )
                    records.append(record)
        return records

    def _parse_age_rankings(
        self,
        table: list[list[str]],
        page_title: str,
        report_year: int | None,
        report_week: int | None,
        week_start: str,
        week_end: str,
        source_url: str,
        raw_file: Path,
    ) -> list[dict]:
        """解析表3：不同年龄组主要病原体前三位。"""
        records: list[dict] = []
        current_age_group = ""
        rank_by_age_scene: dict[tuple[str, str], int] = {}
        for row in table[1:]:
            if len(row) < 4:
                continue
            age_group = clean_text(row[0]) or current_age_group
            if age_group:
                current_age_group = age_group
            if not current_age_group:
                continue

            if clean_text(row[0]):
                outpatient_value = row[2] if len(row) > 2 else ""
                inpatient_value = row[4] if len(row) > 4 else ""
            else:
                # 表3使用跨行结构：第二、第三名所在行的年龄组单元格为空，
                # 病原体名称会左移到第2列和第4列。
                outpatient_value = row[1] if len(row) > 1 else ""
                inpatient_value = row[3] if len(row) > 3 else ""

            scene_values = [
                ("门急诊流感样病例", outpatient_value),
                ("住院严重急性呼吸道感染病例", inpatient_value),
            ]
            for scene, pathogen_text in scene_values:
                ranked_pathogen = clean_ranked_pathogen(pathogen_text)
                if not ranked_pathogen:
                    continue
                key = (current_age_group, scene)
                rank_by_age_scene[key] = rank_by_age_scene.get(key, 0) + 1
                record = self._base_record(
                    page_title, report_year, report_week, week_start, week_end, source_url, raw_file
                )
                record.update(
                    {
                        "age_group": current_age_group,
                        "surveillance_scene": scene,
                        "metric_type": "age_top_pathogen",
                        "rank": rank_by_age_scene[key],
                        "ranked_pathogen": ranked_pathogen,
                    }
                )
                records.append(record)
        return records

    def _parse_report_week(self, page_title: str, soup) -> tuple[int | None, int | None]:
        text = page_title or soup.get_text(" ", strip=True)
        match = REPORT_WEEK_PATTERN.search(text)
        if not match:
            return None, None
        return int(match.group("year")), int(match.group("week"))

    def _parse_week_range(self, soup) -> tuple[str, str]:
        text = soup.get_text(" ", strip=True)
        match = DATE_RANGE_PATTERN.search(text)
        if not match:
            return "", ""
        start_year = int(match.group("start_year"))
        start_month = int(match.group("start_month"))
        start_day = int(match.group("start_day"))
        end_year = int(match.group("end_year") or start_year)
        end_month = int(match.group("end_month"))
        end_day = int(match.group("end_day"))
        return (
            f"{start_year:04d}-{start_month:02d}-{start_day:02d}",
            f"{end_year:04d}-{end_month:02d}-{end_day:02d}",
        )
