from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = ROOT.parent / "数据分析skill复用测试"
PROCESSED = SOURCE_ROOT / "data" / "processed"
ANALYSIS = SOURCE_ROOT / "data" / "analysis"
OUTPUT = ROOT / "data" / "dashboard-data.json"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def to_float(value: str | None, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    try:
        return float(value)
    except ValueError:
        return default


def round_float(value: float, digits: int = 4) -> float:
    return round(value, digits)


def inventory(path: Path) -> dict[str, object]:
    rows = read_csv(path)
    fields = list(rows[0].keys()) if rows else []
    date_fields = [f for f in fields if "date" in f or "year" in f or "month" in f or "period" in f]
    ticker_count = len({r.get("ticker", "") for r in rows if r.get("ticker")})
    time_values: list[str] = []
    for field in date_fields:
        time_values.extend([r.get(field, "") for r in rows if r.get(field)])
    return {
        "file": str(path.relative_to(SOURCE_ROOT)).replace("\\", "/"),
        "rows": len(rows),
        "columns": len(fields),
        "fields": fields,
        "time_fields": date_fields,
        "time_range": [min(time_values), max(time_values)] if time_values else [],
        "ticker_count": ticker_count,
        "missing_key_fields": [f for f in ["ticker", "trade_date", "fiscal_year"] if f in fields and any(not r.get(f) for r in rows)],
    }


def build_monthly_trend(stock_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in stock_rows:
        grouped[row["trade_month"]].append(row)

    trend = []
    for month, rows in sorted(grouped.items()):
        closes = [to_float(r["adj_close"]) for r in rows if r.get("adj_close")]
        returns = [to_float(r["return_pct"]) for r in rows if r.get("return_pct")]
        volume = sum(to_float(r["volume"]) for r in rows)
        trend.append(
            {
                "period": month,
                "avg_adj_close": round_float(sum(closes) / len(closes), 3) if closes else 0,
                "avg_return_pct": round_float(sum(returns) / len(returns), 3) if returns else 0,
                "total_volume_b": round_float(volume / 1_000_000_000, 3),
            }
        )
    return trend


def build_company_trend(stock_rows: list[dict[str, str]]) -> dict[str, list[dict[str, object]]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in stock_rows:
        grouped[(row["ticker"], row["trade_month"])].append(row)

    result: dict[str, list[dict[str, object]]] = defaultdict(list)
    for (ticker, month), rows in sorted(grouped.items()):
        closes = [to_float(r["adj_close"]) for r in rows if r.get("adj_close")]
        returns = [to_float(r["return_pct"]) for r in rows if r.get("return_pct")]
        result[ticker].append(
            {
                "period": month,
                "avg_adj_close": round_float(sum(closes) / len(closes), 3) if closes else 0,
                "avg_return_pct": round_float(sum(returns) / len(returns), 3) if returns else 0,
            }
        )
    return result


def build_industry_summary(features: list[dict[str, str]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in features:
        grouped[row["industry_group"]].append(row)

    summary = []
    for industry, rows in sorted(grouped.items()):
        rd = [to_float(r["latest_rd_expense_busd"]) for r in rows]
        vol = [to_float(r["daily_return_volatility"]) for r in rows]
        summary.append(
            {
                "industry": industry,
                "companies": len(rows),
                "avg_rd_busd": round_float(sum(rd) / len(rd), 3) if rd else 0,
                "avg_volatility": round_float(sum(vol) / len(vol), 4) if vol else 0,
            }
        )
    return summary


def build_companies(features: list[dict[str, str]], clusters: list[dict[str, str]]) -> list[dict[str, object]]:
    cluster_by_ticker = {r["ticker"]: r for r in clusters}
    companies = []
    for row in features:
        cluster = cluster_by_ticker.get(row["ticker"], {})
        companies.append(
            {
                "ticker": row["ticker"],
                "company_name": row["company_name"],
                "industry_group": row["industry_group"],
                "avg_close": round_float(to_float(row["avg_close"]), 3),
                "year_end_adj_close": round_float(to_float(row["year_end_adj_close"]), 3),
                "total_volume_b": round_float(to_float(row["total_volume"]) / 1_000_000_000, 3),
                "avg_daily_return": round_float(to_float(row["avg_daily_return"]) * 100, 4),
                "daily_return_volatility": round_float(to_float(row["daily_return_volatility"]), 4),
                "latest_rd_expense_busd": round_float(to_float(row["latest_rd_expense_busd"]), 3),
                "risk_level": cluster.get("risk_level", "unclustered"),
                "risk_score": round_float(to_float(cluster.get("risk_score")), 4),
                "cluster_id": cluster.get("cluster_id", ""),
            }
        )
    return sorted(companies, key=lambda item: item["risk_score"], reverse=True)


def build_anomalies(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    anomalies = []
    for row in rows:
        ticker = row["series_name"].replace("_return_pct", "")
        anomalies.append(
            {
                "ticker": ticker,
                "period": row["period"],
                "value": round_float(to_float(row["value"]), 3),
                "z_score": round_float(to_float(row["z_score"]), 3),
                "anomaly_type": row["anomaly_type"],
            }
        )
    return sorted(anomalies, key=lambda item: abs(item["z_score"]), reverse=True)[:80]


def build_correlation(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    return [
        {
            "x": row["x_variable"],
            "y": row["y_variable"],
            "value": round_float(to_float(row["pearson_correlation"]), 3),
            "strength": row["strength"],
            "direction": row["direction"],
            "sample_size": int(to_float(row["sample_size"])),
        }
        for row in rows
    ]


def main() -> None:
    stock_rows = read_csv(PROCESSED / "stock_daily_clean.csv")
    features = read_csv(PROCESSED / "company_2024_features.csv")
    clusters = read_csv(ANALYSIS / "cluster_results.csv")
    anomalies = read_csv(ANALYSIS / "anomaly_detection_results.csv")
    correlations = read_csv(ANALYSIS / "correlation_matrix.csv")
    keywords = read_csv(ANALYSIS / "keyword_sentiment_analysis.csv")

    risk_counts = Counter(r.get("risk_level", "unknown") for r in clusters)
    payload = {
        "meta": {
            "title": "医药健康公司研发投入与市场风险可视化 Dashboard",
            "source_root": str(SOURCE_ROOT),
            "generated_from": [
                "data/processed/stock_daily_clean.csv",
                "data/processed/rd_annual_clean.csv",
                "data/processed/company_2024_features.csv",
                "data/analysis/cluster_results.csv",
                "data/analysis/correlation_matrix.csv",
                "data/analysis/anomaly_detection_results.csv",
                "data/analysis/keyword_sentiment_analysis.csv",
            ],
            "stock_rows": len(stock_rows),
            "company_count": len({r["ticker"] for r in features}),
            "months": sorted({r["trade_month"] for r in stock_rows}),
            "industries": sorted({r["industry_group"] for r in features}),
            "risk_counts": dict(risk_counts),
        },
        "inventory": [
            inventory(PROCESSED / "stock_daily_clean.csv"),
            inventory(PROCESSED / "rd_annual_clean.csv"),
            inventory(PROCESSED / "company_2024_features.csv"),
            inventory(ANALYSIS / "cluster_results.csv"),
            inventory(ANALYSIS / "correlation_matrix.csv"),
            inventory(ANALYSIS / "anomaly_detection_results.csv"),
        ],
        "monthly_trend": build_monthly_trend(stock_rows),
        "company_trend": build_company_trend(stock_rows),
        "industry_summary": build_industry_summary(features),
        "companies": build_companies(features, clusters),
        "anomalies": build_anomalies(anomalies),
        "correlations": build_correlation(correlations),
        "keywords": keywords,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"dashboard data written: {OUTPUT}")
    print(f"companies: {payload['meta']['company_count']}")
    print(f"stock rows: {payload['meta']['stock_rows']}")
    print(f"months: {payload['meta']['months'][0]} to {payload['meta']['months'][-1]}")


if __name__ == "__main__":
    main()
