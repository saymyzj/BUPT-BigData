# 呼吸道传染病监测与早期预警分析

本目录用于存放《呼吸道传染病监测与早期预警分析系统》的数据采集、清洗、分析和可视化代码。

## 已实现内容

当前已实现第一个核心数据源：

- 中国疾控中心全国法定传染病月报爬虫：`chinacdc_monthly`

代码采用分层设计：

1. `src/utils/http_client.py`：统一 HTTP 请求、随机延迟、失败重试和反爬状态识别。
2. `src/utils/cache.py`：原始 HTML/PDF/Excel 本地缓存，避免重复访问源站。
3. `src/utils/task_store.py`：SQLite 任务状态表，支持断点续爬和运行记录。
4. `src/crawlers/base.py`：通用爬虫基类，封装发现链接、下载、解析、保存流程。
5. `src/crawlers/chinacdc_monthly.py`：中国疾控月报数据源实现。

## 运行方式

在当前目录执行：

```bash
python3 src/main.py chinacdc_monthly --limit 2
```

参数说明：

- `--limit 2`：只抓取 2 个详情页，用于测试。
- `--parse-only`：只解析已缓存的原始文件，不访问网站。
- `--force`：忽略缓存，重新请求网页。
- `--workers 4`：全局下载线程数。
- `--min-delay 1 --max-delay 3`：同一域名请求间隔为 1-3 秒随机值。

全量采集时建议使用较保守参数：

```bash
python3 src/main.py chinacdc_monthly --workers 2 --min-delay 1.5 --max-delay 3.5
```

## 输出文件

- 原始网页缓存：`data/raw/chinacdc_monthly/`
- 中间结构化数据：`data/interim/chinacdc_monthly.csv`
- 爬取日志：`logs/crawler.log`
- 任务状态库：`logs/crawl_tasks.sqlite`

## 字段原则

结构化数据使用英文 `snake_case` 字段名，字段值保留中文。例如：

- `report_year`：报告年份
- `report_month`：报告月份
- `region`：地区
- `disease_name`：病种名称
- `cases`：发病数
- `deaths`：死亡数
- `source_url`：原始来源链接
- `raw_file`：本地原始文件路径

## 反爬与合规策略

1. 每个 URL 成功请求后保存本地缓存，后续默认读取缓存。
2. 同一域名请求设置随机延迟，避免高频访问。
3. 请求失败只有限重试，不进行无限重试。
4. 遇到 403 或 429 时记录日志并停止该 URL，不绕过验证码或登录限制。
5. 仅采集官方公开汇总数据，不采集个人隐私或病例详情。

