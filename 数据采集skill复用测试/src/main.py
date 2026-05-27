import argparse
import json
from pathlib import Path

from crawlers.market_rd_crawler import MarketRdCrawler
from quality_check import run_quality_check


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="医药上市公司研发投入与市场表现数据采集")
    parser.add_argument("--limit", type=int, help="仅采集前 N 家公司，用于试采集")
    parser.add_argument("--start-date", default="2024-01-01", help="行情开始日期")
    parser.add_argument("--end-date", default="2024-12-31", help="行情结束日期")
    parser.add_argument("--parse-only", action="store_true", help="只解析本地缓存，不联网")
    parser.add_argument("--force", action="store_true", help="忽略缓存，重新下载原始 JSON")
    parser.add_argument("--min-delay", type=float, default=0.2, help="最小请求间隔")
    parser.add_argument("--max-delay", type=float, default=0.8, help="最大请求间隔")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    crawler = MarketRdCrawler(
        start_date=args.start_date,
        end_date=args.end_date,
        min_delay=args.min_delay,
        max_delay=args.max_delay,
        force=args.force,
    )
    paths = crawler.run(limit=args.limit, parse_only=args.parse_only)
    summary = run_quality_check()
    print(json.dumps({"outputs": {k: str(v) for k, v in paths.items()}, "quality": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
