import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

from crawlers.base import BaseCrawler
from parsers.normalizers import parse_float


PROVINCIAL_CAPITALS = [
    {"region": "北京", "city": "北京", "latitude": 39.9042, "longitude": 116.4074},
    {"region": "天津", "city": "天津", "latitude": 39.3434, "longitude": 117.3616},
    {"region": "河北", "city": "石家庄", "latitude": 38.0428, "longitude": 114.5149},
    {"region": "山西", "city": "太原", "latitude": 37.8706, "longitude": 112.5489},
    {"region": "内蒙古", "city": "呼和浩特", "latitude": 40.8426, "longitude": 111.7492},
    {"region": "辽宁", "city": "沈阳", "latitude": 41.8057, "longitude": 123.4315},
    {"region": "吉林", "city": "长春", "latitude": 43.8171, "longitude": 125.3235},
    {"region": "黑龙江", "city": "哈尔滨", "latitude": 45.8038, "longitude": 126.5349},
    {"region": "上海", "city": "上海", "latitude": 31.2304, "longitude": 121.4737},
    {"region": "江苏", "city": "南京", "latitude": 32.0603, "longitude": 118.7969},
    {"region": "浙江", "city": "杭州", "latitude": 30.2741, "longitude": 120.1551},
    {"region": "安徽", "city": "合肥", "latitude": 31.8206, "longitude": 117.2272},
    {"region": "福建", "city": "福州", "latitude": 26.0745, "longitude": 119.2965},
    {"region": "江西", "city": "南昌", "latitude": 28.6820, "longitude": 115.8579},
    {"region": "山东", "city": "济南", "latitude": 36.6512, "longitude": 117.1201},
    {"region": "河南", "city": "郑州", "latitude": 34.7466, "longitude": 113.6254},
    {"region": "湖北", "city": "武汉", "latitude": 30.5928, "longitude": 114.3055},
    {"region": "湖南", "city": "长沙", "latitude": 28.2282, "longitude": 112.9388},
    {"region": "广东", "city": "广州", "latitude": 23.1291, "longitude": 113.2644},
    {"region": "广西", "city": "南宁", "latitude": 22.8170, "longitude": 108.3669},
    {"region": "海南", "city": "海口", "latitude": 20.0440, "longitude": 110.1999},
    {"region": "重庆", "city": "重庆", "latitude": 29.5630, "longitude": 106.5516},
    {"region": "四川", "city": "成都", "latitude": 30.5728, "longitude": 104.0668},
    {"region": "贵州", "city": "贵阳", "latitude": 26.6470, "longitude": 106.6302},
    {"region": "云南", "city": "昆明", "latitude": 25.0389, "longitude": 102.7183},
    {"region": "西藏", "city": "拉萨", "latitude": 29.6520, "longitude": 91.1721},
    {"region": "陕西", "city": "西安", "latitude": 34.3416, "longitude": 108.9398},
    {"region": "甘肃", "city": "兰州", "latitude": 36.0611, "longitude": 103.8343},
    {"region": "青海", "city": "西宁", "latitude": 36.6171, "longitude": 101.7782},
    {"region": "宁夏", "city": "银川", "latitude": 38.4872, "longitude": 106.2309},
    {"region": "新疆", "city": "乌鲁木齐", "latitude": 43.8256, "longitude": 87.6168},
]


class WeatherDailyCrawler(BaseCrawler):
    """NASA POWER 省会/首府城市日度气象数据采集器。"""

    source_key = "weather_daily"
    data_type = "weather_daily"
    raw_default_suffix = ".json"

    def discover_urls(self, limit: int | None = None) -> list[str]:
        """为每个省会/首府城市构造一个日度气象 API 请求地址。"""
        urls: list[str] = []
        parameters = ",".join(self.config["parameters"])
        for city in PROVINCIAL_CAPITALS:
            query = {
                "parameters": parameters,
                "community": "AG",
                "longitude": city["longitude"],
                "latitude": city["latitude"],
                "start": self.config["start_date"],
                "end": self.config["end_date"],
                "format": "JSON",
            }
            urls.append(f"{self.config['base_url']}?{urlencode(query)}")
            if limit and len(urls) >= limit:
                return urls
        return urls

    def parse_raw_files(self, raw_files: list[Path]) -> list[dict]:
        """将每个城市的 JSON 缓存展开为逐日气象记录。"""
        city_by_url = {url: city for url, city in zip(self.discover_urls(), PROVINCIAL_CAPITALS)}
        records: list[dict] = []
        for raw_file in raw_files:
            source_url = self.cache.read_url(raw_file)
            city = city_by_url.get(source_url)
            if not city:
                continue
            data = json.loads(raw_file.read_text(encoding="utf-8"))
            parameters = data.get("properties", {}).get("parameter", {})
            dates = sorted(parameters.get("T2M", {}).keys())
            for date_key in dates:
                records.append(
                    {
                        "source_name": self.source_name,
                        "source_url": source_url,
                        "observation_date": self._format_date(date_key),
                        "region": city["region"],
                        "city": city["city"],
                        "latitude": city["latitude"],
                        "longitude": city["longitude"],
                        "avg_temperature": self._value(parameters, "T2M", date_key),
                        "max_temperature": self._value(parameters, "T2M_MAX", date_key),
                        "min_temperature": self._value(parameters, "T2M_MIN", date_key),
                        "avg_humidity": self._value(parameters, "RH2M", date_key),
                        "precipitation": self._value(parameters, "PRECTOTCORR", date_key),
                        "wind_speed": self._value(parameters, "WS2M", date_key),
                        "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "raw_file": str(raw_file),
                    }
                )
        return records

    @staticmethod
    def _format_date(date_key: str) -> str:
        return f"{date_key[:4]}-{date_key[4:6]}-{date_key[6:8]}"

    @staticmethod
    def _value(parameters: dict, name: str, date_key: str) -> float | str:
        value = parameters.get(name, {}).get(date_key)
        if value in {-999, -999.0, None}:
            return ""
        parsed = parse_float(value)
        return parsed if parsed is not None else ""
