"""Run reusable analysis for cleaned healthcare market and R&D data.

Inputs:
    data/processed/rd_annual_clean.csv
    data/processed/stock_daily_clean.csv
    data/processed/company_2024_features.csv

Outputs:
    data/analysis/descriptive_statistics.csv
    data/analysis/time_series_summary.csv
    data/analysis/correlation_matrix.csv
    data/analysis/cluster_results.csv
    data/analysis/anomaly_detection_results.csv
    data/analysis/keyword_sentiment_analysis.csv
    data/analysis/analysis_data_dictionary.csv
    data/analysis/analysis_summary.json

Methods:
    The script uses standard-library CSV, math, statistics, and JSON modules.
    Correlation, risk grouping, and anomaly flags are exploratory aids only;
    they should not be interpreted as causal evidence or final business labels.
"""

from __future__ import annotations

import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
ANALYSIS_DIR = PROJECT_ROOT / "data" / "analysis"


DESCRIPTIVE_FIELDS = [
    "dataset",
    "group_name",
    "metric_name",
    "observations",
    "mean",
    "min",
    "max",
    "sum",
    "latest_period",
    "latest_value",
]
TIME_SERIES_FIELDS = [
    "series_name",
    "frequency",
    "start_period",
    "end_period",
    "latest_value",
    "previous_value",
    "change",
    "change_percent",
    "recent_4_period_avg",
    "trend_direction",
]
CORRELATION_FIELDS = [
    "x_variable",
    "y_variable",
    "sample_size",
    "pearson_correlation",
    "abs_correlation",
    "strength",
    "direction",
]
CLUSTER_FIELDS = [
    "ticker",
    "company_name",
    "industry_group",
    "cluster_id",
    "risk_level",
    "risk_score",
    "avg_close",
    "year_end_adj_close",
    "total_volume",
    "avg_daily_return",
    "daily_return_volatility",
    "latest_rd_expense_busd",
]
ANOMALY_FIELDS = [
    "series_name",
    "period",
    "value",
    "mean",
    "stddev",
    "z_score",
    "anomaly_type",
]
KEYWORD_FIELDS = [
    "source_table",
    "keyword",
    "category",
    "occurrences",
    "document_count",
    "attention_label",
    "explanation",
]
DICTIONARY_FIELDS = [
    "table_name",
    "field_name",
    "data_type",
    "unit",
    "description",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a UTF-8 CSV file into a list of dictionaries."""
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    """Write dictionaries to CSV with stable field order."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: format_value(row.get(field, "")) for field in fieldnames})


def to_float(value: object) -> float | None:
    """Convert a CSV value to float, returning None for blank or invalid values."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def format_value(value: object) -> object:
    """Format numeric values with a stable precision while preserving text fields."""
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return ""
        return f"{value:.6f}"
    return value


def numeric_values(rows: list[dict[str, str]], field: str) -> list[float]:
    """Return valid numeric values from a field."""
    values: list[float] = []
    for row in rows:
        value = to_float(row.get(field))
        if value is not None:
            values.append(value)
    return values


def latest_by_period(rows: list[dict[str, str]], period_field: str, value_field: str) -> tuple[str, float | None]:
    """Find the latest non-empty value based on a sortable period field."""
    candidates: list[tuple[str, float]] = []
    for row in rows:
        value = to_float(row.get(value_field))
        period = str(row.get(period_field, "")).strip()
        if period and value is not None:
            candidates.append((period, value))
    if not candidates:
        return "", None
    candidates.sort(key=lambda item: item[0])
    return candidates[-1]


def add_stat_row(
    rows: list[dict[str, object]],
    dataset: str,
    group_name: str,
    metric_name: str,
    values: list[float],
    latest_period: str = "",
    latest_value: float | None = None,
) -> None:
    """Append one descriptive statistics row if values are available."""
    if not values:
        return
    rows.append(
        {
            "dataset": dataset,
            "group_name": group_name,
            "metric_name": metric_name,
            "observations": len(values),
            "mean": statistics.fmean(values),
            "min": min(values),
            "max": max(values),
            "sum": sum(values),
            "latest_period": latest_period,
            "latest_value": latest_value if latest_value is not None else "",
        }
    )


def generate_descriptive_statistics(
    rd_rows: list[dict[str, str]],
    stock_rows: list[dict[str, str]],
    feature_rows: list[dict[str, str]],
) -> list[dict[str, object]]:
    """Generate descriptive statistics for core numeric fields and industry groups."""
    output: list[dict[str, object]] = []
    metric_plan = {
        "company_2024_features": (
            feature_rows,
            "trade_year",
            [
                "trading_days",
                "avg_close",
                "year_end_adj_close",
                "total_volume",
                "avg_daily_return",
                "daily_return_volatility",
                "latest_rd_expense_busd",
            ],
        ),
        "stock_daily_clean": (
            stock_rows,
            "trade_date",
            ["close", "adj_close", "volume", "daily_return", "return_pct"],
        ),
        "rd_annual_clean": (
            rd_rows,
            "fiscal_year",
            ["rd_expense_usd", "rd_expense_musd", "rd_expense_busd"],
        ),
    }
    for dataset, (rows, period_field, fields) in metric_plan.items():
        for field in fields:
            latest_period, latest_value = latest_by_period(rows, period_field, field)
            add_stat_row(
                output,
                dataset,
                "all",
                field,
                numeric_values(rows, field),
                latest_period,
                latest_value,
            )

    industry_groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in feature_rows:
        industry_groups[row.get("industry_group", "Unknown") or "Unknown"].append(row)
    for industry, rows in sorted(industry_groups.items()):
        for field in ["avg_close", "year_end_adj_close", "total_volume", "daily_return_volatility", "latest_rd_expense_busd"]:
            latest_period, latest_value = latest_by_period(rows, "trade_year", field)
            add_stat_row(
                output,
                "company_2024_features",
                f"industry_group={industry}",
                field,
                numeric_values(rows, field),
                latest_period,
                latest_value,
            )
    return output


def trend_direction(change: float | None) -> str:
    """Convert a numeric change into a conservative trend label."""
    if change is None:
        return "insufficient_data"
    if change > 0:
        return "up"
    if change < 0:
        return "down"
    return "flat"


def series_summary(series_name: str, frequency: str, ordered_values: list[tuple[str, float]]) -> dict[str, object] | None:
    """Build a time-series summary row from ordered period/value pairs."""
    if not ordered_values:
        return None
    ordered_values = sorted(ordered_values, key=lambda item: item[0])
    latest_period, latest_value = ordered_values[-1]
    previous_value = ordered_values[-2][1] if len(ordered_values) >= 2 else None
    change = latest_value - previous_value if previous_value is not None else None
    change_percent = change / previous_value if previous_value not in (None, 0) else None
    recent_values = [value for _, value in ordered_values[-4:]]
    return {
        "series_name": series_name,
        "frequency": frequency,
        "start_period": ordered_values[0][0],
        "end_period": latest_period,
        "latest_value": latest_value,
        "previous_value": previous_value if previous_value is not None else "",
        "change": change if change is not None else "",
        "change_percent": change_percent if change_percent is not None else "",
        "recent_4_period_avg": statistics.fmean(recent_values),
        "trend_direction": trend_direction(change),
    }


def generate_time_series_summary(
    rd_rows: list[dict[str, str]], stock_rows: list[dict[str, str]]
) -> list[dict[str, object]]:
    """Generate monthly market and annual R&D trend summaries."""
    output: list[dict[str, object]] = []
    monthly: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in stock_rows:
        month = row.get("trade_month", "")
        if not month:
            continue
        for field in ["close", "adj_close", "daily_return"]:
            value = to_float(row.get(field))
            if value is not None:
                monthly[field][month].append(value)
        volume = to_float(row.get("volume"))
        if volume is not None:
            monthly["volume_sum"][month].append(volume)

    metric_labels = {
        "close": ("monthly_avg_close", "monthly"),
        "adj_close": ("monthly_avg_adj_close", "monthly"),
        "daily_return": ("monthly_avg_daily_return", "monthly"),
        "volume_sum": ("monthly_total_volume", "monthly"),
    }
    for field, (label, frequency) in metric_labels.items():
        values = []
        for period, period_values in monthly[field].items():
            if field == "volume_sum":
                values.append((period, sum(period_values)))
            else:
                values.append((period, statistics.fmean(period_values)))
        summary = series_summary(label, frequency, values)
        if summary:
            output.append(summary)

    annual_rd: dict[str, list[float]] = defaultdict(list)
    for row in rd_rows:
        fiscal_year = row.get("fiscal_year", "")
        value = to_float(row.get("rd_expense_busd"))
        if fiscal_year and value is not None:
            annual_rd[fiscal_year].append(value)
    annual_values = [(year, sum(values)) for year, values in annual_rd.items()]
    summary = series_summary("annual_total_rd_expense_busd", "annual", annual_values)
    if summary:
        output.append(summary)
    return output


def pearson(xs: list[float], ys: list[float]) -> float | None:
    """Calculate Pearson correlation for paired numeric values."""
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    mean_x = statistics.fmean(xs)
    mean_y = statistics.fmean(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denom_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    denom_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    denominator = denom_x * denom_y
    if denominator == 0:
        return None
    return numerator / denominator


def correlation_strength(value: float) -> str:
    """Label correlation strength by absolute value."""
    abs_value = abs(value)
    if abs_value >= 0.7:
        return "strong"
    if abs_value >= 0.4:
        return "moderate"
    if abs_value >= 0.2:
        return "weak"
    return "very_weak"


def generate_correlation_matrix(feature_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    """Generate pairwise Pearson correlations for company-level numeric features."""
    fields = [
        "trading_days",
        "avg_close",
        "year_end_adj_close",
        "total_volume",
        "avg_daily_return",
        "daily_return_volatility",
        "latest_rd_expense_busd",
    ]
    output: list[dict[str, object]] = []
    for index, x_field in enumerate(fields):
        for y_field in fields[index + 1 :]:
            pairs = []
            for row in feature_rows:
                x_value = to_float(row.get(x_field))
                y_value = to_float(row.get(y_field))
                if x_value is not None and y_value is not None:
                    pairs.append((x_value, y_value))
            corr = pearson([x for x, _ in pairs], [y for _, y in pairs])
            if corr is None:
                continue
            output.append(
                {
                    "x_variable": x_field,
                    "y_variable": y_field,
                    "sample_size": len(pairs),
                    "pearson_correlation": corr,
                    "abs_correlation": abs(corr),
                    "strength": correlation_strength(corr),
                    "direction": "positive" if corr >= 0 else "negative",
                }
            )
    return output


def percentile(sorted_values: list[float], ratio: float) -> float:
    """Return a nearest-rank percentile from pre-sorted values."""
    if not sorted_values:
        return 0.0
    index = min(len(sorted_values) - 1, max(0, round((len(sorted_values) - 1) * ratio)))
    return sorted_values[index]


def z_scores(values_by_key: dict[str, float]) -> dict[str, float]:
    """Standardize values and use zero when a feature has no variance."""
    values = list(values_by_key.values())
    if len(values) < 2:
        return {key: 0.0 for key in values_by_key}
    mean = statistics.fmean(values)
    stddev = statistics.pstdev(values)
    if stddev == 0:
        return {key: 0.0 for key in values_by_key}
    return {key: (value - mean) / stddev for key, value in values_by_key.items()}


def generate_cluster_results(feature_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    """Generate conservative company risk groups from standardized features."""
    keyed_rows = {row["ticker"]: row for row in feature_rows if row.get("ticker")}
    rd_z = z_scores(
        {
            ticker: to_float(row.get("latest_rd_expense_busd")) or 0.0
            for ticker, row in keyed_rows.items()
        }
    )
    volatility_z = z_scores(
        {
            ticker: to_float(row.get("daily_return_volatility")) or 0.0
            for ticker, row in keyed_rows.items()
        }
    )
    volume_z = z_scores(
        {ticker: to_float(row.get("total_volume")) or 0.0 for ticker, row in keyed_rows.items()}
    )
    return_z = z_scores(
        {ticker: to_float(row.get("avg_daily_return")) or 0.0 for ticker, row in keyed_rows.items()}
    )
    price_z = z_scores(
        {ticker: to_float(row.get("year_end_adj_close")) or 0.0 for ticker, row in keyed_rows.items()}
    )

    scored = []
    for ticker, row in keyed_rows.items():
        risk_score = (
            0.35 * volatility_z[ticker]
            + 0.20 * volume_z[ticker]
            + 0.20 * rd_z[ticker]
            - 0.15 * return_z[ticker]
            - 0.10 * price_z[ticker]
        )
        scored.append((ticker, risk_score))

    sorted_scores = sorted(score for _, score in scored)
    low_cut = percentile(sorted_scores, 1 / 3)
    high_cut = percentile(sorted_scores, 2 / 3)
    output: list[dict[str, object]] = []
    for ticker, score in sorted(scored, key=lambda item: item[1], reverse=True):
        row = keyed_rows[ticker]
        if score >= high_cut:
            cluster_id, risk_level = 2, "high_attention"
        elif score <= low_cut:
            cluster_id, risk_level = 0, "low_attention"
        else:
            cluster_id, risk_level = 1, "medium_attention"
        output.append(
            {
                "ticker": ticker,
                "company_name": row.get("company_name", ""),
                "industry_group": row.get("industry_group", ""),
                "cluster_id": cluster_id,
                "risk_level": risk_level,
                "risk_score": score,
                "avg_close": to_float(row.get("avg_close")) or "",
                "year_end_adj_close": to_float(row.get("year_end_adj_close")) or "",
                "total_volume": to_float(row.get("total_volume")) or "",
                "avg_daily_return": to_float(row.get("avg_daily_return")) or "",
                "daily_return_volatility": to_float(row.get("daily_return_volatility")) or "",
                "latest_rd_expense_busd": to_float(row.get("latest_rd_expense_busd")) or "",
            }
        )
    return output


def anomaly_rows_for_metric(
    stock_rows: list[dict[str, str]], metric: str, label: str
) -> list[dict[str, object]]:
    """Generate z-score anomaly rows for one ticker-level daily metric."""
    by_ticker: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in stock_rows:
        by_ticker[row.get("ticker", "")].append(row)

    output: list[dict[str, object]] = []
    for ticker, rows in by_ticker.items():
        values = [to_float(row.get(metric)) for row in rows]
        values = [value for value in values if value is not None]
        if len(values) < 10:
            continue
        mean = statistics.fmean(values)
        stddev = statistics.pstdev(values)
        if stddev == 0:
            continue
        for row in rows:
            value = to_float(row.get(metric))
            if value is None:
                continue
            z_score = (value - mean) / stddev
            if abs(z_score) >= 2:
                output.append(
                    {
                        "series_name": f"{ticker}_{label}",
                        "period": row.get("trade_date", ""),
                        "value": value,
                        "mean": mean,
                        "stddev": stddev,
                        "z_score": z_score,
                        "anomaly_type": "high_value" if z_score > 0 else "low_value",
                    }
                )
    return output


def generate_anomaly_results(stock_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    """Generate daily return and volume anomaly candidates."""
    rows = anomaly_rows_for_metric(stock_rows, "return_pct", "return_pct")
    rows.extend(anomaly_rows_for_metric(stock_rows, "volume", "volume"))
    return sorted(rows, key=lambda row: (row["series_name"], row["period"]))


def generate_keyword_sentiment_analysis(feature_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    """Generate official-field keyword attention statistics without inventing sentiment."""
    keyword_rules = [
        ("Biotechnology", "industry", "risk_attention", "生物技术行业分组，通常研发投入和市场波动关注度较高"),
        ("Pharmaceuticals", "industry", "regular_monitoring", "制药行业分组，用于常规行业对比"),
        ("Medical Devices", "industry", "regular_monitoring", "医疗器械行业分组，用于常规行业对比"),
        ("Diagnostics", "industry", "regular_monitoring", "诊断行业分组，用于常规行业对比"),
        ("Life Sciences Tools", "industry", "regular_monitoring", "生命科学工具行业分组，用于常规行业对比"),
        ("Therapeutics", "company_name", "risk_attention", "公司名称中的治疗相关关键词，提示研发型业务关注"),
        ("Pharmaceuticals", "company_name", "regular_monitoring", "公司名称中的制药相关关键词"),
        ("Bio", "company_name", "risk_attention", "公司名称中的生物相关关键词，提示创新研发关注"),
        ("Medical", "company_name", "regular_monitoring", "公司名称中的医疗相关关键词"),
    ]

    counters: dict[tuple[str, str, str, str], Counter[str]] = {}
    explanations: dict[tuple[str, str], str] = {}
    for keyword, category, attention_label, explanation in keyword_rules:
        explanations[(keyword, category)] = explanation
        occurrences = 0
        documents: set[str] = set()
        for row in feature_rows:
            text = " ".join(
                [
                    row.get("industry_group", ""),
                    row.get("company_name", ""),
                ]
            )
            count = text.lower().count(keyword.lower())
            if count:
                occurrences += count
                documents.add(row.get("ticker", ""))
        if occurrences:
            key = ("company_2024_features", keyword, category, attention_label)
            counters[key] = Counter({"occurrences": occurrences, "document_count": len(documents)})

    output = []
    for (source_table, keyword, category, attention_label), counter in sorted(counters.items()):
        explanation = explanations[(keyword, category)]
        output.append(
            {
                "source_table": source_table,
                "keyword": keyword,
                "category": category,
                "occurrences": counter["occurrences"],
                "document_count": counter["document_count"],
                "attention_label": attention_label,
                "explanation": explanation,
            }
        )
    return output


def build_analysis_dictionary_rows() -> list[dict[str, str]]:
    """Build field-level metadata for all analysis outputs."""
    specs = {
        "descriptive_statistics.csv": {
            "dataset": ("string", "-", "来源数据表"),
            "group_name": ("string", "-", "统计分组名称"),
            "metric_name": ("string", "-", "指标名称"),
            "observations": ("integer", "rows", "有效观测数量"),
            "mean": ("float", "varies", "均值"),
            "min": ("float", "varies", "最小值"),
            "max": ("float", "varies", "最大值"),
            "sum": ("float", "varies", "总和"),
            "latest_period": ("string", "-", "最新时期"),
            "latest_value": ("float", "varies", "最新时期对应值"),
        },
        "time_series_summary.csv": {
            "series_name": ("string", "-", "序列名称"),
            "frequency": ("string", "-", "时间粒度"),
            "start_period": ("string", "-", "起始时期"),
            "end_period": ("string", "-", "结束时期"),
            "latest_value": ("float", "varies", "最新值"),
            "previous_value": ("float", "varies", "上一期值"),
            "change": ("float", "varies", "变化量"),
            "change_percent": ("float", "ratio", "变化率"),
            "recent_4_period_avg": ("float", "varies", "最近 4 期均值"),
            "trend_direction": ("string", "-", "趋势方向"),
        },
        "correlation_matrix.csv": {
            "x_variable": ("string", "-", "第一变量"),
            "y_variable": ("string", "-", "第二变量"),
            "sample_size": ("integer", "rows", "配对样本量"),
            "pearson_correlation": ("float", "coefficient", "Pearson 相关系数"),
            "abs_correlation": ("float", "coefficient", "相关系数绝对值"),
            "strength": ("string", "-", "相关强度"),
            "direction": ("string", "-", "正相关或负相关"),
        },
        "cluster_results.csv": {
            "ticker": ("string", "-", "股票代码"),
            "company_name": ("string", "-", "公司名称"),
            "industry_group": ("string", "-", "行业分组"),
            "cluster_id": ("integer", "-", "分组编号"),
            "risk_level": ("string", "-", "风险关注等级"),
            "risk_score": ("float", "score", "标准化综合风险得分"),
            "avg_close": ("float", "USD", "2024 年平均收盘价"),
            "year_end_adj_close": ("float", "USD", "2024 年年末复权收盘价"),
            "total_volume": ("float", "shares", "2024 年总成交量"),
            "avg_daily_return": ("float", "ratio", "2024 年平均日收益率"),
            "daily_return_volatility": ("float", "ratio", "2024 年日收益率波动率"),
            "latest_rd_expense_busd": ("float", "billion USD", "最新研发费用"),
        },
        "anomaly_detection_results.csv": {
            "series_name": ("string", "-", "异常检测序列名称"),
            "period": ("date", "-", "异常候选日期"),
            "value": ("float", "varies", "当前值"),
            "mean": ("float", "varies", "序列均值"),
            "stddev": ("float", "varies", "序列标准差"),
            "z_score": ("float", "score", "标准化异常分数"),
            "anomaly_type": ("string", "-", "异常高值或异常低值"),
        },
        "keyword_sentiment_analysis.csv": {
            "source_table": ("string", "-", "来源数据表"),
            "keyword": ("string", "-", "关键词"),
            "category": ("string", "-", "关键词类别"),
            "occurrences": ("integer", "count", "出现次数"),
            "document_count": ("integer", "companies", "覆盖公司数量"),
            "attention_label": ("string", "-", "关注标签"),
            "explanation": ("string", "-", "结果解释"),
        },
        "analysis_summary.json": {
            "generated_at": ("datetime", "-", "分析生成时间"),
            "input_rows": ("object", "rows", "输入表行数"),
            "output_rows": ("object", "rows", "输出表行数"),
            "key_findings": ("array", "-", "核心发现"),
            "limitations": ("array", "-", "分析局限"),
        },
    }
    rows: list[dict[str, str]] = []
    for table_name, fields in specs.items():
        for field_name, (data_type, unit, description) in fields.items():
            rows.append(
                {
                    "table_name": table_name,
                    "field_name": field_name,
                    "data_type": data_type,
                    "unit": unit,
                    "description": description,
                }
            )
    return rows


def build_summary(
    rd_rows: list[dict[str, str]],
    stock_rows: list[dict[str, str]],
    feature_rows: list[dict[str, str]],
    outputs: dict[str, list[dict[str, object]]],
) -> dict[str, object]:
    """Build a machine-readable summary for reports and validation."""
    high_attention = [row for row in outputs["cluster_results.csv"] if row["risk_level"] == "high_attention"]
    strongest_corr = None
    if outputs["correlation_matrix.csv"]:
        strongest_corr = max(outputs["correlation_matrix.csv"], key=lambda row: row["abs_correlation"])
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_rows": {
            "rd_annual_clean": len(rd_rows),
            "stock_daily_clean": len(stock_rows),
            "company_2024_features": len(feature_rows),
        },
        "output_rows": {name: len(rows) for name, rows in outputs.items()},
        "key_findings": [
            f"公司特征宽表覆盖 {len(feature_rows)} 家公司，行业包括 {len({row.get('industry_group') for row in feature_rows})} 个分组。",
            f"风险分组中高关注公司 {len(high_attention)} 家，结果用于提示而非最终业务判断。",
            f"异常检测输出 {len(outputs['anomaly_detection_results.csv'])} 条日度收益率或成交量异常候选。",
        ],
        "limitations": [
            "相关性不等于因果关系，研发投入和市场表现之间只能做线性共变解释。",
            "风险分组采用标准化规则和分位数切分，不替代财务、临床或监管尽调。",
            "关键词分析来自官方字段文本，不代表社交媒体主观情绪。",
        ],
    }
    if strongest_corr:
        summary["key_findings"].append(
            "最强公司级相关组合为 "
            f"{strongest_corr['x_variable']} 与 {strongest_corr['y_variable']}，"
            f"Pearson={strongest_corr['pearson_correlation']:.3f}。"
        )
    return summary


def run_analysis() -> None:
    """Run the complete analysis workflow and write all outputs."""
    rd_rows = read_csv(PROCESSED_DIR / "rd_annual_clean.csv")
    stock_rows = read_csv(PROCESSED_DIR / "stock_daily_clean.csv")
    feature_rows = read_csv(PROCESSED_DIR / "company_2024_features.csv")

    descriptive = generate_descriptive_statistics(rd_rows, stock_rows, feature_rows)
    time_series = generate_time_series_summary(rd_rows, stock_rows)
    correlation = generate_correlation_matrix(feature_rows)
    clusters = generate_cluster_results(feature_rows)
    anomalies = generate_anomaly_results(stock_rows)
    keywords = generate_keyword_sentiment_analysis(feature_rows)
    dictionary = build_analysis_dictionary_rows()

    outputs = {
        "descriptive_statistics.csv": descriptive,
        "time_series_summary.csv": time_series,
        "correlation_matrix.csv": correlation,
        "cluster_results.csv": clusters,
        "anomaly_detection_results.csv": anomalies,
        "keyword_sentiment_analysis.csv": keywords,
        "analysis_data_dictionary.csv": dictionary,
    }
    write_csv(ANALYSIS_DIR / "descriptive_statistics.csv", descriptive, DESCRIPTIVE_FIELDS)
    write_csv(ANALYSIS_DIR / "time_series_summary.csv", time_series, TIME_SERIES_FIELDS)
    write_csv(ANALYSIS_DIR / "correlation_matrix.csv", correlation, CORRELATION_FIELDS)
    write_csv(ANALYSIS_DIR / "cluster_results.csv", clusters, CLUSTER_FIELDS)
    write_csv(ANALYSIS_DIR / "anomaly_detection_results.csv", anomalies, ANOMALY_FIELDS)
    write_csv(ANALYSIS_DIR / "keyword_sentiment_analysis.csv", keywords, KEYWORD_FIELDS)
    write_csv(ANALYSIS_DIR / "analysis_data_dictionary.csv", dictionary, DICTIONARY_FIELDS)

    summary = build_summary(rd_rows, stock_rows, feature_rows, outputs)
    with (ANALYSIS_DIR / "analysis_summary.json").open("w", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    run_analysis()
