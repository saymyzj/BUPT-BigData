# Agent 与 Skill 复用说明

## 复用目标

本次按照 `skills/bigdata-data-visualization/SKILL.md` 的流程，承接上一阶段清洗与分析成果，补齐数据可视化阶段交付物。

## 工作流记录

1. 读取可视化 skill 要求。
2. 盘点 `数据分析skill复用测试/data/processed` 和 `data/analysis`。
3. 设计 Dashboard 图表、交互和数据准备方案。
4. 编写 `prepare_dashboard_data.py`，生成前端 JSON。
5. 编写原生 HTML/CSS/JS Dashboard。
6. 使用浏览器验证页面渲染和交互状态。
7. 生成截图材料与文档交付物。

## 关键提示词摘要

用户请求：

```text
根据skill，对 E:\BUPT\BUPT-BigData\数据分析skill复用测试 进行数据可视化复用测试，放在新建文件夹命名 数据可视化skill复用测试 下面
```

执行策略：

```text
承接上一阶段 data/processed 和 data/analysis，不重新采集或清洗数据；
输出可运行 Dashboard、数据准备脚本、图表说明、报告、截图材料和复用说明。
```

## 人工审核说明

| 审核项 | 结果 |
|---|---|
| 是否读取成员 B 数据 | 是，读取 processed 与 analysis 目录 |
| 图表类型是否满足 3-5 类要求 | 是，包含折线、柱状、环图、散点、热力图、表格 |
| 交互控件是否改变图表结果 | 是，股票、行业、指标、日期、缩放均联动 |
| 是否生成截图材料 | 是，生成 5 张 PNG |
| 是否避免因果化解释 | 是，报告中明确相关性和聚类结果仅作探索性解释 |

## 运行入口

```text
cd E:\BUPT\BUPT-BigData\数据可视化skill复用测试
C:\Users\10932\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m http.server 8765
```

打开：

```text
http://localhost:8765/src/dashboard/dashboard.html
```
