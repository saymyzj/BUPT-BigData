import argparse
from pathlib import Path

from crawlers.chinacdc_monthly import ChinaCdcMonthlyCrawler
from crawlers.influenza_weekly import InfluenzaWeeklyCrawler
from crawlers.respiratory_weekly import RespiratoryWeeklyCrawler
from crawlers.weather_daily import WeatherDailyCrawler


CRAWLERS = {
    "chinacdc_monthly": ChinaCdcMonthlyCrawler,
    "influenza_weekly": InfluenzaWeeklyCrawler,
    "respiratory_weekly": RespiratoryWeeklyCrawler,
    "weather_daily": WeatherDailyCrawler,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="呼吸道传染病数据采集爬虫")
    parser.add_argument(
        "source",
        choices=sorted(CRAWLERS.keys()),
        help="需要采集的数据源标识",
    )
    parser.add_argument("--limit", type=int, help="最多采集的报告页面数量")
    parser.add_argument(
        "--parse-only",
        action="store_true",
        help="只解析本地已缓存的原始文件，不发起网络请求",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="忽略本地缓存，重新请求网页",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="全局下载线程数；同一域名仍会单独限速",
    )
    parser.add_argument("--min-delay", type=float, default=1.0, help="同一域名最小请求间隔")
    parser.add_argument("--max-delay", type=float, default=3.0, help="同一域名最大请求间隔")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    crawler_cls = CRAWLERS[args.source]
    crawler = crawler_cls(
        min_delay=args.min_delay,
        max_delay=args.max_delay,
        max_workers=args.workers,
        force=args.force,
    )
    output_path: Path = crawler.run(limit=args.limit, parse_only=args.parse_only)
    print(output_path)


if __name__ == "__main__":
    main()
