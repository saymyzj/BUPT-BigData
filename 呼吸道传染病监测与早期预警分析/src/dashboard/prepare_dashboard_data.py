"""Build frontend data for the respiratory disease early-warning dashboard."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = ROOT.parent
PROJECT_ROOT = REPO_ROOT / "呼吸道传染病监测与早期预警分析"
PROCESSED = PROJECT_ROOT / "data" / "processed"
ANALYSIS = PROJECT_ROOT / "data" / "analysis"
OUTPUT_FILE = ROOT / "data" / "dashboard-data.js"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def to_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def to_int(value: str | None) -> int | None:
    numeric = to_float(value)
    return int(numeric) if numeric is not None else None


def year_week_key(year_week: str) -> tuple[int, int]:
    year, week = year_week.split("-W")
    return int(year), int(week)


def average_rows(groups: dict[tuple[str, ...], list[float]], field_names: list[str]) -> list[dict[str, object]]:
    rows = []
    for key, values in groups.items():
        row = {field: value for field, value in zip(field_names, key)}
        row["value"] = round(mean(values), 4)
        rows.append(row)
    return rows


def build_resp_trends(resp_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    groups: dict[tuple[str, str, str, str, str], list[float]] = defaultdict(list)
    for row in resp_rows:
        if row.get("metric_type") != "pathogen_positive_rate":
            continue
        rate = to_float(row.get("positive_rate"))
        if rate is None or not row.get("pathogen_name"):
            continue
        groups[
            (
                row["year_week"],
                row["week_start"],
                row["surveillance_scene"],
                row["region_group"] or "全国",
                row["pathogen_name"],
            )
        ].append(rate)
    rows = average_rows(groups, ["year_week", "week_start", "scene", "region_group", "pathogen"])
    return sorted(rows, key=lambda item: (*year_week_key(str(item["year_week"])), str(item["pathogen"])))


def build_ili_series(influenza_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    rows = []
    for row in influenza_rows:
        if row.get("metric_type") != "ili_percent":
            continue
        value = to_float(row.get("metric_percent"))
        if value is None:
            continue
        rows.append(
            {
                "year_week": row["year_week"],
                "week_start": row["week_start"],
                "region_group": row["region_group"],
                "value": value,
            }
        )
    return sorted(rows, key=lambda item: (*year_week_key(str(item["year_week"])), str(item["region_group"])))


def build_outbreak_series(influenza_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    rows = []
    for row in influenza_rows:
        if row.get("metric_type") != "outbreak_count":
            continue
        value = to_float(row.get("outbreak_count") or row.get("indicator_value"))
        if value is None:
            continue
        rows.append({"year_week": row["year_week"], "week_start": row["week_start"], "value": value})
    return sorted(rows, key=lambda item: year_week_key(str(item["year_week"])))


def build_flu_positive_series(influenza_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    rows = []
    for row in influenza_rows:
        if row.get("metric_type") != "lab_result":
            continue
        if row.get("metric_name") != "阳性数(%)":
            continue
        value = to_float(row.get("metric_percent"))
        if value is None:
            continue
        rows.append(
            {
                "year_week": row["year_week"],
                "week_start": row["week_start"],
                "region_group": row["region_group"],
                "value": value,
            }
        )
    return sorted(rows, key=lambda item: (*year_week_key(str(item["year_week"])), str(item["region_group"])))


def build_flu_subtype_series(influenza_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    excluded = {"检测数", "阳性数(%)"}
    rows = []
    for row in influenza_rows:
        if row.get("metric_type") != "lab_result":
            continue
        if row.get("region_group") != "合计":
            continue
        metric_name = row.get("metric_name") or ""
        if metric_name in excluded:
            continue
        value = to_float(row.get("metric_percent"))
        if value is None:
            continue
        rows.append(
            {
                "year_week": row["year_week"],
                "week_start": row["week_start"],
                "subtype": metric_name,
                "value": value,
            }
        )
    return sorted(rows, key=lambda item: (*year_week_key(str(item["year_week"])), str(item["subtype"])))


def build_risk_rows(cluster_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    rows = []
    for row in cluster_rows:
        risk_score = to_float(row.get("risk_score"))
        if risk_score is None:
            continue
        rows.append(
            {
                "region": row["region"],
                "city": row["city"],
                "year_week": row["year_week"],
                "report_year": to_int(row.get("report_year")),
                "report_week": to_int(row.get("report_week")),
                "risk_level": row["risk_level"],
                "risk_score": risk_score,
                "avg_temperature": to_float(row.get("avg_temperature")),
                "avg_humidity": to_float(row.get("avg_humidity")),
                "precipitation_total": to_float(row.get("precipitation_total")),
                "wind_speed": to_float(row.get("wind_speed")),
                "influenza_ili_percent_north": to_float(row.get("influenza_ili_percent_north")),
                "influenza_ili_percent_south": to_float(row.get("influenza_ili_percent_south")),
                "influenza_outbreak_count": to_float(row.get("influenza_outbreak_count")),
                "resp_outpatient_ili_influenza_positive_rate": to_float(
                    row.get("resp_outpatient_ili_influenza_positive_rate")
                ),
                "resp_outpatient_ili_covid_positive_rate": to_float(row.get("resp_outpatient_ili_covid_positive_rate")),
                "resp_hospital_sari_influenza_positive_rate": to_float(
                    row.get("resp_hospital_sari_influenza_positive_rate")
                ),
                "resp_hospital_sari_covid_positive_rate": to_float(row.get("resp_hospital_sari_covid_positive_rate")),
            }
        )
    return sorted(rows, key=lambda item: (*year_week_key(str(item["year_week"])), str(item["city"])))


def build_monthly_disease(chinacdc_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    focus_names = {"新型冠状病毒感染", "流行性感冒", "肺结核", "百日咳", "麻疹", "猩红热"}
    rows = []
    for row in chinacdc_rows:
        if row.get("disease_name") not in focus_names:
            continue
        cases = to_float(row.get("cases"))
        if cases is None:
            continue
        rows.append(
            {
                "period_month": row["period_month"],
                "disease": row["disease_name"],
                "cases": cases,
                "deaths": to_float(row.get("deaths")),
            }
        )
    return sorted(rows, key=lambda item: (str(item["period_month"]), str(item["disease"])))


def build_keywords(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    result = []
    for row in rows:
        result.append(
            {
                "source_table": row["source_table"],
                "keyword": row["keyword"],
                "category": row["category"],
                "occurrences": to_int(row.get("occurrences")) or 0,
                "document_count": to_int(row.get("document_count")) or 0,
                "attention_label": row["attention_label"],
                "explanation": row["explanation"],
            }
        )
    return result


def build_keyword_events(
    respiratory_rows: list[dict[str, str]],
    influenza_rows: list[dict[str, str]],
    chinacdc_rows: list[dict[str, str]],
) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []

    def add_keyword(year: str, keyword: str, source: str, *, pathogen: str = "", scene: str = "") -> None:
        keyword = (keyword or "").strip()
        if not keyword:
            return
        events.append(
            {
                "year": year,
                "keyword": keyword,
                "source_table": source,
                "pathogen": pathogen,
                "scene": scene,
            }
        )

    for row in respiratory_rows:
        year = row.get("report_year", "")
        scene = row.get("surveillance_scene", "")
        pathogen = row.get("pathogen_name", "") or row.get("ranked_pathogen", "")
        add_keyword(year, "监测", "respiratory_weekly_clean", pathogen=pathogen, scene=scene)
        add_keyword(year, pathogen, "respiratory_weekly_clean", pathogen=pathogen, scene=scene)
        add_keyword(year, scene, "respiratory_weekly_clean", pathogen=pathogen, scene=scene)
        if row.get("metric_type") == "pathogen_positive_rate":
            add_keyword(year, "阳性率", "respiratory_weekly_clean", pathogen=pathogen, scene=scene)

    for row in influenza_rows:
        year = row.get("report_year", "")
        region = row.get("region_group", "")
        metric = row.get("metric_name", "")
        subtype = row.get("dominant_subtype", "")
        add_keyword(year, "流感", "influenza_weekly_clean", scene=region)
        add_keyword(year, "监测", "influenza_weekly_clean", scene=region)
        add_keyword(year, metric, "influenza_weekly_clean", scene=region)
        add_keyword(year, subtype, "influenza_weekly_clean", scene=region)
        if row.get("metric_type") == "outbreak_count":
            add_keyword(year, "暴发疫情", "influenza_weekly_clean", scene=region)

    for row in chinacdc_rows:
        year = row.get("report_year", "")
        disease = row.get("disease_name", "")
        add_keyword(year, "疫情", "chinacdc_monthly_clean")
        add_keyword(year, disease, "chinacdc_monthly_clean")
        if row.get("is_respiratory_focus") == "1":
            add_keyword(year, "呼吸道重点病种", "chinacdc_monthly_clean")

    return events


def numeric_analysis_rows(rows: list[dict[str, str]], numeric_fields: list[str]) -> list[dict[str, object]]:
    output = []
    for row in rows:
        item: dict[str, object] = dict(row)
        for field in numeric_fields:
            item[field] = to_float(row.get(field))
        output.append(item)
    return output


def main() -> None:
    respiratory = read_csv(PROCESSED / "respiratory_weekly_clean.csv")
    influenza = read_csv(PROCESSED / "influenza_weekly_clean.csv")
    chinacdc = read_csv(PROCESSED / "chinacdc_monthly_clean.csv")
    clusters = build_risk_rows(read_csv(ANALYSIS / "cluster_results.csv"))
    trends = build_resp_trends(respiratory)
    ili_series = build_ili_series(influenza)
    outbreak_series = build_outbreak_series(influenza)
    flu_positive_series = build_flu_positive_series(influenza)
    flu_subtype_series = build_flu_subtype_series(influenza)
    monthly_disease = build_monthly_disease(chinacdc)

    weeks = sorted({str(row["year_week"]) for row in trends} | {str(row["year_week"]) for row in clusters}, key=year_week_key)
    pathogens = sorted({str(row["pathogen"]) for row in trends})
    scenes = sorted({str(row["scene"]) for row in trends})
    region_groups = sorted({str(row["region_group"]) for row in trends})
    cities = sorted({str(row["city"]) for row in clusters})
    years = sorted({year_week_key(week)[0] for week in weeks})

    latest_week = weeks[-1]
    latest_trends = [row for row in trends if row["year_week"] == latest_week]
    latest_pathogen_avg = Counter()
    latest_pathogen_count = Counter()
    for row in latest_trends:
        latest_pathogen_avg[str(row["pathogen"])] += float(row["value"])
        latest_pathogen_count[str(row["pathogen"])] += 1
    latest_pathogens = [
        {
            "pathogen": pathogen,
            "value": round(total / latest_pathogen_count[pathogen], 4),
        }
        for pathogen, total in latest_pathogen_avg.items()
    ]
    latest_pathogens.sort(key=lambda item: item["value"], reverse=True)

    risk_counts = Counter(row["risk_level"] for row in clusters)
    high_risk_rows = [row for row in clusters if row["risk_level"] == "高风险"]

    payload = {
        "meta": {
            "project": "呼吸道传染病监测与早期预警分析",
            "minWeek": weeks[0],
            "maxWeek": weeks[-1],
            "years": years,
            "respiratoryRows": len(respiratory),
            "influenzaRows": len(influenza),
            "clusterRows": len(clusters),
            "highRiskRows": len(high_risk_rows),
        },
        "filters": {
            "weeks": weeks,
            "years": years,
            "pathogens": pathogens,
            "scenes": scenes,
            "regionGroups": region_groups,
            "cities": cities,
        },
        "respiratoryTrends": trends,
        "iliSeries": ili_series,
        "outbreakSeries": outbreak_series,
        "fluPositiveSeries": flu_positive_series,
        "fluSubtypeSeries": flu_subtype_series,
        "monthlyDisease": monthly_disease,
        "latestPathogens": latest_pathogens,
        "riskRows": clusters,
        "riskCounts": dict(risk_counts),
        "anomalies": numeric_analysis_rows(
            read_csv(ANALYSIS / "anomaly_detection_results.csv"),
            ["value", "mean", "stddev", "z_score"],
        ),
        "correlations": numeric_analysis_rows(
            read_csv(ANALYSIS / "correlation_matrix.csv"),
            ["sample_size", "pearson_correlation", "abs_correlation"],
        ),
        "timeSeriesSummary": numeric_analysis_rows(
            read_csv(ANALYSIS / "time_series_summary.csv"),
            ["observations", "latest_value", "previous_value", "change", "change_percent", "recent_4_period_avg"],
        ),
        "keywords": build_keywords(read_csv(ANALYSIS / "keyword_sentiment_analysis.csv")),
        "keywordEvents": build_keyword_events(respiratory, influenza, chinacdc),
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        "window.DASHBOARD_DATA = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    print(f"wrote {OUTPUT_FILE}")
    print(
        json.dumps(
            {
                "weeks": [weeks[0], weeks[-1]],
                "pathogens": len(pathogens),
                "cities": len(cities),
                "trendRows": len(trends),
                "riskRows": len(clusters),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
