"""成员 B 数据分析脚本。

本脚本基于 `data/processed/` 中的清洗结果，生成描述性统计、时间序列
趋势、相关性矩阵、聚类风险分组和异常检测结果。脚本只使用 Python 标准库，
确保在课程提交环境中可以直接复现。
"""

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from utils.paths import DATA_DIR, PROCESSED_DIR


ANALYSIS_DIR = DATA_DIR / "analysis"

FOCUS_DISEASES = {
    "新型冠状病毒感染",
    "流行性感冒",
    "肺结核",
    "百日咳",
    "麻疹",
    "猩红热",
    "流行性腮腺炎",
}

WEATHER_FIELDS = [
    "avg_temperature",
    "avg_humidity",
    "precipitation_total",
    "wind_speed",
]

CLUSTER_HEALTH_FIELDS = [
    "influenza_ili_percent_north",
    "influenza_ili_percent_south",
    "influenza_outbreak_count",
    "resp_outpatient_ili_influenza_positive_rate",
    "resp_outpatient_ili_covid_positive_rate",
    "resp_outpatient_ili_rsv_positive_rate",
    "resp_outpatient_ili_mycoplasma_positive_rate",
    "resp_hospital_sari_influenza_positive_rate",
    "resp_hospital_sari_covid_positive_rate",
]

KEYWORD_RULES = [
    ("新型冠状病毒", "病原体"),
    ("新冠", "病种/病原体"),
    ("流感", "病种/病原体"),
    ("肺结核", "病种"),
    ("百日咳", "病种"),
    ("麻疹", "病种"),
    ("猩红热", "病种"),
    ("流行性腮腺炎", "病种"),
    ("呼吸道合胞病毒", "病原体"),
    ("腺病毒", "病原体"),
    ("肺炎支原体", "病原体"),
    ("人偏肺病毒", "病原体"),
    ("副流感病毒", "病原体"),
    ("博卡病毒", "病原体"),
    ("鼻病毒", "病原体"),
    ("ILI", "监测指标"),
    ("暴发", "风险词"),
    ("阳性率", "监测指标"),
    ("疫情", "风险词"),
    ("监测", "监测指标"),
    ("预警", "风险词"),
    ("风险", "风险词"),
]


def read_csv(path: Path) -> List[Dict[str, str]]:
    """读取 UTF-8 CSV 文件。"""
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: Sequence[Dict[str, object]], fields: Sequence[str]) -> None:
    """按固定字段顺序写出 CSV。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def to_float(value: object) -> Optional[float]:
    """将 CSV 单元格转换为 float，无法转换时返回 None。"""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def mean(values: Iterable[float]) -> Optional[float]:
    """计算平均值。"""
    numbers = list(values)
    if not numbers:
        return None
    return sum(numbers) / len(numbers)


def stddev(values: Iterable[float]) -> Optional[float]:
    """计算总体标准差。"""
    numbers = list(values)
    if len(numbers) < 2:
        return None
    avg = sum(numbers) / len(numbers)
    variance = sum((value - avg) ** 2 for value in numbers) / len(numbers)
    return math.sqrt(variance)


def fmt(value: Optional[float], digits: int = 4) -> str:
    """格式化数值，便于 CSV 输出。"""
    if value is None:
        return ""
    rounded = round(value, digits)
    if rounded == int(rounded):
        return str(int(rounded))
    return str(rounded)


def pearson(x_values: Sequence[float], y_values: Sequence[float]) -> Optional[float]:
    """计算 Pearson 相关系数。"""
    if len(x_values) < 3 or len(x_values) != len(y_values):
        return None
    x_avg = mean(x_values)
    y_avg = mean(y_values)
    if x_avg is None or y_avg is None:
        return None
    numerator = sum((x - x_avg) * (y - y_avg) for x, y in zip(x_values, y_values))
    x_denominator = math.sqrt(sum((x - x_avg) ** 2 for x in x_values))
    y_denominator = math.sqrt(sum((y - y_avg) ** 2 for y in y_values))
    denominator = x_denominator * y_denominator
    if denominator == 0:
        return None
    return numerator / denominator


def correlation_strength(value: float) -> str:
    """根据相关系数绝对值给出强度标签。"""
    abs_value = abs(value)
    if abs_value >= 0.7:
        return "强相关"
    if abs_value >= 0.4:
        return "中等相关"
    if abs_value >= 0.2:
        return "弱相关"
    return "相关较弱"


def summarize_series(
    dataset: str,
    group_name: str,
    metric_name: str,
    period_values: Sequence[Tuple[str, float]],
    note: str,
) -> Dict[str, object]:
    """生成单个数值序列的描述性统计。"""
    if not period_values:
        return {}
    values = [value for _, value in period_values]
    latest_period, latest_value = sorted(period_values, key=lambda item: item[0])[-1]
    return {
        "analysis_type": "descriptive",
        "dataset": dataset,
        "group_name": group_name,
        "metric_name": metric_name,
        "observations": len(values),
        "mean": fmt(mean(values)),
        "min": fmt(min(values)),
        "max": fmt(max(values)),
        "sum": fmt(sum(values)),
        "latest_period": latest_period,
        "latest_value": fmt(latest_value),
        "note": note,
    }


def build_monthly_disease_series(
    rows: Sequence[Dict[str, str]]
) -> Dict[str, List[Tuple[str, float]]]:
    """构建重点病种月度发病数时间序列。"""
    series: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
    for row in rows:
        disease_name = row.get("disease_name", "")
        if disease_name not in FOCUS_DISEASES or row.get("is_total_row") == "1":
            continue
        value = to_float(row.get("cases"))
        period = row.get("period_month", "")
        if value is not None and period:
            series[disease_name].append((period, value))
    return series


def build_respiratory_series(rows: Sequence[Dict[str, str]]) -> Dict[str, List[Tuple[str, float]]]:
    """构建急性呼吸道病原体阳性率周度序列。"""
    series: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
    for row in rows:
        if row.get("metric_type") != "pathogen_positive_rate":
            continue
        value = to_float(row.get("positive_rate"))
        period = row.get("year_week", "")
        scene = row.get("surveillance_scene", "")
        pathogen = row.get("pathogen_name", "")
        if value is not None and period and pathogen:
            series[f"{scene}-{pathogen}阳性率"].append((period, value))
    return series


def build_influenza_series(rows: Sequence[Dict[str, str]]) -> Dict[str, List[Tuple[str, float]]]:
    """构建流感周报数值指标时间序列。"""
    series: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
    for row in rows:
        value = to_float(row.get("indicator_value"))
        period = row.get("year_week", "")
        metric_type = row.get("metric_type", "")
        if value is None or not period:
            continue
        if metric_type == "ili_percent":
            group = row.get("region_group", "")
            series[f"{group} ILI%"].append((period, value))
        elif metric_type == "outbreak_count":
            series["流感样病例暴发疫情数"].append((period, value))
    return series


def build_weekly_feature_rows(rows: Sequence[Dict[str, str]]) -> List[Dict[str, object]]:
    """将城市周度特征压缩为全国周度特征，避免相关性分析重复计数。"""
    groups: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        year_week = row.get("year_week", "")
        if year_week:
            groups[year_week].append(row)

    weekly_rows = []
    for year_week, items in sorted(groups.items()):
        output: Dict[str, object] = {"year_week": year_week}
        for field in WEATHER_FIELDS:
            values = [to_float(item.get(field)) for item in items]
            values = [value for value in values if value is not None]
            output[field] = mean(values)

        for field in numeric_health_fields(rows):
            values = [to_float(item.get(field)) for item in items]
            values = [value for value in values if value is not None]
            output[field] = values[0] if values else None
        weekly_rows.append(output)
    return weekly_rows


def numeric_health_fields(rows: Sequence[Dict[str, str]]) -> List[str]:
    """识别省份周度特征表中的数值型健康监测字段。"""
    if not rows:
        return []
    fields = []
    for field in rows[0].keys():
        if field.startswith("resp_") and field.endswith("_positive_rate"):
            fields.append(field)
        elif field.startswith("influenza_") and field != "influenza_dominant_subtype":
            fields.append(field)
    return fields


def generate_descriptive_statistics(
    chinacdc_rows: Sequence[Dict[str, str]],
    respiratory_rows: Sequence[Dict[str, str]],
    influenza_rows: Sequence[Dict[str, str]],
    province_weekly_rows: Sequence[Dict[str, str]],
) -> List[Dict[str, object]]:
    """生成描述性统计结果。"""
    result = []

    for disease, series in build_monthly_disease_series(chinacdc_rows).items():
        row = summarize_series(
            "chinacdc_monthly_clean",
            disease,
            "cases",
            series,
            "重点呼吸道病种月度发病数。",
        )
        if row:
            result.append(row)

    for name, series in build_respiratory_series(respiratory_rows).items():
        row = summarize_series(
            "respiratory_weekly_clean",
            name,
            "positive_rate",
            series,
            "急性呼吸道哨点监测病原体阳性率。",
        )
        if row:
            result.append(row)

    for name, series in build_influenza_series(influenza_rows).items():
        row = summarize_series(
            "influenza_weekly_clean",
            name,
            "indicator_value",
            series,
            "流感监测周报核心数值指标。",
        )
        if row:
            result.append(row)

    region_values: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    for row in province_weekly_rows:
        region = row.get("region", "")
        for field in WEATHER_FIELDS:
            value = to_float(row.get(field))
            if region and value is not None:
                region_values[region][field].append(value)

    for region, metrics in sorted(region_values.items()):
        for field, values in metrics.items():
            period_values = [(str(index), value) for index, value in enumerate(values)]
            row = summarize_series(
                "province_weekly_features",
                region,
                field,
                period_values,
                "省会城市周度气象指标。",
            )
            if row:
                result.append(row)

    return result


def generate_time_series_summary(
    chinacdc_rows: Sequence[Dict[str, str]],
    respiratory_rows: Sequence[Dict[str, str]],
    influenza_rows: Sequence[Dict[str, str]],
) -> List[Dict[str, object]]:
    """生成时间序列趋势摘要。"""
    all_series = {}
    monthly_series = build_monthly_disease_series(chinacdc_rows)
    all_series.update({f"{name}月度发病数": values for name, values in monthly_series.items()})
    all_series.update(build_respiratory_series(respiratory_rows))
    all_series.update(build_influenza_series(influenza_rows))

    rows = []
    for series_name, period_values in sorted(all_series.items()):
        sorted_values = sorted(period_values, key=lambda item: item[0])
        if len(sorted_values) < 2:
            continue
        latest_period, latest_value = sorted_values[-1]
        previous_period, previous_value = sorted_values[-2]
        change = latest_value - previous_value
        change_percent = None
        if previous_value != 0:
            change_percent = change / previous_value * 100
        recent_values = [value for _, value in sorted_values[-4:]]
        recent_avg = mean(recent_values)
        trend = "上升" if change > 0 else "下降" if change < 0 else "持平"
        rows.append(
            {
                "series_name": series_name,
                "frequency": "月度" if "月度" in series_name else "周度",
                "start_period": sorted_values[0][0],
                "end_period": latest_period,
                "observations": len(sorted_values),
                "latest_value": fmt(latest_value),
                "previous_period": previous_period,
                "previous_value": fmt(previous_value),
                "change": fmt(change),
                "change_percent": fmt(change_percent),
                "recent_4_period_avg": fmt(recent_avg),
                "trend_direction": trend,
            }
        )
    return rows


def generate_correlation_matrix(
    province_weekly_rows: Sequence[Dict[str, str]]
) -> List[Dict[str, object]]:
    """生成气象指标与健康监测指标之间的相关性矩阵。"""
    weekly_rows = build_weekly_feature_rows(province_weekly_rows)
    health_fields = numeric_health_fields(province_weekly_rows)
    rows = []
    for weather_field in WEATHER_FIELDS:
        for health_field in health_fields:
            paired = []
            for row in weekly_rows:
                x_value = row.get(weather_field)
                y_value = row.get(health_field)
                if isinstance(x_value, float) and isinstance(y_value, float):
                    paired.append((x_value, y_value))
            if len(paired) < 10:
                continue
            x_values = [item[0] for item in paired]
            y_values = [item[1] for item in paired]
            corr = pearson(x_values, y_values)
            if corr is None:
                continue
            rows.append(
                {
                    "x_variable": weather_field,
                    "y_variable": health_field,
                    "sample_size": len(paired),
                    "pearson_correlation": fmt(corr),
                    "abs_correlation": fmt(abs(corr)),
                    "strength": correlation_strength(corr),
                    "direction": "正相关" if corr > 0 else "负相关",
                }
            )
    return sorted(rows, key=lambda row: float(row["abs_correlation"]), reverse=True)


def column_means(rows: Sequence[Dict[str, str]], fields: Sequence[str]) -> Dict[str, float]:
    """计算指定字段的均值，用于缺失值填补。"""
    means = {}
    for field in fields:
        values = [to_float(row.get(field)) for row in rows]
        values = [value for value in values if value is not None]
        means[field] = mean(values) or 0.0
    return means


def normalize_matrix(matrix: Sequence[Sequence[float]]) -> List[List[float]]:
    """对矩阵按列做 Z-score 标准化。"""
    if not matrix:
        return []
    column_count = len(matrix[0])
    columns = [[row[index] for row in matrix] for index in range(column_count)]
    averages = [mean(column) or 0.0 for column in columns]
    deviations = [stddev(column) or 1.0 for column in columns]
    normalized = []
    for row in matrix:
        normalized.append(
            [
                (value - averages[index]) / deviations[index]
                for index, value in enumerate(row)
            ]
        )
    return normalized


def euclidean(left: Sequence[float], right: Sequence[float]) -> float:
    """计算欧氏距离。"""
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(left, right)))


def kmeans(matrix: Sequence[Sequence[float]], k: int = 3, iterations: int = 40) -> List[int]:
    """简单 K-Means 聚类实现，避免引入 scikit-learn 依赖。"""
    if not matrix:
        return []
    centroids = [list(matrix[index * len(matrix) // k]) for index in range(k)]
    labels = [0 for _ in matrix]
    for _ in range(iterations):
        changed = False
        for row_index, row in enumerate(matrix):
            distances = [euclidean(row, centroid) for centroid in centroids]
            label = min(range(k), key=lambda index: distances[index])
            if label != labels[row_index]:
                labels[row_index] = label
                changed = True
        for cluster_index in range(k):
            cluster_rows = [
                row for row, label in zip(matrix, labels) if label == cluster_index
            ]
            if not cluster_rows:
                continue
            centroids[cluster_index] = [
                mean(column) or 0.0 for column in zip(*cluster_rows)
            ]
        if not changed:
            break
    return labels


def generate_cluster_results(
    province_weekly_rows: Sequence[Dict[str, str]]
) -> List[Dict[str, object]]:
    """对城市周度记录进行风险聚类。"""
    fields = WEATHER_FIELDS + CLUSTER_HEALTH_FIELDS
    candidate_rows = [
        row for row in province_weekly_rows
        if any(to_float(row.get(field)) is not None for field in CLUSTER_HEALTH_FIELDS)
    ]
    if not candidate_rows:
        return []

    means = column_means(candidate_rows, fields)
    matrix = []
    risk_scores = []
    for row in candidate_rows:
        values = [to_float(row.get(field)) for field in fields]
        filled_values = [
            value if value is not None else means[field]
            for value, field in zip(values, fields)
        ]
        matrix.append(filled_values)
        health_values = [
            to_float(row.get(field)) for field in CLUSTER_HEALTH_FIELDS
        ]
        health_values = [value for value in health_values if value is not None]
        risk_scores.append(mean(health_values) or 0.0)

    normalized_matrix = normalize_matrix(matrix)
    labels = kmeans(normalized_matrix, k=3)
    cluster_risk = defaultdict(list)
    for label, score in zip(labels, risk_scores):
        cluster_risk[label].append(score)
    ordered_clusters = sorted(
        cluster_risk,
        key=lambda label: mean(cluster_risk[label]) or 0.0,
    )
    risk_level_map = {
        ordered_clusters[0]: "低风险",
        ordered_clusters[1]: "中风险",
        ordered_clusters[2]: "高风险",
    }

    rows = []
    for source_row, label, risk_score in zip(candidate_rows, labels, risk_scores):
        output = {
            "region": source_row.get("region", ""),
            "city": source_row.get("city", ""),
            "report_year": source_row.get("report_year", ""),
            "report_week": source_row.get("report_week", ""),
            "year_week": source_row.get("year_week", ""),
            "cluster_id": label,
            "risk_level": risk_level_map[label],
            "risk_score": fmt(risk_score),
        }
        for field in fields:
            output[field] = source_row.get(field, "")
        rows.append(output)
    return rows


def generate_anomaly_results(
    chinacdc_rows: Sequence[Dict[str, str]],
    respiratory_rows: Sequence[Dict[str, str]],
    influenza_rows: Sequence[Dict[str, str]],
) -> List[Dict[str, object]]:
    """使用 Z-score 识别异常高值和异常低值。"""
    all_series = {}
    monthly_series = build_monthly_disease_series(chinacdc_rows)
    all_series.update({f"{name}月度发病数": values for name, values in monthly_series.items()})
    all_series.update(build_respiratory_series(respiratory_rows))
    all_series.update(build_influenza_series(influenza_rows))

    rows = []
    for series_name, period_values in sorted(all_series.items()):
        sorted_values = sorted(period_values, key=lambda item: item[0])
        values = [value for _, value in sorted_values]
        avg = mean(values)
        deviation = stddev(values)
        if avg is None or deviation in (None, 0):
            continue
        for period, value in sorted_values:
            z_score = (value - avg) / deviation
            if abs(z_score) < 2:
                continue
            rows.append(
                {
                    "series_name": series_name,
                    "period": period,
                    "value": fmt(value),
                    "mean": fmt(avg),
                    "stddev": fmt(deviation),
                    "z_score": fmt(z_score),
                    "anomaly_type": "异常高值" if z_score > 0 else "异常低值",
                }
            )
    return sorted(rows, key=lambda row: abs(float(row["z_score"])), reverse=True)


def generate_keyword_sentiment_analysis(
    chinacdc_rows: Sequence[Dict[str, str]],
    respiratory_rows: Sequence[Dict[str, str]],
    influenza_rows: Sequence[Dict[str, str]],
) -> List[Dict[str, object]]:
    """基于官方通报文本字段生成关键词和关注倾向分析。

    当前项目没有采集微博、新闻评论等真实社交舆情数据，因此这里使用官方
    通报标题、病种名、病原体名和指标名做“公共卫生关注关键词分析”。情绪
    标签不是主观情绪判断，而是根据关键词类别区分常规监测和风险关注。
    """
    corpus = []
    for row in chinacdc_rows:
        corpus.append(
            (
                "chinacdc_monthly_clean",
                " ".join(
                    [
                        row.get("report_title", ""),
                        row.get("disease_name", ""),
                        row.get("disease_category", ""),
                    ]
                ),
            )
        )
    for row in respiratory_rows:
        corpus.append(
            (
                "respiratory_weekly_clean",
                " ".join(
                    [
                        row.get("report_title", ""),
                        row.get("surveillance_scene", ""),
                        row.get("pathogen_name", ""),
                        row.get("ranked_pathogen", ""),
                        row.get("metric_type", ""),
                    ]
                ),
            )
        )
    for row in influenza_rows:
        corpus.append(
            (
                "influenza_weekly_clean",
                " ".join(
                    [
                        row.get("report_title", ""),
                        row.get("metric_type", ""),
                        row.get("metric_name", ""),
                        row.get("dominant_subtype", ""),
                    ]
                ),
            )
        )

    counter: Dict[Tuple[str, str, str], Dict[str, int]] = defaultdict(
        lambda: {"occurrences": 0, "document_count": 0}
    )
    for source_table, text in corpus:
        for keyword, category in KEYWORD_RULES:
            count = text.count(keyword)
            if count == 0:
                continue
            key = (source_table, keyword, category)
            counter[key]["occurrences"] += count
            counter[key]["document_count"] += 1

    rows = []
    for (source_table, keyword, category), values in sorted(counter.items()):
        sentiment_label = "风险关注" if category == "风险词" else "常规监测关注"
        rows.append(
            {
                "source_table": source_table,
                "keyword": keyword,
                "category": category,
                "occurrences": values["occurrences"],
                "document_count": values["document_count"],
                "attention_label": sentiment_label,
                "explanation": "基于官方通报文本字段统计，非社交媒体主观情绪。",
            }
        )
    return sorted(rows, key=lambda row: int(row["occurrences"]), reverse=True)


def build_summary(
    descriptive_rows: Sequence[Dict[str, object]],
    time_series_rows: Sequence[Dict[str, object]],
    correlation_rows: Sequence[Dict[str, object]],
    cluster_rows: Sequence[Dict[str, object]],
    anomaly_rows: Sequence[Dict[str, object]],
    keyword_rows: Sequence[Dict[str, object]],
    output_dir: Path,
) -> Dict[str, object]:
    """生成核心结论摘要。"""
    risk_counter = Counter(row.get("risk_level") for row in cluster_rows)
    top_correlations = correlation_rows[:5]
    top_anomalies = anomaly_rows[:10]

    conclusions = []
    if top_correlations:
        top = top_correlations[0]
        conclusions.append(
            f"相关性最高的组合为 {top['x_variable']} 与 {top['y_variable']}，"
            f"Pearson 相关系数为 {top['pearson_correlation']}。"
        )
    if risk_counter:
        conclusions.append(
            "聚类结果形成低风险、中风险和高风险三类城市周度记录，"
            f"其中高风险记录数为 {risk_counter.get('高风险', 0)}。"
        )
    if top_anomalies:
        conclusions.append(
            f"异常检测共识别 {len(anomaly_rows)} 个异常点，"
            "可作为后续早期预警指标候选。"
        )
    conclusions.append(
        "清洗后数据能够支撑描述统计、趋势跟踪、气象相关性分析、"
        "风险分组和异常检测等成员 B 负责的核心分析任务。"
    )

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "output_dir": str(output_dir),
        "descriptive_statistics_rows": len(descriptive_rows),
        "time_series_summary_rows": len(time_series_rows),
        "correlation_pairs": len(correlation_rows),
        "cluster_rows": len(cluster_rows),
        "cluster_counts": dict(risk_counter),
        "anomaly_rows": len(anomaly_rows),
        "keyword_sentiment_rows": len(keyword_rows),
        "top_correlations": top_correlations,
        "top_anomalies": top_anomalies,
        "top_keywords": keyword_rows[:10],
        "core_conclusions": conclusions,
        "application_directions": [
            "呼吸道传染病早期预警：基于阳性率、ILI%、暴发疫情数和异常检测结果识别风险升高周。",
            "气象驱动风险提示：结合气温、湿度、降水等因素评估呼吸道病原体活跃风险。",
            "重点病原体趋势监测：持续跟踪流感病毒、新冠病毒、呼吸道合胞病毒等重点对象。",
        ],
        "feasibility": {
            "technical": "数据来源公开，清洗和分析脚本可复现，技术实现可行。",
            "cost": "使用公开数据和本地脚本，部署成本较低。",
            "demand": "学校、社区、医院和疾控场景均存在呼吸道风险监测需求。",
            "data_availability": "当前已有 10 万级采集数据和多张清洗后分析表，数据基础可用。",
        },
    }


def build_analysis_dictionary_rows() -> List[Dict[str, str]]:
    """生成分析输出文件字段说明。"""
    rows: List[Dict[str, str]] = []

    def add(
        table_name: str,
        field_name: str,
        data_type: str,
        unit: str,
        description: str,
    ) -> None:
        rows.append(
            {
                "table_name": table_name,
                "field_name": field_name,
                "data_type": data_type,
                "unit": unit,
                "description": description,
            }
        )

    table = "descriptive_statistics.csv"
    add(table, "analysis_type", "string", "-", "分析类型。")
    add(table, "dataset", "string", "-", "统计对象来源数据表。")
    add(table, "group_name", "string", "-", "统计分组名称，如病种、病原体或地区。")
    add(table, "metric_name", "string", "-", "统计指标名称。")
    add(table, "observations", "integer", "期/条", "参与统计的观测数量。")
    add(table, "mean", "float", "按指标类型", "指标均值。")
    add(table, "min", "float", "按指标类型", "指标最小值。")
    add(table, "max", "float", "按指标类型", "指标最大值。")
    add(table, "sum", "float", "按指标类型", "指标总和。")
    add(table, "latest_period", "string", "-", "最新观测期。")
    add(table, "latest_value", "float", "按指标类型", "最新观测值。")
    add(table, "note", "string", "-", "统计说明。")

    table = "time_series_summary.csv"
    add(table, "series_name", "string", "-", "时间序列名称。")
    add(table, "frequency", "string", "-", "时间粒度，月度或周度。")
    add(table, "start_period", "string", "-", "序列起始时期。")
    add(table, "end_period", "string", "-", "序列结束时期。")
    add(table, "observations", "integer", "期", "序列观测期数量。")
    add(table, "latest_value", "float", "按指标类型", "最新一期数值。")
    add(table, "previous_period", "string", "-", "上一期时期。")
    add(table, "previous_value", "float", "按指标类型", "上一期数值。")
    add(table, "change", "float", "按指标类型", "最新值相对上一期变化量。")
    add(table, "change_percent", "float", "%", "最新值相对上一期变化率。")
    add(table, "recent_4_period_avg", "float", "按指标类型", "最近 4 期均值。")
    add(table, "trend_direction", "string", "-", "趋势方向，上升、下降或持平。")

    table = "correlation_matrix.csv"
    add(table, "x_variable", "string", "-", "气象变量名称。")
    add(table, "y_variable", "string", "-", "健康监测变量名称。")
    add(table, "sample_size", "integer", "周", "参与相关性计算的样本量。")
    add(table, "pearson_correlation", "float", "-", "Pearson 相关系数。")
    add(table, "abs_correlation", "float", "-", "相关系数绝对值。")
    add(table, "strength", "string", "-", "相关强度标签。")
    add(table, "direction", "string", "-", "相关方向，正相关或负相关。")

    table = "cluster_results.csv"
    for field in ["region", "city", "year_week"]:
        add(table, field, "string", "-", "城市周度记录标识字段。")
    add(table, "report_year", "integer", "年", "ISO 周所属年份。")
    add(table, "report_week", "integer", "周", "ISO 周次。")
    add(table, "cluster_id", "integer", "-", "K-Means 聚类编号。")
    add(table, "risk_level", "string", "-", "风险等级，低风险、中风险或高风险。")
    add(table, "risk_score", "float", "按指标类型", "根据健康监测指标计算的风险得分。")
    for field in WEATHER_FIELDS:
        add(table, field, "float", "按字段原单位", "用于聚类的气象特征。")
    for field in CLUSTER_HEALTH_FIELDS:
        add(table, field, "float", "%/起", "用于聚类的健康监测特征。")

    table = "anomaly_detection_results.csv"
    add(table, "series_name", "string", "-", "异常检测序列名称。")
    add(table, "period", "string", "-", "异常发生时期。")
    add(table, "value", "float", "按指标类型", "该时期观测值。")
    add(table, "mean", "float", "按指标类型", "该序列均值。")
    add(table, "stddev", "float", "按指标类型", "该序列标准差。")
    add(table, "z_score", "float", "-", "标准化异常分数。")
    add(table, "anomaly_type", "string", "-", "异常类型，异常高值或异常低值。")

    table = "keyword_sentiment_analysis.csv"
    add(table, "source_table", "string", "-", "关键词来源数据表。")
    add(table, "keyword", "string", "-", "统计关键词。")
    add(table, "category", "string", "-", "关键词类别。")
    add(table, "occurrences", "integer", "次", "关键词出现次数。")
    add(table, "document_count", "integer", "条", "包含该关键词的记录数量。")
    add(table, "attention_label", "string", "-", "关注标签，如常规监测关注或风险关注。")
    add(table, "explanation", "string", "-", "结果解释。")

    table = "analysis_summary.json"
    add(table, "generated_at", "datetime", "-", "分析结果生成时间。")
    add(table, "output_dir", "string", "-", "分析结果输出目录。")
    add(table, "descriptive_statistics_rows", "integer", "行", "描述统计结果行数。")
    add(table, "time_series_summary_rows", "integer", "行", "时间序列结果行数。")
    add(table, "correlation_pairs", "integer", "组", "相关性变量对数量。")
    add(table, "cluster_rows", "integer", "行", "聚类结果行数。")
    add(table, "cluster_counts", "object", "-", "不同风险等级的记录数量。")
    add(table, "anomaly_rows", "integer", "行", "异常检测结果行数。")
    add(table, "keyword_sentiment_rows", "integer", "行", "关键词分析结果行数。")
    add(table, "top_correlations", "array", "-", "相关性最高的变量组合。")
    add(table, "top_anomalies", "array", "-", "异常程度最高的记录。")
    add(table, "top_keywords", "array", "-", "出现频次最高的关键词。")
    add(table, "core_conclusions", "array", "-", "核心分析结论。")
    add(table, "application_directions", "array", "-", "应用方向。")
    add(table, "feasibility", "object", "-", "技术、成本、需求和数据可用性分析。")

    return rows


def run_analysis(processed_dir: Path, output_dir: Path) -> Dict[str, object]:
    """执行完整数据分析流程。"""
    output_dir.mkdir(parents=True, exist_ok=True)

    chinacdc_rows = read_csv(processed_dir / "chinacdc_monthly_clean.csv")
    respiratory_rows = read_csv(processed_dir / "respiratory_weekly_clean.csv")
    influenza_rows = read_csv(processed_dir / "influenza_weekly_clean.csv")
    province_weekly_rows = read_csv(processed_dir / "province_weekly_features.csv")

    descriptive_rows = generate_descriptive_statistics(
        chinacdc_rows,
        respiratory_rows,
        influenza_rows,
        province_weekly_rows,
    )
    write_csv(
        output_dir / "descriptive_statistics.csv",
        descriptive_rows,
        [
            "analysis_type",
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
            "note",
        ],
    )

    time_series_rows = generate_time_series_summary(
        chinacdc_rows,
        respiratory_rows,
        influenza_rows,
    )
    write_csv(
        output_dir / "time_series_summary.csv",
        time_series_rows,
        [
            "series_name",
            "frequency",
            "start_period",
            "end_period",
            "observations",
            "latest_value",
            "previous_period",
            "previous_value",
            "change",
            "change_percent",
            "recent_4_period_avg",
            "trend_direction",
        ],
    )

    correlation_rows = generate_correlation_matrix(province_weekly_rows)
    write_csv(
        output_dir / "correlation_matrix.csv",
        correlation_rows,
        [
            "x_variable",
            "y_variable",
            "sample_size",
            "pearson_correlation",
            "abs_correlation",
            "strength",
            "direction",
        ],
    )

    cluster_rows = generate_cluster_results(province_weekly_rows)
    cluster_fields = [
        "region",
        "city",
        "report_year",
        "report_week",
        "year_week",
        "cluster_id",
        "risk_level",
        "risk_score",
    ] + WEATHER_FIELDS + CLUSTER_HEALTH_FIELDS
    write_csv(output_dir / "cluster_results.csv", cluster_rows, cluster_fields)

    anomaly_rows = generate_anomaly_results(
        chinacdc_rows,
        respiratory_rows,
        influenza_rows,
    )
    write_csv(
        output_dir / "anomaly_detection_results.csv",
        anomaly_rows,
        [
            "series_name",
            "period",
            "value",
            "mean",
            "stddev",
            "z_score",
            "anomaly_type",
        ],
    )

    keyword_rows = generate_keyword_sentiment_analysis(
        chinacdc_rows,
        respiratory_rows,
        influenza_rows,
    )
    write_csv(
        output_dir / "keyword_sentiment_analysis.csv",
        keyword_rows,
        [
            "source_table",
            "keyword",
            "category",
            "occurrences",
            "document_count",
            "attention_label",
            "explanation",
        ],
    )

    summary = build_summary(
        descriptive_rows,
        time_series_rows,
        correlation_rows,
        cluster_rows,
        anomaly_rows,
        keyword_rows,
        output_dir,
    )
    with (output_dir / "analysis_summary.json").open("w", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)

    dictionary_rows = build_analysis_dictionary_rows()
    write_csv(
        output_dir / "analysis_data_dictionary.csv",
        dictionary_rows,
        ["table_name", "field_name", "data_type", "unit", "description"],
    )

    return summary


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数。"""
    parser = argparse.ArgumentParser(description="成员B数据分析脚本")
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=PROCESSED_DIR,
        help="清洗后数据目录，默认 data/processed",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ANALYSIS_DIR,
        help="分析结果输出目录，默认 data/analysis",
    )
    return parser


def main() -> None:
    """命令行入口。"""
    args = build_parser().parse_args()
    summary = run_analysis(args.processed_dir, args.output_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
