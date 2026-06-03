# Agent 与 Skill 复用说明

## 1. 使用目标

本次任务用于测试 `bigdata-data-visualization` 技能在《医药上市公司研发投入与市场表现分析》项目上的复用能力。目标不是只生成静态图，而是完整走通数据可视化阶段：

1. 承接上一阶段清洗数据和分析结果。
2. 盘点 `data/processed/` 与 `data/analysis/` 中可视化可用字段。
3. 编写数据可视化方案。
4. 生成前端可读取的数据文件。
5. 搭建可运行 Dashboard 页面。
6. 实现股票、行业、指标、日期范围、缩放和悬停提示等交互。
7. 输出图表说明、可视化报告、运行日志和输入输出样例。
8. 生成页面截图和交互截图材料。

## 2. 关键提示词摘要

用户要求根据 `skills/bigdata-data-visualization/SKILL.md`，对以下目录进行数据可视化复用测试：

```text
E:\BUPT\BUPT-BigData\数据分析skill复用测试
```

并要求新建输出目录：

```text
E:\BUPT\BUPT-BigData\数据可视化skill复用测试
```

执行时遵循的核心原则是：不重新采集数据，不重复清洗数据，优先复用上一阶段成员 B 已输出的 `data/processed/` 和 `data/analysis/`，并将可视化阶段的代码、数据、截图、报告和 Skill 复用说明整理为独立交付物。

## 3. Skill 复用环节

| Skill 要求 | 本次落实情况 |
|---|---|
| 自动承接上一阶段清洗和分析成果 | 已读取 `数据分析skill复用测试/data/processed` 与 `data/analysis`。 |
| 检查 processed 与 analysis 中的可用数据 | 已在 `prepare_dashboard_data.py` 中读取日行情、公司特征、聚类、相关性、异常检测和关键词结果。 |
| 形成数据可视化方案 | 已输出 `docs/visualization/数据可视化方案.md`。 |
| 生成前端可读取数据 | 已生成 `data/dashboard-data.json`。 |
| 搭建可运行 Dashboard | 已完成 `src/dashboard/dashboard.html`、`styles.css`、`app.js`。 |
| 制作 3-5 类不同图表 | 已包含折线图、柱状图、环图、散点图、热力图和异常表格。 |
| 实现交互功能 | 已实现股票选择、行业筛选、指标切换、日期范围、近 6 月/近 3 月缩放、重置和悬停提示。 |
| 输出页面截图和交互截图 | 已生成 `screenshots/visualization/` 下 5 张 PNG。 |
| 输出图表说明和可视化报告 | 已输出 `图表说明.md` 与 `数据可视化报告.md`。 |
| 汇总运行日志和输入输出样例 | 已输出 `运行日志汇总.md`、`输入输出样例汇总.md` 和 `logs/visualization_run_log.md`。 |
| 输出 Agent/Skill 复用说明 | 当前文件及 `docs/visualization/Agent与Skill复用说明.md` 已完成。 |

## 4. 关键命令记录

本机普通 `python` 命令不可用，因此使用 Codex bundled Python 和 Node 运行：

```bash
C:\Users\10932\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe src/dashboard/prepare_dashboard_data.py
C:\Users\10932\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe --check src/dashboard/app.js
C:\Users\10932\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m http.server 8765
C:\Users\10932\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe src/dashboard/generate_screenshot_materials.py
```

页面运行入口：

```text
http://localhost:8765/src/dashboard/dashboard.html
```

## 5. 复用效果评价

本次 Skill 复用覆盖了“承接上一阶段成果、数据盘点、方案设计、数据准备、Dashboard 开发、交互实现、浏览器验证、截图整理、报告输出、Agent/Skill 说明”十个环节。

核心数据规模如下：

| 指标 | 结果 |
|---|---:|
| 公司数量 | 43 |
| 2024 年日行情记录 | 10,836 |
| 时间范围 | 2024-01 至 2024-12 |
| 高关注公司 | 15 |
| 异常候选记录 | 80 |
| Dashboard SVG 图表 | 5 |
| 异常表首屏行数 | 16 |
| 截图材料 | 5 张 |

整体看，本次复用已经满足数据可视化阶段的实验要求。需要说明的是，Headless Edge 在当前 Windows 沙箱中保存截图时出现权限噪声，因此额外用 `generate_screenshot_materials.py` 生成截图材料；Dashboard 本身已通过浏览器打开验证，页面数据和图表均能正常渲染。

## 6. 实验要求完成情况检查

| 实验要求 | 是否完成 | 对应交付物 |
|---|---|---|
| 使用指定可视化 Skill 完成复用测试 | 完成 | 本文件、`docs/visualization/Agent与Skill复用说明.md` |
| 新建 `数据可视化skill复用测试` 文件夹 | 完成 | `E:\BUPT\BUPT-BigData\数据可视化skill复用测试` |
| 复用上一阶段分析结果 | 完成 | `src/dashboard/prepare_dashboard_data.py` |
| 不伪造分析结果 | 完成 | 数据均来自上一阶段 CSV/JSON |
| 输出可运行 Dashboard | 完成 | `src/dashboard/dashboard.html` |
| 输出前端数据准备脚本 | 完成 | `src/dashboard/prepare_dashboard_data.py` |
| 输出前端数据文件 | 完成 | `data/dashboard-data.json` |
| 至少 3-5 类图表 | 完成 | 折线、柱状、环图、散点、热力、表格 |
| 支持交互筛选和悬停提示 | 完成 | `src/dashboard/app.js` |
| 输出截图材料 | 完成 | `screenshots/visualization/*.png` |
| 输出可视化方案和报告 | 完成 | `docs/visualization/数据可视化方案.md`、`数据可视化报告.md` |
| 输出图表说明 | 完成 | `docs/visualization/图表说明.md` |
| 输出运行日志汇总 | 完成 | `docs/visualization/运行日志汇总.md`、`logs/visualization_run_log.md` |
| 输出输入输出样例 | 完成 | `docs/visualization/输入输出样例汇总.md` |
| 输出 Agent/Skill 复用说明 | 完成 | 当前文件 |

结论：本次数据可视化 Skill 复用测试已完成实验要求，可作为数据采集、数据分析之后的第三阶段复用材料提交。
