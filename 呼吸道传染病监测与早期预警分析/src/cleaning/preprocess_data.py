"""成员 B 数据清洗与预处理脚本。

本脚本只处理本地已经采集到的 CSV 文件，不发起网络请求。主要目标是把
`data/interim/` 中格式相对原始的中间表，转换为适合统计分析、预警建模
和可视化展示的标准化数据表。

设计原则：
1. 只使用 Python 标准库，避免额外安装依赖。
2. 每个数据源单独清洗，规则集中在对应的 `clean_*` 函数中，便于维护。
3. 输出质量摘要和数据字典，方便报告撰写与人工审核。
"""

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

# 脚本位于 `src/cleaning/` 下。直接执行该文件时，Python 默认只把
# `src/cleaning/` 加入导入路径；这里显式加入上一级 `src/`，保证可以复用
# 项目已有的 `utils.paths` 路径配置。
SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from utils.paths import INTERIM_DIR, LOG_DIR, PROCESSED_DIR, ensure_project_dirs


# 项目原始表中常见的空值写法。统一为空字符串，便于后续统计缺失值。
MISSING_VALUES = {"", "-", "--", "—", "NA", "N/A", "null", "None", "nan"}

# 期末项目重点关注的呼吸道相关病种，用于在月报中打标。
RESPIRATORY_DISEASES = {
    "新型冠状病毒感染",
    "流行性感冒",
    "肺结核",
    "百日咳",
    "麻疹",
    "猩红热",
    "流行性腮腺炎",
}

# 病种名称可能来自不同来源或不同表述，这里做最小必要的标准化。
DISEASE_ALIASES = {
    "新型冠状病毒感染": "新型冠状病毒感染",
    "新冠病毒感染": "新型冠状病毒感染",
    "COVID-19": "新型冠状病毒感染",
    "流行性感冒": "流行性感冒",
    "流感": "流行性感冒",
}

# 病原体名称标准化映射，保证周报特征列名称稳定。
PATHOGEN_ALIASES = {
    "新型冠状病毒": "新型冠状病毒",
    "新冠病毒": "新型冠状病毒",
    "SARS-CoV-2": "新型冠状病毒",
    "流感病毒": "流感病毒",
    "呼吸道合胞病毒": "呼吸道合胞病毒",
    "肺炎支原体": "肺炎支原体",
    "腺病毒": "腺病毒",
    "人偏肺病毒": "人偏肺病毒",
    "副流感病毒": "副流感病毒",
    "普通冠状病毒": "普通冠状病毒",
    "博卡病毒": "博卡病毒",
    "鼻病毒": "鼻病毒",
}

# 生成建模特征列时使用的英文短名，避免 CSV 表头中出现过长中文字段。
PATHOGEN_FEATURE_NAMES = {
    "新型冠状病毒": "covid",
    "流感病毒": "influenza",
    "呼吸道合胞病毒": "rsv",
    "肺炎支原体": "mycoplasma",
    "腺病毒": "adenovirus",
    "人偏肺病毒": "hmpv",
    "副流感病毒": "parainfluenza",
    "普通冠状病毒": "common_coronavirus",
    "博卡病毒": "bocavirus",
    "鼻病毒": "rhinovirus",
}

# 两类急性呼吸道哨点监测场景，对应门急诊和住院病例。
SCENE_FEATURE_NAMES = {
    "门急诊流感样病例": "outpatient_ili",
    "住院严重急性呼吸道感染病例": "hospital_sari",
}


def clean_text(value: object) -> str:
    """清理单元格文本，统一处理空白和常见空值。

    CSV 中的值可能包含换行、连续空格、全角空格或缺失值占位符。所有清洗
    函数都先调用本函数，避免各处重复写空值判断。
    """
    if value is None:
        return ""
    text = re.sub(r"\s+", " ", str(value)).strip()
    return "" if text in MISSING_VALUES else text


def parse_int(value: object) -> Optional[int]:
    """将含逗号或中文符号的整数文本转换为 int。

    例如 `"1,234"`、`"1234例"` 会被转换为 `1234`。无法解析时返回
    `None`，由调用方决定是否保留为空值。
    """
    text = clean_text(value).replace(",", "")
    if not text:
        return None
    text = re.sub(r"[^0-9\-]", "", text)
    if text in {"", "-"}:
        return None
    return int(text)


def parse_float(value: object) -> Optional[float]:
    """将比例、温度、降水等小数字段转换为 float。

    函数会移除百分号和非数字符号，但保留负号与小数点，适合处理阳性率、
    气温、湿度等指标。
    """
    text = clean_text(value).replace(",", "").replace("%", "")
    if not text:
        return None
    text = re.sub(r"[^0-9.\-]", "", text)
    if text in {"", "-", ".", "-."}:
        return None
    return float(text)


def parse_date(value: object) -> str:
    """统一日期格式为 YYYY-MM-DD。

    当前数据中主要是 `YYYY-MM-DD`，这里额外兼容 `YYYY/MM/DD` 和
    `YYYYMMDD`，便于后续扩展其他数据源。
    """
    text = clean_text(value)
    if not text:
        return ""
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return text


def iso_week_start(year: int, week: int) -> str:
    """根据 ISO 年和周数计算该周周一日期。"""
    return date.fromisocalendar(year, week, 1).isoformat()


def iso_week_end(year: int, week: int) -> str:
    """根据 ISO 年和周数计算该周周日日期。"""
    return (date.fromisocalendar(year, week, 1) + timedelta(days=6)).isoformat()


def normalize_disease(value: object) -> str:
    """标准化病种名称，减少同义写法对分析结果的影响。"""
    text = clean_text(value)
    text = re.sub(r"[\s\u3000]+", "", text)
    return DISEASE_ALIASES.get(text, text)


def normalize_pathogen(value: object) -> str:
    """标准化病原体名称，保证同一病原体聚合到同一类。"""
    text = clean_text(value)
    text = re.sub(r"[\s\u3000]+", "", text)
    return PATHOGEN_ALIASES.get(text, text)


def normalize_region(value: object) -> str:
    """标准化地区名称，目前主要移除多余空格。"""
    text = clean_text(value)
    return text.replace(" ", "")


def format_number(value: Optional[float], digits: int = 4) -> str:
    """将数值转换为适合写入 CSV 的简洁文本。

    整数值不保留 `.0`，小数最多保留 `digits` 位，空值返回空字符串。
    """
    if value is None:
        return ""
    rounded = round(value, digits)
    if rounded == int(rounded):
        return str(int(rounded))
    return str(rounded)


def read_csv(path: Path) -> List[Dict[str, str]]:
    """读取 UTF-8 CSV，并对每个单元格做基础文本清理。"""
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return [{key: clean_text(value) for key, value in row.items()} for row in reader]


def write_csv(path: Path, rows: Sequence[Dict[str, object]], fieldnames: Sequence[str]) -> None:
    """按照指定字段顺序写出 CSV。

    使用 `utf-8-sig` 是为了兼容 Excel 直接打开中文 CSV 时的编码识别。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def deduplicate(
    rows: Iterable[Dict[str, object]], key_fields: Sequence[str]
) -> Tuple[List[Dict[str, object]], int]:
    """基于业务主键去重，并返回去重后的记录和删除数量。"""
    seen = set()
    clean_rows = []
    duplicate_count = 0
    for row in rows:
        key = tuple(row.get(field, "") for field in key_fields)
        if key in seen:
            duplicate_count += 1
            continue
        seen.add(key)
        clean_rows.append(row)
    return clean_rows, duplicate_count


def missing_count(rows: Sequence[Dict[str, object]]) -> Dict[str, int]:
    """统计每个字段中的空值数量，用于生成质量摘要。"""
    counts: Dict[str, int] = defaultdict(int)
    for row in rows:
        for field, value in row.items():
            if value in (None, ""):
                counts[field] += 1
    return dict(sorted(counts.items()))


def clean_chinacdc_monthly(rows: Sequence[Dict[str, str]]) -> Tuple[List[Dict[str, object]], int]:
    """清洗中国疾控法定传染病月报数据。

    重点处理内容包括：年月字段、病种名称、病例数、死亡数和呼吸道重点
    病种标记。该表用于后续月度趋势和重点病种分析。
    """
    cleaned = []
    for row in rows:
        report_year = parse_int(row.get("report_year"))
        report_month = parse_int(row.get("report_month"))
        disease_name = normalize_disease(row.get("disease_name"))
        cases = parse_int(row.get("cases"))
        deaths = parse_int(row.get("deaths"))
        incidence_rate = parse_float(row.get("incidence_rate"))
        mortality_rate = parse_float(row.get("mortality_rate"))
        period_month = ""
        if report_year and report_month:
            period_month = f"{report_year:04d}-{report_month:02d}"
        is_total_row = any(token in disease_name for token in ("总计", "合计"))
        cleaned.append(
            {
                "source_name": clean_text(row.get("source_name")),
                "source_url": clean_text(row.get("source_url")),
                "report_title": clean_text(row.get("report_title")),
                "report_year": report_year or "",
                "report_month": report_month or "",
                "period_month": period_month,
                "region": normalize_region(row.get("region")) or "全国",
                "disease_name": disease_name,
                "disease_category": clean_text(row.get("disease_category")),
                "is_respiratory_focus": "1" if disease_name in RESPIRATORY_DISEASES else "0",
                "is_total_row": "1" if is_total_row else "0",
                "cases": cases if cases is not None else "",
                "deaths": deaths if deaths is not None else "",
                "incidence_rate": format_number(incidence_rate),
                "mortality_rate": format_number(mortality_rate),
                "crawl_time": clean_text(row.get("crawl_time")),
                "raw_file": clean_text(row.get("raw_file")),
            }
        )
    return deduplicate(cleaned, ["report_year", "report_month", "region", "disease_name"])


def clean_respiratory_weekly(rows: Sequence[Dict[str, str]]) -> Tuple[List[Dict[str, object]], int]:
    """清洗急性呼吸道传染病哨点周报数据。

    该表包含病原体阳性率、环比变化、不同监测场景和排名信息。清洗后会
    生成统一的 `year_week` 字段，方便与气象周度数据对齐。
    """
    cleaned = []
    for row in rows:
        report_year = parse_int(row.get("report_year"))
        report_week = parse_int(row.get("report_week"))
        week_start = parse_date(row.get("week_start"))
        week_end = parse_date(row.get("week_end"))
        if report_year and report_week and not week_start:
            week_start = iso_week_start(report_year, report_week)
            week_end = iso_week_end(report_year, report_week)
        year_week = f"{report_year:04d}-W{report_week:02d}" if report_year and report_week else ""
        week_over_week_change = parse_float(row.get("week_over_week_change"))
        pathogen_name = normalize_pathogen(row.get("pathogen_name"))
        ranked_pathogen = normalize_pathogen(row.get("ranked_pathogen"))
        cleaned.append(
            {
                "source_name": clean_text(row.get("source_name")),
                "source_url": clean_text(row.get("source_url")),
                "report_title": clean_text(row.get("report_title")),
                "report_year": report_year or "",
                "report_week": report_week or "",
                "year_week": year_week,
                "week_start": week_start,
                "week_end": week_end,
                "region_group": normalize_region(row.get("region_group")) or "全国",
                "age_group": clean_text(row.get("age_group")),
                "surveillance_scene": clean_text(row.get("surveillance_scene")),
                "metric_type": clean_text(row.get("metric_type")),
                "pathogen_name": pathogen_name,
                "positive_rate": format_number(parse_float(row.get("positive_rate"))),
                "week_over_week_change": format_number(week_over_week_change),
                "rank": parse_int(row.get("rank")) or "",
                "ranked_pathogen": ranked_pathogen,
                "crawl_time": clean_text(row.get("crawl_time")),
                "raw_file": clean_text(row.get("raw_file")),
            }
        )
    return deduplicate(
        cleaned,
        [
            "report_year",
            "report_week",
            "region_group",
            "age_group",
            "surveillance_scene",
            "metric_type",
            "pathogen_name",
            "rank",
            "ranked_pathogen",
        ],
    )


def clean_influenza_weekly(rows: Sequence[Dict[str, str]]) -> Tuple[List[Dict[str, object]], int]:
    """清洗流感监测周报数据。

    流感周报中同时存在百分比、检测数、优势毒株和暴发疫情数。本函数新增
    `indicator_value`，方便后续按统一数值字段做统计和可视化。
    """
    cleaned = []
    for row in rows:
        report_year = parse_int(row.get("report_year"))
        report_week = parse_int(row.get("report_week"))
        week_start = parse_date(row.get("week_start"))
        week_end = parse_date(row.get("week_end"))
        if report_year and report_week and not week_start:
            week_start = iso_week_start(report_year, report_week)
            week_end = iso_week_end(report_year, report_week)
        year_week = f"{report_year:04d}-W{report_week:02d}" if report_year and report_week else ""
        metric_value = parse_float(row.get("metric_value"))
        metric_percent = parse_float(row.get("metric_percent"))
        outbreak_count = parse_int(row.get("outbreak_count"))
        indicator_value: Optional[float] = None
        if metric_percent is not None:
            indicator_value = metric_percent
        elif metric_value is not None:
            indicator_value = metric_value
        elif outbreak_count is not None:
            indicator_value = float(outbreak_count)
        cleaned.append(
            {
                "source_name": clean_text(row.get("source_name")),
                "source_url": clean_text(row.get("source_url")),
                "pdf_url": clean_text(row.get("pdf_url")),
                "report_title": clean_text(row.get("report_title")),
                "report_year": report_year or "",
                "report_week": report_week or "",
                "year_week": year_week,
                "issue_no": parse_int(row.get("issue_no")) or "",
                "week_start": week_start,
                "week_end": week_end,
                "region_group": normalize_region(row.get("region_group")) or "全国",
                "metric_type": clean_text(row.get("metric_type")),
                "metric_name": clean_text(row.get("metric_name")),
                "metric_value": format_number(metric_value),
                "metric_percent": format_number(metric_percent),
                "dominant_subtype": clean_text(row.get("dominant_subtype")),
                "outbreak_count": outbreak_count if outbreak_count is not None else "",
                "indicator_value": format_number(indicator_value),
                "crawl_time": clean_text(row.get("crawl_time")),
                "raw_file": clean_text(row.get("raw_file")),
                "pdf_file": clean_text(row.get("pdf_file")),
            }
        )
    return deduplicate(
        cleaned,
        [
            "report_year",
            "report_week",
            "region_group",
            "metric_type",
            "metric_name",
            "dominant_subtype",
        ],
    )


def clean_weather_daily(rows: Sequence[Dict[str, str]]) -> Tuple[List[Dict[str, object]], int]:
    """清洗日度气象数据，并补充周度、月度时间字段。

    气象数据来自 NASA POWER，原始粒度为城市日度。后续会在此基础上聚合
    为周度和月度数据，与疾控周报、月报保持时间粒度一致。
    """
    cleaned = []
    for row in rows:
        observation_date = parse_date(row.get("observation_date"))
        report_year = ""
        report_week = ""
        period_month = ""
        if observation_date:
            parsed_date = date.fromisoformat(observation_date)
            iso_year, iso_week, _ = parsed_date.isocalendar()
            report_year = iso_year
            report_week = iso_week
            period_month = observation_date[:7]
        year_week = f"{report_year:04d}-W{report_week:02d}" if report_year and report_week else ""
        week_start = iso_week_start(report_year, report_week) if report_year and report_week else ""
        week_end = iso_week_end(report_year, report_week) if report_year and report_week else ""
        cleaned.append(
            {
                "source_name": clean_text(row.get("source_name")),
                "source_url": clean_text(row.get("source_url")),
                "observation_date": observation_date,
                "period_month": period_month,
                "report_year": report_year,
                "report_week": report_week,
                "year_week": year_week,
                "week_start": week_start,
                "week_end": week_end,
                "region": normalize_region(row.get("region")),
                "city": clean_text(row.get("city")),
                "latitude": format_number(parse_float(row.get("latitude")), 6),
                "longitude": format_number(parse_float(row.get("longitude")), 6),
                "avg_temperature": format_number(parse_float(row.get("avg_temperature"))),
                "max_temperature": format_number(parse_float(row.get("max_temperature"))),
                "min_temperature": format_number(parse_float(row.get("min_temperature"))),
                "avg_humidity": format_number(parse_float(row.get("avg_humidity"))),
                "precipitation": format_number(parse_float(row.get("precipitation"))),
                "wind_speed": format_number(parse_float(row.get("wind_speed"))),
                "crawl_time": clean_text(row.get("crawl_time")),
                "raw_file": clean_text(row.get("raw_file")),
            }
        )
    return deduplicate(cleaned, ["observation_date", "region", "city"])


def average(values: Iterable[object]) -> Optional[float]:
    """计算非空数值的平均值。"""
    numbers = [parse_float(value) for value in values]
    numbers = [value for value in numbers if value is not None]
    if not numbers:
        return None
    return sum(numbers) / len(numbers)


def total(values: Iterable[object]) -> Optional[float]:
    """计算非空数值的总和。"""
    numbers = [parse_float(value) for value in values]
    numbers = [value for value in numbers if value is not None]
    if not numbers:
        return None
    return sum(numbers)


def aggregate_weather_weekly(rows: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
    """将城市日度气象数据聚合为城市周度气象数据。"""
    groups: Dict[Tuple[object, object, object, object], List[Dict[str, object]]] = defaultdict(list)
    for row in rows:
        key = (row["region"], row["city"], row["report_year"], row["report_week"])
        groups[key].append(row)

    aggregated = []
    for (region, city, report_year, report_week), items in sorted(groups.items()):
        avg_temperature = average(item["avg_temperature"] for item in items)
        max_temperature = average(item["max_temperature"] for item in items)
        min_temperature = average(item["min_temperature"] for item in items)
        avg_humidity = average(item["avg_humidity"] for item in items)
        precipitation_total = total(item["precipitation"] for item in items)
        wind_speed = average(item["wind_speed"] for item in items)
        aggregated.append(
            {
                "region": region,
                "city": city,
                "report_year": report_year,
                "report_week": report_week,
                "year_week": f"{int(report_year):04d}-W{int(report_week):02d}",
                "week_start": items[0]["week_start"],
                "week_end": items[0]["week_end"],
                "days_count": len(items),
                "avg_temperature": format_number(avg_temperature),
                "max_temperature": format_number(max_temperature),
                "min_temperature": format_number(min_temperature),
                "avg_humidity": format_number(avg_humidity),
                "precipitation_total": format_number(precipitation_total),
                "wind_speed": format_number(wind_speed),
            }
        )
    return aggregated


def aggregate_weather_monthly(rows: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
    """将城市日度气象数据聚合为城市月度气象数据。"""
    groups: Dict[Tuple[object, object, object], List[Dict[str, object]]] = defaultdict(list)
    for row in rows:
        key = (row["region"], row["city"], row["period_month"])
        groups[key].append(row)

    aggregated = []
    for (region, city, period_month), items in sorted(groups.items()):
        avg_temperature = average(item["avg_temperature"] for item in items)
        max_temperature = average(item["max_temperature"] for item in items)
        min_temperature = average(item["min_temperature"] for item in items)
        avg_humidity = average(item["avg_humidity"] for item in items)
        precipitation_total = total(item["precipitation"] for item in items)
        wind_speed = average(item["wind_speed"] for item in items)
        aggregated.append(
            {
                "region": region,
                "city": city,
                "period_month": period_month,
                "days_count": len(items),
                "avg_temperature": format_number(avg_temperature),
                "max_temperature": format_number(max_temperature),
                "min_temperature": format_number(min_temperature),
                "avg_humidity": format_number(avg_humidity),
                "precipitation_total": format_number(precipitation_total),
                "wind_speed": format_number(wind_speed),
            }
        )
    return aggregated


def build_weekly_health_features(
    respiratory_rows: Sequence[Dict[str, object]], influenza_rows: Sequence[Dict[str, object]]
) -> Dict[Tuple[object, object], Dict[str, object]]:
    """从周报数据中提取可合并到周度特征表的全国健康监测指标。

    当前疾控周报和流感周报主要是全国或南北方分组指标，没有省级病例数。
    因此这里将全国周度健康指标按周合并到每个城市的周度气象行上，形成
    可供可视化和初步相关性分析使用的宽表。
    """
    features: Dict[Tuple[object, object], Dict[str, object]] = defaultdict(dict)

    for row in respiratory_rows:
        if row.get("metric_type") != "pathogen_positive_rate":
            continue
        pathogen = row.get("pathogen_name")
        scene = row.get("surveillance_scene")
        pathogen_key = PATHOGEN_FEATURE_NAMES.get(str(pathogen))
        scene_key = SCENE_FEATURE_NAMES.get(str(scene))
        if not pathogen_key or not scene_key:
            continue
        key = (row.get("report_year"), row.get("report_week"))
        feature_name = f"resp_{scene_key}_{pathogen_key}_positive_rate"
        features[key][feature_name] = row.get("positive_rate", "")

    for row in influenza_rows:
        key = (row.get("report_year"), row.get("report_week"))
        region_group = row.get("region_group")
        metric_type = row.get("metric_type")
        if metric_type == "ili_percent" and region_group in {"南方省份", "北方省份"}:
            suffix = "south" if region_group == "南方省份" else "north"
            features[key][f"influenza_ili_percent_{suffix}"] = row.get("metric_percent", "")
        elif metric_type == "outbreak_count":
            features[key]["influenza_outbreak_count"] = row.get("outbreak_count", "")
        elif metric_type == "summary" and row.get("dominant_subtype"):
            features[key]["influenza_dominant_subtype"] = row.get("dominant_subtype", "")

    return features


def build_province_weekly_features(
    weather_weekly: Sequence[Dict[str, object]],
    respiratory_rows: Sequence[Dict[str, object]],
    influenza_rows: Sequence[Dict[str, object]],
) -> List[Dict[str, object]]:
    """合并周度气象特征和周度健康监测特征。"""
    health_features = build_weekly_health_features(respiratory_rows, influenza_rows)
    rows = []
    for weather_row in weather_weekly:
        key = (weather_row.get("report_year"), weather_row.get("report_week"))
        row = dict(weather_row)
        row.update(health_features.get(key, {}))
        rows.append(row)
    return rows


def build_dictionary_rows() -> List[Dict[str, str]]:
    """生成完整数据字典。

    数据字典覆盖每张清洗后表的字段含义、数据类型、单位、缺失值处理方式和
    来源字段对应关系，便于成员 B 写报告，也便于成员 C 接入可视化数据。
    """

    rows: List[Dict[str, str]] = []

    def add(
        table_name: str,
        field_name: str,
        data_type: str,
        unit: str,
        missing_value_strategy: str,
        source_field: str,
        description: str,
    ) -> None:
        rows.append(
            {
                "table_name": table_name,
                "field_name": field_name,
                "data_type": data_type,
                "unit": unit,
                "missing_value_strategy": missing_value_strategy,
                "source_field": source_field,
                "description": description,
            }
        )

    # 1. 法定传染病月报清洗表。
    table = "chinacdc_monthly_clean.csv"
    add(table, "source_name", "string", "-", "保留为空并回查采集记录", "source_name", "数据源名称。")
    add(table, "source_url", "string", "-", "关键追溯字段，原则上不可为空", "source_url", "原始网页链接。")
    add(table, "report_title", "string", "-", "保留为空并回查原始网页", "report_title", "报告标题。")
    add(table, "report_year", "integer", "年", "关键时间字段，原则上不可为空", "report_year", "报告年份。")
    add(table, "report_month", "integer", "月", "关键时间字段，原则上不可为空", "report_month", "报告月份。")
    add(
        table,
        "period_month",
        "string",
        "-",
        "由年月派生，缺失时回查年月字段",
        "report_year + report_month",
        "报告年月，格式为 YYYY-MM。",
    )
    add(table, "region", "string", "-", "缺失时默认回查来源，当前为全国", "region", "地区名称。")
    add(table, "disease_name", "string", "-", "核心字段，缺失时回查原始表格", "disease_name", "标准化后的病种名称。")
    add(table, "disease_category", "string", "-", "保留为空，不做填补", "disease_category", "病种类别或合计类别。")
    add(
        table,
        "is_respiratory_focus",
        "integer",
        "0/1",
        "由病种名称派生，不手工填补",
        "disease_name",
        "是否为呼吸道重点病种。",
    )
    add(table, "is_total_row", "integer", "0/1", "由病种名称派生，不手工填补", "disease_name", "是否为总计或合计行。")
    add(table, "cases", "integer", "例", "保留为空并在分析时排除", "cases", "发病数。")
    add(table, "deaths", "integer", "人", "保留为空并在分析时排除", "deaths", "死亡数。")
    add(table, "incidence_rate", "float", "1/10万或源表口径", "源数据未提供时保留为空", "incidence_rate", "发病率。")
    add(table, "mortality_rate", "float", "1/10万或源表口径", "源数据未提供时保留为空", "mortality_rate", "死亡率。")
    add(table, "crawl_time", "datetime", "-", "保留为空并回查运行日志", "crawl_time", "采集或解析时间。")
    add(table, "raw_file", "string", "-", "保留为空并回查缓存目录", "raw_file", "原始缓存文件路径。")

    # 2. 急性呼吸道哨点周报清洗表。
    table = "respiratory_weekly_clean.csv"
    add(table, "source_name", "string", "-", "保留为空并回查采集记录", "source_name", "数据源名称。")
    add(table, "source_url", "string", "-", "关键追溯字段，原则上不可为空", "source_url", "原始网页链接。")
    add(table, "report_title", "string", "-", "保留为空并回查原始网页", "report_title", "报告标题。")
    add(table, "report_year", "integer", "年", "关键时间字段，原则上不可为空", "report_year", "报告年份。")
    add(table, "report_week", "integer", "周", "关键时间字段，原则上不可为空", "report_week", "报告周次。")
    add(
        table,
        "year_week",
        "string",
        "-",
        "由年份和周次派生",
        "report_year + report_week",
        "ISO 周标识，格式为 YYYY-Www。",
    )
    add(table, "week_start", "date", "-", "缺失时由年份和周次推算", "week_start", "周起始日期。")
    add(table, "week_end", "date", "-", "缺失时由年份和周次推算", "week_end", "周结束日期。")
    add(
        table,
        "region_group",
        "string",
        "-",
        "缺失时保留为空或回查原文",
        "region_group",
        "地区分组，如全国、南方省份、北方省份。",
    )
    add(table, "age_group", "string", "-", "字段不适用时保留为空", "age_group", "年龄组，仅年龄组排名记录适用。")
    add(table, "surveillance_scene", "string", "-", "字段不适用时保留为空", "surveillance_scene", "监测场景。")
    add(table, "metric_type", "string", "-", "核心分类字段，原则上不可为空", "metric_type", "指标类型。")
    add(table, "pathogen_name", "string", "-", "排名类记录不适用时保留为空", "pathogen_name", "标准化病原体名称。")
    add(table, "positive_rate", "float", "%", "排名类记录不适用时保留为空", "positive_rate", "病原体阳性率。")
    add(
        table,
        "week_over_week_change",
        "float",
        "百分点",
        "排名类记录不适用时保留为空",
        "week_over_week_change",
        "环比变化。",
    )
    add(table, "rank", "integer", "名", "阳性率记录不适用时保留为空", "rank", "病原体排名。")
    add(table, "ranked_pathogen", "string", "-", "阳性率记录不适用时保留为空", "ranked_pathogen", "排名记录中的病原体名称。")
    add(table, "crawl_time", "datetime", "-", "保留为空并回查运行日志", "crawl_time", "采集或解析时间。")
    add(table, "raw_file", "string", "-", "保留为空并回查缓存目录", "raw_file", "原始缓存文件路径。")

    # 3. 流感监测周报清洗表。
    table = "influenza_weekly_clean.csv"
    add(table, "source_name", "string", "-", "保留为空并回查采集记录", "source_name", "数据源名称。")
    add(table, "source_url", "string", "-", "关键追溯字段，原则上不可为空", "source_url", "原始网页链接。")
    add(table, "pdf_url", "string", "-", "无 PDF 附件时保留为空", "pdf_url", "PDF 附件链接。")
    add(table, "report_title", "string", "-", "保留为空并回查原始网页", "report_title", "报告标题。")
    add(table, "report_year", "integer", "年", "关键时间字段，原则上不可为空", "report_year", "报告年份。")
    add(table, "report_week", "integer", "周", "关键时间字段，原则上不可为空", "report_week", "报告周次。")
    add(table, "year_week", "string", "-", "由年份和周次派生", "report_year + report_week", "ISO 周标识。")
    add(table, "issue_no", "integer", "期", "缺失时保留为空", "issue_no", "周报期号。")
    add(table, "week_start", "date", "-", "缺失时由年份和周次推算", "week_start", "周起始日期。")
    add(table, "week_end", "date", "-", "缺失时由年份和周次推算", "week_end", "周结束日期。")
    add(table, "region_group", "string", "-", "缺失时保留为空或回查原文", "region_group", "地区分组。")
    add(table, "metric_type", "string", "-", "核心分类字段，原则上不可为空", "metric_type", "指标类型。")
    add(table, "metric_name", "string", "-", "摘要类记录不适用时保留为空", "metric_name", "具体指标名称。")
    add(table, "metric_value", "float", "份/例/起", "百分比或摘要类记录不适用时保留为空", "metric_value", "普通数值指标。")
    add(table, "metric_percent", "float", "%", "数量或摘要类记录不适用时保留为空", "metric_percent", "百分比指标。")
    add(table, "dominant_subtype", "string", "-", "非摘要类记录不适用时保留为空", "dominant_subtype", "优势流感亚型。")
    add(table, "outbreak_count", "integer", "起", "非暴发疫情记录不适用时保留为空", "outbreak_count", "流感样病例暴发疫情数。")
    add(
        table,
        "indicator_value",
        "float",
        "按指标类型",
        "无法数值化时保留为空",
        "metric_value/metric_percent/outbreak_count",
        "统一指标值。",
    )
    add(table, "crawl_time", "datetime", "-", "保留为空并回查运行日志", "crawl_time", "采集或解析时间。")
    add(table, "raw_file", "string", "-", "保留为空并回查缓存目录", "raw_file", "HTML 原始缓存文件路径。")
    add(table, "pdf_file", "string", "-", "无 PDF 附件时保留为空", "pdf_file", "PDF 原始缓存文件路径。")

    # 4. 日度气象清洗表。
    table = "weather_daily_clean.csv"
    add(table, "source_name", "string", "-", "保留为空并回查采集记录", "source_name", "数据源名称。")
    add(table, "source_url", "string", "-", "关键追溯字段，原则上不可为空", "source_url", "NASA POWER API 请求链接。")
    add(table, "observation_date", "date", "-", "关键时间字段，原则上不可为空", "observation_date", "气象观测日期。")
    add(table, "period_month", "string", "-", "由观测日期派生", "observation_date", "观测月份，格式为 YYYY-MM。")
    add(table, "report_year", "integer", "年", "由观测日期派生", "observation_date", "ISO 周所属年份。")
    add(table, "report_week", "integer", "周", "由观测日期派生", "observation_date", "ISO 周次。")
    add(table, "year_week", "string", "-", "由观测日期派生", "observation_date", "ISO 周标识。")
    add(table, "week_start", "date", "-", "由观测日期派生", "observation_date", "周起始日期。")
    add(table, "week_end", "date", "-", "由观测日期派生", "observation_date", "周结束日期。")
    add(table, "region", "string", "-", "核心地区字段，原则上不可为空", "region", "省级行政区名称。")
    add(table, "city", "string", "-", "核心地区字段，原则上不可为空", "city", "省会或首府城市名称。")
    add(table, "latitude", "float", "度", "保留为空并回查城市配置", "latitude", "城市纬度。")
    add(table, "longitude", "float", "度", "保留为空并回查城市配置", "longitude", "城市经度。")
    add(table, "avg_temperature", "float", "摄氏度", "API 缺测时保留为空", "avg_temperature", "日平均气温。")
    add(table, "max_temperature", "float", "摄氏度", "API 缺测时保留为空", "max_temperature", "日最高气温。")
    add(table, "min_temperature", "float", "摄氏度", "API 缺测时保留为空", "min_temperature", "日最低气温。")
    add(table, "avg_humidity", "float", "%", "API 缺测时保留为空", "avg_humidity", "日平均相对湿度。")
    add(table, "precipitation", "float", "毫米", "API 缺测时保留为空", "precipitation", "日降水量。")
    add(table, "wind_speed", "float", "米/秒", "API 缺测时保留为空", "wind_speed", "日平均风速。")
    add(table, "crawl_time", "datetime", "-", "保留为空并回查运行日志", "crawl_time", "采集或解析时间。")
    add(table, "raw_file", "string", "-", "保留为空并回查缓存目录", "raw_file", "原始 JSON 缓存文件路径。")

    # 5. 气象聚合表和省份周度特征表的公共字段。
    weekly_common = [
        ("region", "string", "-", "继承周度气象表", "region", "省级行政区名称。"),
        ("city", "string", "-", "继承周度气象表", "city", "省会或首府城市名称。"),
        ("report_year", "integer", "年", "由日度气象日期派生", "report_year", "ISO 周所属年份。"),
        ("report_week", "integer", "周", "由日度气象日期派生", "report_week", "ISO 周次。"),
        ("year_week", "string", "-", "由年份和周次派生", "year_week", "ISO 周标识。"),
        ("week_start", "date", "-", "由日度气象日期派生", "week_start", "周起始日期。"),
        ("week_end", "date", "-", "由日度气象日期派生", "week_end", "周结束日期。"),
        ("days_count", "integer", "天", "聚合结果字段，原则上不可为空", "observation_date", "参与聚合的日数。"),
        ("avg_temperature", "float", "摄氏度", "忽略空值后求平均", "avg_temperature", "周平均气温。"),
        ("max_temperature", "float", "摄氏度", "忽略空值后求平均", "max_temperature", "周平均最高气温。"),
        ("min_temperature", "float", "摄氏度", "忽略空值后求平均", "min_temperature", "周平均最低气温。"),
        ("avg_humidity", "float", "%", "忽略空值后求平均", "avg_humidity", "周平均相对湿度。"),
        ("precipitation_total", "float", "毫米", "忽略空值后求和", "precipitation", "周累计降水量。"),
        ("wind_speed", "float", "米/秒", "忽略空值后求平均", "wind_speed", "周平均风速。"),
    ]
    for field in weekly_common:
        add("weather_weekly.csv", *field)
        add("province_weekly_features.csv", *field)

    monthly_common = [
        ("region", "string", "-", "继承日度气象表", "region", "省级行政区名称。"),
        ("city", "string", "-", "继承日度气象表", "city", "省会或首府城市名称。"),
        ("period_month", "string", "-", "由观测日期派生", "period_month", "观测月份，格式为 YYYY-MM。"),
        ("days_count", "integer", "天", "聚合结果字段，原则上不可为空", "observation_date", "参与聚合的日数。"),
        ("avg_temperature", "float", "摄氏度", "忽略空值后求平均", "avg_temperature", "月平均气温。"),
        ("max_temperature", "float", "摄氏度", "忽略空值后求平均", "max_temperature", "月平均最高气温。"),
        ("min_temperature", "float", "摄氏度", "忽略空值后求平均", "min_temperature", "月平均最低气温。"),
        ("avg_humidity", "float", "%", "忽略空值后求平均", "avg_humidity", "月平均相对湿度。"),
        ("precipitation_total", "float", "毫米", "忽略空值后求和", "precipitation", "月累计降水量。"),
        ("wind_speed", "float", "米/秒", "忽略空值后求平均", "wind_speed", "月平均风速。"),
    ]
    for field in monthly_common:
        add("weather_monthly.csv", *field)

    # 6. 省份周度特征表中的健康监测衍生字段。
    for scene_name in SCENE_FEATURE_NAMES.values():
        for pathogen_name in PATHOGEN_FEATURE_NAMES.values():
            field_name = f"resp_{scene_name}_{pathogen_name}_positive_rate"
            add(
                "province_weekly_features.csv",
                field_name,
                "float",
                "%",
                "该周未采集到对应指标时保留为空",
                "respiratory_weekly_clean.positive_rate",
                "全国急性呼吸道哨点监测病原体阳性率特征。",
            )

    add(
        "province_weekly_features.csv",
        "influenza_ili_percent_north",
        "float",
        "%",
        "该周未采集到对应指标时保留为空",
        "influenza_weekly_clean.metric_percent",
        "北方省份流感样病例百分比。",
    )
    add(
        "province_weekly_features.csv",
        "influenza_ili_percent_south",
        "float",
        "%",
        "该周未采集到对应指标时保留为空",
        "influenza_weekly_clean.metric_percent",
        "南方省份流感样病例百分比。",
    )
    add(
        "province_weekly_features.csv",
        "influenza_outbreak_count",
        "integer",
        "起",
        "该周未采集到对应指标时保留为空",
        "influenza_weekly_clean.outbreak_count",
        "全国流感样病例暴发疫情数。",
    )
    add(
        "province_weekly_features.csv",
        "influenza_dominant_subtype",
        "string",
        "-",
        "该周未采集到对应指标时保留为空",
        "influenza_weekly_clean.dominant_subtype",
        "流感周报摘要中提取的优势毒株或主要型别。",
    )

    return rows


def record_summary(
    summary: Dict[str, object],
    dataset_name: str,
    input_rows: Sequence[Dict[str, object]],
    output_rows: Sequence[Dict[str, object]],
    duplicate_count: int,
) -> None:
    """向质量摘要中写入单个数据集的行数、去重和缺失值统计。"""
    summary[dataset_name] = {
        "input_rows": len(input_rows),
        "output_rows": len(output_rows),
        "duplicates_dropped": duplicate_count,
        "missing_cells_by_field": missing_count(output_rows),
    }


def run_preprocess(input_dir: Path, output_dir: Path) -> Dict[str, object]:
    """执行完整的数据清洗与预处理流程。

    主流程严格按照“读取原始中间表 -> 单表清洗 -> 聚合派生 -> 质量摘要”
    的顺序组织，便于检查每一步的输入输出。
    """
    ensure_project_dirs()
    output_dir.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    summary: Dict[str, object] = {}

    # 1. 清洗法定传染病月报，保留月度重点病种趋势分析所需字段。
    chinacdc_raw = read_csv(input_dir / "chinacdc_monthly.csv")
    chinacdc_clean, chinacdc_duplicates = clean_chinacdc_monthly(chinacdc_raw)
    write_csv(
        output_dir / "chinacdc_monthly_clean.csv",
        chinacdc_clean,
        [
            "source_name",
            "source_url",
            "report_title",
            "report_year",
            "report_month",
            "period_month",
            "region",
            "disease_name",
            "disease_category",
            "is_respiratory_focus",
            "is_total_row",
            "cases",
            "deaths",
            "incidence_rate",
            "mortality_rate",
            "crawl_time",
            "raw_file",
        ],
    )
    record_summary(summary, "chinacdc_monthly", chinacdc_raw, chinacdc_clean, chinacdc_duplicates)

    # 2. 清洗急性呼吸道哨点周报，生成周度病原体阳性率数据。
    respiratory_raw = read_csv(input_dir / "respiratory_weekly.csv")
    respiratory_clean, respiratory_duplicates = clean_respiratory_weekly(respiratory_raw)
    write_csv(
        output_dir / "respiratory_weekly_clean.csv",
        respiratory_clean,
        list(respiratory_clean[0].keys()),
    )
    record_summary(
        summary,
        "respiratory_weekly",
        respiratory_raw,
        respiratory_clean,
        respiratory_duplicates,
    )

    # 3. 清洗流感周报，统一处理 ILI%、检测数、暴发疫情数等指标。
    influenza_raw = read_csv(input_dir / "influenza_weekly.csv")
    influenza_clean, influenza_duplicates = clean_influenza_weekly(influenza_raw)
    write_csv(
        output_dir / "influenza_weekly_clean.csv",
        influenza_clean,
        list(influenza_clean[0].keys()),
    )
    record_summary(
        summary,
        "influenza_weekly",
        influenza_raw,
        influenza_clean,
        influenza_duplicates,
    )

    # 4. 清洗日度气象数据，补充 ISO 周和年月字段。
    weather_raw = read_csv(input_dir / "weather_daily.csv")
    weather_clean, weather_duplicates = clean_weather_daily(weather_raw)
    write_csv(output_dir / "weather_daily_clean.csv", weather_clean, list(weather_clean[0].keys()))
    record_summary(summary, "weather_daily", weather_raw, weather_clean, weather_duplicates)

    # 5. 将日度气象数据聚合为周度和月度，分别对齐周报与月报分析。
    weather_weekly = aggregate_weather_weekly(weather_clean)
    write_csv(output_dir / "weather_weekly.csv", weather_weekly, list(weather_weekly[0].keys()))
    summary["weather_weekly"] = {"output_rows": len(weather_weekly)}

    weather_monthly = aggregate_weather_monthly(weather_clean)
    write_csv(output_dir / "weather_monthly.csv", weather_monthly, list(weather_monthly[0].keys()))
    summary["weather_monthly"] = {"output_rows": len(weather_monthly)}

    # 6. 构建宽表特征，作为成员 C 可视化和后续预警分析的主要输入。
    province_weekly = build_province_weekly_features(
        weather_weekly,
        respiratory_clean,
        influenza_clean,
    )
    province_fields = sorted({field for row in province_weekly for field in row.keys()})
    base_fields = [
        "region",
        "city",
        "report_year",
        "report_week",
        "year_week",
        "week_start",
        "week_end",
        "days_count",
        "avg_temperature",
        "max_temperature",
        "min_temperature",
        "avg_humidity",
        "precipitation_total",
        "wind_speed",
    ]
    feature_fields = base_fields + [field for field in province_fields if field not in base_fields]
    write_csv(output_dir / "province_weekly_features.csv", province_weekly, feature_fields)
    summary["province_weekly_features"] = {
        "output_rows": len(province_weekly),
        "feature_columns": len(feature_fields),
    }

    # 7. 输出数据字典和质量摘要，便于报告撰写和人工审核。
    dictionary_rows = build_dictionary_rows()
    write_csv(
        output_dir / "data_dictionary.csv",
        dictionary_rows,
        [
            "table_name",
            "field_name",
            "data_type",
            "unit",
            "missing_value_strategy",
            "source_field",
            "description",
        ],
    )

    summary["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    summary["output_dir"] = str(output_dir)
    with (output_dir / "quality_summary.json").open("w", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)

    with (LOG_DIR / "preprocess.log").open("a", encoding="utf-8") as file:
        file.write(f"[{summary['generated_at']}] processed data into {output_dir}\n")

    return summary


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(description="成员B数据清洗与预处理脚本")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=INTERIM_DIR,
        help="中间数据目录，默认 data/interim",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROCESSED_DIR,
        help="清洗结果目录，默认 data/processed",
    )
    return parser


def main() -> None:
    """命令行入口函数。"""
    args = build_parser().parse_args()
    summary = run_preprocess(args.input_dir, args.output_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
