# 呼吸道传染病监测与早期预警 Agent 与 Skills 加分材料汇总

## 1. 全组复用材料索引

本项目的 AI Agent 与 Skills 加分材料按阶段存放在主目录下的复用测试文件夹中。各阶段材料包含 Agent 工作流目标、关键提示词或对话摘要、运行命令、输入输出样例、结果文件和人工审核说明。

| 阶段 | 复用材料位置 | 说明 |
|---|---|---|
| 数据采集 | `../数据采集skill复用测试/Agent与Skill复用说明.md` | 数据源选择、爬虫运行、缓存、失败重试和质检说明 |
| 数据清洗 | `../数据清洗skill复用测试/数据清洗Skill复用说明.md` | 原始数据清洗、字段标准化、缺失值处理和质量检查 |
| 数据分析 | `../数据分析skill复用测试/数据分析Skill复用说明.md` | 描述统计、时间序列、相关性、聚类、异常检测和应用价值分析 |
| 数据可视化 | `../数据可视化skill复用测试/Agent与Skill复用说明.md` | Dashboard 生成、交互验证、图表说明和截图材料整理 |
| 可视化补充材料 | `../数据可视化skill复用测试/docs/visualization/` | 图表说明、运行日志汇总、输入输出样例汇总和页面截图记录 |

项目级 Skill 文件位于：

```text
../skills/bigdata-data-collection/SKILL.md
../skills/bigdata-data-cleaning/SKILL.md
../skills/bigdata-data-analysis/SKILL.md
../skills/bigdata-data-visualization/SKILL.md
```

这些 Skill 覆盖“爬取数据 -> 清洗预处理 -> 统计分析 -> 可视化展示 -> 报告材料生成”的复用流程，满足课程加分项中对 Agent 工作流、Skills 封装质量和自动化复用效果的要求。

## 2. 成员 C 可视化 Agent 工作流目标

使用 AI Agent 协助成员 C 完成呼吸道传染病监测与早期预警 Dashboard：读取成员 AB 已完成的清洗数据和分析结果，生成前端数据、搭建交互式页面、编写可视化方案和报告材料。

## 3. 关键提示词摘要

```text
我要进行 E:\BUPT\BUPT-BigData\呼吸道传染病监测与早期预警分析 的分析。

要求：
包含 3-5 种不同类型的图表，维度指标合理，支持筛选、缩放、悬停显示详细信息，效果美观且具有创新性。
```

## 4. 输入文件样例

- `呼吸道传染病监测与早期预警分析/data/processed/respiratory_weekly_clean.csv`
- `呼吸道传染病监测与早期预警分析/data/processed/influenza_weekly_clean.csv`
- `呼吸道传染病监测与早期预警分析/data/analysis/cluster_results.csv`
- `呼吸道传染病监测与早期预警分析/data/analysis/correlation_matrix.csv`
- `呼吸道传染病监测与早期预警分析/data/analysis/anomaly_detection_results.csv`

## 5. 输出文件样例

- `呼吸道传染病监测与早期预警分析/src/dashboard/dashboard.html`
- `呼吸道传染病监测与早期预警分析/src/dashboard/app.js`
- `呼吸道传染病监测与早期预警分析/src/dashboard/styles.css`
- `呼吸道传染病监测与早期预警分析/data/dashboard-data.js`
- `呼吸道传染病监测与早期预警分析/数据可视化方案.md`
- `呼吸道传染病监测与早期预警分析/数据可视化报告.md`

## 6. 运行命令

```powershell
cd E:\BUPT\BUPT-BigData\呼吸道传染病监测与早期预警分析
& "C:\Users\10932\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" src/dashboard/prepare_dashboard_data.py
& "C:\Users\10932\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m http.server 8000
```

访问：

```text
http://localhost:8000/src/dashboard/dashboard.html
```

## 7. 自动完成步骤

1. 读取呼吸道主项目清洗数据和分析结果。
2. 聚合周度病原体阳性率、ILI%、暴发疫情数、风险分级、相关性和异常点。
3. 生成前端数据文件。
4. 构建交互式 Dashboard。
5. 输出可视化方案、报告和复用说明。

## 8. 可视化截图材料

成员 C 已补充主项目 Dashboard 截图，路径如下：

```text
screenshots/dashboard/Dashboard 首页全貌.png
screenshots/dashboard/病原体指标切换截图.png
screenshots/dashboard/周范围缩放截图.png
screenshots/dashboard/悬停截图.png
screenshots/dashboard/省市风险分布或异常检测表截图.png
```

截图覆盖首页展示、指标切换、周范围缩放、悬停提示和风险/异常结果展示，可用于研究实践报告和课堂 PPT。

## 9. 人工审核说明

Dashboard 中风险分级、相关性和异常检测均来自探索性分析。已人工确认截图清晰、筛选条件与报告描述一致，并在报告中说明结果不替代疾控业务判断。
