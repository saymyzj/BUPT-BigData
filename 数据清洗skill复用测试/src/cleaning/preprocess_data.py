"""Clean and preprocess pharmaceutical R&D and stock market datasets.

Inputs:
    data/interim/rd_annual_sec.csv
    data/interim/stock_daily_market.csv

Outputs:
    data/processed/rd_annual_clean.csv
    data/processed/stock_daily_clean.csv
    data/processed/company_2024_features.csv
    data/processed/data_dictionary.csv
    data/processed/quality_summary.json

Design principles:
    Preserve source traceability, avoid subjective imputation, keep stable
    output schemas, and record quality checks for reproducibility.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERIM_DIR = PROJECT_ROOT / "data" / "interim"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

MISSING_TOKENS = {"", "-", "--", "—", "NA", "N/A", "NULL", "null", "None", "none", "nan", "NaN"}

RD_COLUMNS = [
    "ticker",
    "company_name",
    "industry_group",
    "cik",
    "fiscal_year",
    "rd_expense_usd",
    "rd_expense_musd",
    "rd_expense_busd",
    "sec_fact_tag",
    "form",
    "filed_date",
    "source_url",
    "crawl_time",
    "raw_file",
]

STOCK_COLUMNS = [
    "ticker",
    "company_name",
    "industry_group",
    "trade_date",
    "trade_year",
    "trade_month",
    "open",
    "high",
    "low",
    "close",
    "adj_close",
    "volume",
    "daily_return",
    "return_pct",
    "source_url",
    "crawl_time",
    "raw_file",
]

FEATURE_COLUMNS = [
    "ticker",
    "company_name",
    "industry_group",
    "trade_year",
    "trading_days",
    "avg_close",
    "year_end_adj_close",
    "total_volume",
    "avg_daily_return",
    "daily_return_volatility",
    "latest_rd_fiscal_year",
    "latest_rd_expense_usd",
    "latest_rd_expense_musd",
    "latest_rd_expense_busd",
]


def read_csv(path: Path) -> pd.DataFrame:
    """Read a CSV file with stable string handling for identifiers."""
    return pd.read_csv(path, dtype={"ticker": "string", "cik": "string"}, keep_default_na=True)


def write_csv(df: pd.DataFrame, path: Path, columns: list[str]) -> None:
    """Write a CSV with a fixed column order and UTF-8 BOM for spreadsheet tools."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.loc[:, columns].to_csv(path, index=False, encoding="utf-8-sig")


def clean_text(value: Any) -> Any:
    """Normalize whitespace and missing-value tokens in text cells."""
    if pd.isna(value):
        return pd.NA
    text = str(value).replace("\u3000", " ").strip()
    text = re.sub(r"\s+", " ", text)
    if text in MISSING_TOKENS:
        return pd.NA
    return text


def parse_float(value: Any) -> float | pd.NA:
    """Parse numeric text containing commas, percent signs, or simple unit labels."""
    if pd.isna(value):
        return pd.NA
    text = str(value).strip()
    if text in MISSING_TOKENS:
        return pd.NA
    text = text.replace(",", "").replace("%", "")
    text = re.sub(r"[^0-9eE+\-.]", "", text)
    if text in MISSING_TOKENS:
        return pd.NA
    return float(text)


def parse_int(value: Any) -> int | pd.NA:
    """Parse integer text after applying the shared numeric normalization."""
    parsed = parse_float(value)
    if pd.isna(parsed):
        return pd.NA
    return int(parsed)


def parse_date(value: Any) -> str | pd.NA:
    """Parse a date-like value and return YYYY-MM-DD."""
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return pd.NA
    return parsed.strftime("%Y-%m-%d")


def parse_datetime(value: Any) -> str | pd.NA:
    """Parse a datetime-like value and return an ISO timestamp string."""
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(parsed):
        return pd.NA
    return parsed.isoformat()


def normalize_text_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Apply shared text cleanup to selected columns."""
    cleaned = df.copy()
    for column in columns:
        cleaned[column] = cleaned[column].map(clean_text).astype("string")
    return cleaned


def deduplicate(df: pd.DataFrame, keys: list[str]) -> tuple[pd.DataFrame, int]:
    """Sort and drop duplicate business keys, returning the dropped count."""
    before = len(df)
    cleaned = df.drop_duplicates(subset=keys, keep="first").reset_index(drop=True)
    return cleaned, before - len(cleaned)


def missing_count(df: pd.DataFrame) -> dict[str, int]:
    """Count missing cells by field."""
    return {column: int(df[column].isna().sum()) for column in df.columns}


def clean_rd_annual(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Clean annual SEC R&D expenditure records."""
    text_columns = [
        "ticker",
        "company_name",
        "industry_group",
        "cik",
        "sec_fact_tag",
        "form",
        "source_url",
        "raw_file",
    ]
    cleaned = normalize_text_columns(df, text_columns)
    cleaned["ticker"] = cleaned["ticker"].str.upper()
    cleaned["cik"] = cleaned["cik"].str.replace(r"\D", "", regex=True).str.zfill(10)
    cleaned["fiscal_year"] = cleaned["fiscal_year"].map(parse_int).astype("Int64")
    cleaned["rd_expense_usd"] = cleaned["rd_expense_usd"].map(parse_float).astype("Float64")
    cleaned["rd_expense_musd"] = cleaned["rd_expense_musd"].map(parse_float).astype("Float64")
    cleaned["rd_expense_busd"] = (cleaned["rd_expense_usd"] / 1_000_000_000).astype("Float64")
    cleaned["filed_date"] = cleaned["filed_date"].map(parse_date).astype("string")
    cleaned["crawl_time"] = cleaned["crawl_time"].map(parse_datetime).astype("string")
    cleaned = cleaned.sort_values(["ticker", "fiscal_year", "filed_date"], na_position="last")
    cleaned, duplicates_dropped = deduplicate(cleaned, ["ticker", "fiscal_year"])
    return cleaned.loc[:, RD_COLUMNS], {"duplicates_dropped": duplicates_dropped}


def clean_stock_daily(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Clean daily stock market records."""
    text_columns = ["ticker", "company_name", "industry_group", "source_url", "raw_file"]
    cleaned = normalize_text_columns(df, text_columns)
    cleaned["ticker"] = cleaned["ticker"].str.upper()
    cleaned["trade_date"] = cleaned["trade_date"].map(parse_date).astype("string")
    trade_dt = pd.to_datetime(cleaned["trade_date"], errors="coerce")
    cleaned["trade_year"] = trade_dt.dt.year.astype("Int64")
    cleaned["trade_month"] = trade_dt.dt.strftime("%Y-%m").astype("string")
    for column in ["open", "high", "low", "close", "adj_close", "daily_return"]:
        cleaned[column] = cleaned[column].map(parse_float).astype("Float64")
    cleaned["volume"] = cleaned["volume"].map(parse_int).astype("Int64")
    cleaned["return_pct"] = (cleaned["daily_return"] * 100).astype("Float64")
    cleaned["crawl_time"] = cleaned["crawl_time"].map(parse_datetime).astype("string")
    cleaned = cleaned.sort_values(["ticker", "trade_date"], na_position="last")
    cleaned, duplicates_dropped = deduplicate(cleaned, ["ticker", "trade_date"])
    return cleaned.loc[:, STOCK_COLUMNS], {"duplicates_dropped": duplicates_dropped}


def build_features(stock: pd.DataFrame, rd: pd.DataFrame) -> pd.DataFrame:
    """Build ticker-level 2024 features from daily stock data and latest R&D values."""
    stock_2024 = stock[stock["trade_year"] == 2024].copy()
    latest_price = (
        stock_2024.sort_values(["ticker", "trade_date"])
        .groupby("ticker", as_index=False)
        .tail(1)[["ticker", "adj_close"]]
        .rename(columns={"adj_close": "year_end_adj_close"})
    )
    grouped = (
        stock_2024.groupby(["ticker", "company_name", "industry_group", "trade_year"], dropna=False)
        .agg(
            trading_days=("trade_date", "count"),
            avg_close=("close", "mean"),
            total_volume=("volume", "sum"),
            avg_daily_return=("daily_return", "mean"),
            daily_return_volatility=("daily_return", "std"),
        )
        .reset_index()
    )
    features = grouped.merge(latest_price, on="ticker", how="left")
    latest_rd = (
        rd[rd["fiscal_year"] <= 2024]
        .sort_values(["ticker", "fiscal_year"])
        .groupby("ticker", as_index=False)
        .tail(1)[["ticker", "fiscal_year", "rd_expense_usd", "rd_expense_musd", "rd_expense_busd"]]
        .rename(
            columns={
                "fiscal_year": "latest_rd_fiscal_year",
                "rd_expense_usd": "latest_rd_expense_usd",
                "rd_expense_musd": "latest_rd_expense_musd",
                "rd_expense_busd": "latest_rd_expense_busd",
            }
        )
    )
    features = features.merge(latest_rd, on="ticker", how="left")
    return features.loc[:, FEATURE_COLUMNS].sort_values("ticker").reset_index(drop=True)


def build_dictionary_rows() -> list[dict[str, str]]:
    """Create dictionary rows covering all processed output fields."""
    specs = {
        "rd_annual_clean": {
            "ticker": ("string", "-", "保留为空并检查来源", "ticker", "股票代码，统一为大写"),
            "company_name": ("string", "-", "保留为空并检查来源", "company_name", "公司名称"),
            "industry_group": ("string", "-", "保留为空并检查来源", "industry_group", "行业分组"),
            "cik": ("string", "-", "保留为空并检查来源", "cik", "SEC CIK，标准化为 10 位字符串"),
            "fiscal_year": ("integer", "year", "关键字段不插补", "fiscal_year", "SEC 报告财年"),
            "rd_expense_usd": ("float", "USD", "关键指标不插补", "rd_expense_usd", "研发费用，美元"),
            "rd_expense_musd": ("float", "million USD", "关键指标不插补", "rd_expense_musd", "研发费用，百万美元"),
            "rd_expense_busd": ("float", "billion USD", "由 rd_expense_usd 派生", "rd_expense_usd / 1e9", "研发费用，十亿美元"),
            "sec_fact_tag": ("string", "-", "保留为空并检查来源", "sec_fact_tag", "SEC XBRL fact 标签"),
            "form": ("string", "-", "保留为空并检查来源", "form", "SEC 申报表类型"),
            "filed_date": ("date", "-", "保留为空并检查来源", "filed_date", "SEC 文件提交日期"),
            "source_url": ("string", "-", "保留为空并检查来源", "source_url", "来源接口 URL"),
            "crawl_time": ("datetime", "-", "保留为空并检查来源", "crawl_time", "采集时间"),
            "raw_file": ("string", "-", "保留为空并检查来源", "raw_file", "原始缓存文件路径"),
        },
        "stock_daily_clean": {
            "ticker": ("string", "-", "保留为空并检查来源", "ticker", "股票代码，统一为大写"),
            "company_name": ("string", "-", "保留为空并检查来源", "company_name", "公司名称"),
            "industry_group": ("string", "-", "保留为空并检查来源", "industry_group", "行业分组"),
            "trade_date": ("date", "-", "关键字段不插补", "trade_date", "交易日期"),
            "trade_year": ("integer", "year", "由 trade_date 派生", "trade_date", "交易年份"),
            "trade_month": ("string", "month", "由 trade_date 派生", "trade_date", "交易月份，YYYY-MM"),
            "open": ("float", "USD/share", "关键指标不插补", "open", "开盘价"),
            "high": ("float", "USD/share", "关键指标不插补", "high", "最高价"),
            "low": ("float", "USD/share", "关键指标不插补", "low", "最低价"),
            "close": ("float", "USD/share", "关键指标不插补", "close", "收盘价"),
            "adj_close": ("float", "USD/share", "关键指标不插补", "adj_close", "复权收盘价"),
            "volume": ("integer", "shares", "关键指标不插补", "volume", "成交量"),
            "daily_return": ("float", "ratio", "首个交易日结构性空值保留", "daily_return", "日收益率"),
            "return_pct": ("float", "percent", "由 daily_return 派生", "daily_return * 100", "日收益率百分比"),
            "source_url": ("string", "-", "保留为空并检查来源", "source_url", "来源接口 URL"),
            "crawl_time": ("datetime", "-", "保留为空并检查来源", "crawl_time", "采集时间"),
            "raw_file": ("string", "-", "保留为空并检查来源", "raw_file", "原始缓存文件路径"),
        },
        "company_2024_features": {
            "ticker": ("string", "-", "来自股票表", "ticker", "股票代码"),
            "company_name": ("string", "-", "来自股票表", "company_name", "公司名称"),
            "industry_group": ("string", "-", "来自股票表", "industry_group", "行业分组"),
            "trade_year": ("integer", "year", "来自 trade_date", "trade_year", "交易年份"),
            "trading_days": ("integer", "days", "由股票日表聚合", "count(trade_date)", "年度交易日数量"),
            "avg_close": ("float", "USD/share", "由股票日表聚合", "mean(close)", "年度平均收盘价"),
            "year_end_adj_close": ("float", "USD/share", "由股票日表聚合", "last(adj_close)", "年末复权收盘价"),
            "total_volume": ("integer", "shares", "由股票日表聚合", "sum(volume)", "年度总成交量"),
            "avg_daily_return": ("float", "ratio", "由股票日表聚合", "mean(daily_return)", "平均日收益率"),
            "daily_return_volatility": ("float", "ratio", "由股票日表聚合", "std(daily_return)", "日收益率波动率"),
            "latest_rd_fiscal_year": ("integer", "year", "无可用研发记录则为空", "rd_annual_clean", "不晚于 2024 年的最新研发费用财年"),
            "latest_rd_expense_usd": ("float", "USD", "无可用研发记录则为空", "rd_annual_clean", "最新可用研发费用，美元"),
            "latest_rd_expense_musd": ("float", "million USD", "无可用研发记录则为空", "rd_annual_clean", "最新可用研发费用，百万美元"),
            "latest_rd_expense_busd": ("float", "billion USD", "无可用研发记录则为空", "rd_annual_clean", "最新可用研发费用，十亿美元"),
        },
    }
    rows: list[dict[str, str]] = []
    for table_name, fields in specs.items():
        for field_name, (data_type, unit, strategy, source_field, description) in fields.items():
            rows.append(
                {
                    "table_name": table_name,
                    "field_name": field_name,
                    "data_type": data_type,
                    "unit": unit,
                    "missing_value_strategy": strategy,
                    "source_field": source_field,
                    "description": description,
                }
            )
    return rows


def build_quality_summary(
    raw_counts: dict[str, int],
    outputs: dict[str, pd.DataFrame],
    duplicate_counts: dict[str, int],
) -> dict[str, Any]:
    """Build a table-level quality summary for processed outputs."""
    return {
        "input_rows": raw_counts,
        "output_rows": {name: int(len(df)) for name, df in outputs.items()},
        "duplicates_dropped": duplicate_counts,
        "missing_cells_by_field": {name: missing_count(df) for name, df in outputs.items()},
        "feature_columns": {"company_2024_features": int(outputs["company_2024_features"].shape[1])},
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output_dir": str(PROCESSED_DIR),
        "notes": [
            "stock_daily_clean.daily_return 的空值主要来自每个 ticker 首个交易日，属于收益率计算的结构性空值。",
            "关键金额、价格和收益率指标未做主观插补。",
        ],
        "output_files": [
            "rd_annual_clean.csv",
            "stock_daily_clean.csv",
            "company_2024_features.csv",
            "data_dictionary.csv",
            "quality_summary.json",
        ],
    }


def run_preprocess() -> dict[str, Any]:
    """Run the full preprocessing workflow."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Stage 1: read input tables.
    rd_raw = read_csv(INTERIM_DIR / "rd_annual_sec.csv")
    stock_raw = read_csv(INTERIM_DIR / "stock_daily_market.csv")
    raw_counts = {"rd_annual_sec": int(len(rd_raw)), "stock_daily_market": int(len(stock_raw))}

    # Stage 2: clean individual tables.
    rd_clean, rd_stats = clean_rd_annual(rd_raw)
    stock_clean, stock_stats = clean_stock_daily(stock_raw)

    # Stage 3: build analysis features and metadata outputs.
    features = build_features(stock_clean, rd_clean)
    dictionary = pd.DataFrame(build_dictionary_rows())
    outputs = {
        "rd_annual_clean": rd_clean,
        "stock_daily_clean": stock_clean,
        "company_2024_features": features,
    }
    duplicate_counts = {
        "rd_annual_clean": int(rd_stats["duplicates_dropped"]),
        "stock_daily_clean": int(stock_stats["duplicates_dropped"]),
        "company_2024_features": 0,
    }
    quality_summary = build_quality_summary(raw_counts, outputs, duplicate_counts)

    # Stage 4: write all processed artifacts.
    write_csv(rd_clean, PROCESSED_DIR / "rd_annual_clean.csv", RD_COLUMNS)
    write_csv(stock_clean, PROCESSED_DIR / "stock_daily_clean.csv", STOCK_COLUMNS)
    write_csv(features, PROCESSED_DIR / "company_2024_features.csv", FEATURE_COLUMNS)
    dictionary.to_csv(PROCESSED_DIR / "data_dictionary.csv", index=False, encoding="utf-8-sig")
    (PROCESSED_DIR / "quality_summary.json").write_text(
        json.dumps(quality_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return quality_summary


if __name__ == "__main__":
    summary = run_preprocess()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
