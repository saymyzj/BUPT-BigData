import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
REPORT_PATH = PROJECT_ROOT / "data" / "processed" / "quality_summary.json"


def inspect_csv(path: Path, natural_key: list[str], required_fields: list[str]) -> dict:
    frame = pd.read_csv(path)
    duplicate_count = int(frame.duplicated(natural_key).sum()) if natural_key else 0
    missing_required = {
        field: int(frame[field].isna().sum())
        for field in required_fields
        if field in frame.columns
    }
    summary = {
        "file": str(path.relative_to(PROJECT_ROOT)),
        "rows": int(len(frame)),
        "columns": int(len(frame.columns)),
        "duplicate_count": duplicate_count,
        "missing_required": missing_required,
    }
    if "trade_date" in frame.columns and len(frame) > 0:
        summary["trade_date_min"] = str(frame["trade_date"].min())
        summary["trade_date_max"] = str(frame["trade_date"].max())
        summary["ticker_count"] = int(frame["ticker"].nunique())
    if "fiscal_year" in frame.columns and len(frame) > 0:
        summary["fiscal_year_min"] = int(frame["fiscal_year"].min())
        summary["fiscal_year_max"] = int(frame["fiscal_year"].max())
        summary["ticker_count"] = int(frame["ticker"].nunique())
    return summary


def run_quality_check() -> dict:
    stock_path = DATA_DIR / "interim" / "stock_daily_market.csv"
    rd_path = DATA_DIR / "interim" / "rd_annual_sec.csv"
    merged_path = DATA_DIR / "processed" / "market_rd_daily_merged.csv"
    raw_counts = {
        "yahoo_chart_json": len(list((DATA_DIR / "raw" / "yahoo_chart").glob("*.json"))),
        "sec_companyfacts_json": len(list((DATA_DIR / "raw" / "sec_companyfacts").glob("*.json"))),
        "source_url_sidecars": len(list((DATA_DIR / "raw").glob("**/*.url"))),
    }
    summary = {
        "raw_counts": raw_counts,
        "tables": [
            inspect_csv(
                stock_path,
                ["ticker", "trade_date"],
                ["ticker", "trade_date", "close", "source_url", "raw_file"],
            ),
            inspect_csv(
                rd_path,
                ["ticker", "fiscal_year"],
                ["ticker", "fiscal_year", "rd_expense_usd", "source_url", "raw_file"],
            ),
            inspect_csv(
                merged_path,
                ["ticker", "trade_date"],
                ["ticker", "trade_date", "close", "rd_expense_usd", "source_url", "raw_file"],
            ),
        ],
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


if __name__ == "__main__":
    print(json.dumps(run_quality_check(), ensure_ascii=False, indent=2))
