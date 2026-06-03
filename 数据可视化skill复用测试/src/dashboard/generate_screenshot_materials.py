from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "dashboard-data.json"
OUT = ROOT / "screenshots" / "visualization"
FONT = Path("C:/Windows/Fonts/msyh.ttc")


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = Path("C:/Windows/Fonts/msyhbd.ttc") if bold and Path("C:/Windows/Fonts/msyhbd.ttc").exists() else FONT
    return ImageFont.truetype(str(path), size)


def draw_card(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], title: str, value: str) -> None:
    draw.rounded_rectangle(xy, radius=10, fill="#ffffff", outline="#d8ded8")
    draw.text((xy[0] + 18, xy[1] + 18), title, fill="#69716d", font=font(18))
    draw.text((xy[0] + 18, xy[1] + 50), value, fill="#18211f", font=font(34, True))


def draw_frame(title_suffix: str, selected: dict[str, str], filename: str, tooltip: bool = False) -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    img = Image.new("RGB", (1365, 900), "#f6f7f4")
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, 1365, 112), fill="#ffffff", outline="#d8ded8")
    draw.text((34, 24), "数据可视化 Skill 复用测试", fill="#24745a", font=font(17, True))
    draw.text((34, 54), "医药健康公司研发投入与市场风险 Dashboard", fill="#18211f", font=font(32, True))
    draw.text((1198, 37), "↺", fill="#18211f", font=font(32))

    labels = [
        ("股票", selected.get("ticker", "全部股票")),
        ("行业", selected.get("industry", "全部行业")),
        ("指标", selected.get("metric", "月均调整收盘价")),
        ("起始月份", selected.get("start", "2024-01")),
        ("结束月份", selected.get("end", "2024-12")),
        ("时间窗口", selected.get("window", "全量")),
    ]
    x = 34
    for label, value in labels:
        draw.text((x, 130), label, fill="#69716d", font=font(15, True))
        draw.rounded_rectangle((x, 155, x + 188, 196), radius=8, fill="#ffffff", outline="#d8ded8")
        draw.text((x + 14, 164), value, fill="#18211f", font=font(16))
        x += 202

    draw_card(draw, (34, 218, 340, 308), "公司数量", str(data["meta"]["company_count"]))
    draw_card(draw, (354, 218, 660, 308), "日行情记录", f'{data["meta"]["stock_rows"]:,}')
    draw_card(draw, (674, 218, 980, 308), "高关注公司", str(data["meta"]["risk_counts"].get("high_attention", 0)))
    draw_card(draw, (994, 218, 1300, 308), "异常候选", str(len(data["anomalies"])))

    draw.rounded_rectangle((34, 330, 1300, 690), radius=10, fill="#ffffff", outline="#d8ded8")
    draw.text((54, 350), "月度趋势", fill="#18211f", font=font(22, True))
    draw.text((54, 382), title_suffix, fill="#69716d", font=font(15))
    left, top, right, bottom = 105, 430, 1245, 645
    draw.line((left, bottom, right, bottom), fill="#9aa39e", width=2)
    draw.line((left, top, left, bottom), fill="#9aa39e", width=2)
    for i in range(1, 4):
        y = top + i * (bottom - top) / 4
        draw.line((left, y, right, y), fill="#e7ebe7", width=1)
    trend = data["monthly_trend"]
    vals = [row["avg_adj_close"] for row in trend]
    vmin, vmax = min(vals) - 5, max(vals) + 5
    points = []
    for i, row in enumerate(trend):
        px = left + i * (right - left) / (len(trend) - 1)
        py = bottom - (row["avg_adj_close"] - vmin) / (vmax - vmin) * (bottom - top)
        points.append((px, py))
    draw.line(points, fill="#356cae", width=4)
    for px, py in points:
        draw.ellipse((px - 5, py - 5, px + 5, py + 5), fill="#356cae")

    draw.rounded_rectangle((34, 712, 650, 870), radius=10, fill="#ffffff", outline="#d8ded8")
    draw.text((54, 732), "行业对比", fill="#18211f", font=font(21, True))
    colors = ["#24745a", "#356cae", "#a47425", "#2f8f9d"]
    for i, row in enumerate(data["industry_summary"][:4]):
        bar = int(row["avg_rd_busd"] * 18)
        y = 774 + i * 22
        draw.rectangle((210, y, 210 + bar, y + 14), fill=colors[i % len(colors)])
        draw.text((54, y - 4), row["industry"][:18], fill="#18211f", font=font(13))

    draw.rounded_rectangle((684, 712, 1300, 870), radius=10, fill="#ffffff", outline="#d8ded8")
    draw.text((704, 732), "异常候选与风险提示", fill="#18211f", font=font(21, True))
    for i, row in enumerate(data["anomalies"][:5]):
        draw.text((704, 772 + i * 18), f'{row["ticker"]}  {row["period"]}  z={row["z_score"]}', fill="#18211f", font=font(13))

    if tooltip:
        draw.rounded_rectangle((905, 500, 1260, 595), radius=10, fill="#ffffff", outline="#cbd2cc")
        first = data["companies"][0]
        draw.text((925, 518), f'{first["ticker"]} {first["company_name"]}', fill="#18211f", font=font(16, True))
        draw.text((925, 548), f'研发投入: {first["latest_rd_expense_busd"]} 十亿美元', fill="#18211f", font=font(14))
        draw.text((925, 570), f'风险: {first["risk_level"]}', fill="#b84a4a", font=font(14, True))

    OUT.mkdir(parents=True, exist_ok=True)
    img.save(OUT / filename)


def main() -> None:
    draw_frame("全部公司 · 2024-01 至 2024-12 · 月均调整收盘价", {}, "dashboard-home.png")
    draw_frame("MRNA · 2024-01 至 2024-12 · 月均调整收盘价", {"ticker": "MRNA · Moderna, Inc."}, "stock-select.png")
    draw_frame("全部公司 · 2024-07 至 2024-12 · 月均调整收盘价", {"start": "2024-07", "end": "2024-12"}, "date-range.png")
    draw_frame("全部公司 · 2024-10 至 2024-12 · 月均调整收盘价", {"start": "2024-10", "end": "2024-12", "window": "近 3 月"}, "zoom.png")
    draw_frame("悬停提示示例 · 研发投入与波动率散点", {}, "hover-tooltip.png", tooltip=True)
    print(f"screenshot materials written: {OUT}")


if __name__ == "__main__":
    main()
