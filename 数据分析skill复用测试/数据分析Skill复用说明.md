# 数据分析 Skill 复用说明

## 1. 复用目标

本说明用于记录 `bigdata-data-analysis` Skill 在本项目中的复用方式，便于课程展示、团队交接和后续项目迁移。本次复用目标是：在已有清洗结果 `data/processed/` 的基础上，按标准流程生成数据分析方案、分析脚本、结构化分析结果、分析数据字典、数据分析报告和整体应用价值分析。

## 2. 本次使用的 Skill

| 项目 | 内容 |
|---|---|
| Skill 名称 | `bigdata-data-analysis` |
| Skill 文件 | `skills/bigdata-data-analysis/SKILL.md` |
| 适用阶段 | 数据清洗完成后的数据分析阶段 |
| 主要能力 | 描述性统计、时间序列趋势、相关性分析、风险分组、异常检测、关键词关注分析、数据字典和报告撰写 |
| 本次执行目录 | `数据分析skill复用测试/` |

## 3. 触发与执行方式

本次复用由用户明确要求触发：

```text
请你首先使用工具阅读并严格遵循 SKILL.md 这个文档中的所有规范和流程（作为你的 SOP）。
在数据分析skill复用测试文件夹中完成该任务
```

执行时先读取 `skills/bigdata-data-analysis/SKILL.md`，再按其中的总体流程推进：

1. 阅读数据字典和清洗质量摘要。
2. 盘点 `data/processed/` 中的可分析数据表。
3. 编写《数据分析方案》。
4. 编写分析脚本。
5. 生成描述性统计、时间序列、相关性、风险分组、异常检测和关键词关注结果。
6. 生成分析输出数据字典。
7. 编写《数据分析报告》和《整体应用价值分析》。
8. 运行脚本并检查输出完整性。

## 4. 输入数据复用条件

复用本 Skill 前，项目目录应至少具备以下结构：

```text
project/
├── data/
│   └── processed/
│       ├── cleaned_data.csv
│       ├── features.csv
│       ├── data_dictionary.csv
│       └── quality_summary.json
```

本次实际输入为：

| 输入文件 | 行数 | 用途 |
|---|---:|---|
| `data/processed/rd_annual_clean.csv` | 527 | 年度研发费用分析 |
| `data/processed/stock_daily_clean.csv` | 10836 | 2024 年日行情趋势和异常检测 |
| `data/processed/company_2024_features.csv` | 43 | 公司级相关性和风险分组 |
| `data/processed/data_dictionary.csv` | - | 字段含义和单位说明 |
| `data/processed/quality_summary.json` | - | 清洗质量和缺失值说明 |

## 5. 复用后的目录结构

本次复用后形成以下关键目录和文件：

```text
数据分析skill复用测试/
├── data/
│   ├── processed/
│   └── analysis/
│       ├── descriptive_statistics.csv
│       ├── time_series_summary.csv
│       ├── correlation_matrix.csv
│       ├── cluster_results.csv
│       ├── anomaly_detection_results.csv
│       ├── keyword_sentiment_analysis.csv
│       ├── analysis_data_dictionary.csv
│       └── analysis_summary.json
├── src/
│   └── analysis/
│       ├── __init__.py
│       └── analyze_cleaned_data.py
├── 数据分析方案.md
├── 数据分析报告.md
├── 整体应用价值分析.md
└── 数据分析Skill复用说明.md
```

## 6. 关键产物说明

| 产物 | 说明 | 可复用价值 |
|---|---|---|
| `数据分析方案.md` | 说明分析目标、输入、方法、输出和实施计划 | 后续项目可按同样框架替换数据和指标 |
| `src/analysis/analyze_cleaned_data.py` | 标准库分析脚本 | 可直接复跑，也可按字段名迁移到新项目 |
| `data/analysis/descriptive_statistics.csv` | 描述性统计结果 | 可用于指标概览和可视化看板 |
| `data/analysis/time_series_summary.csv` | 时间序列趋势摘要 | 可用于趋势图和近期变化提示 |
| `data/analysis/correlation_matrix.csv` | Pearson 相关性结果 | 可用于变量关系探索，但不能解释为因果 |
| `data/analysis/cluster_results.csv` | 风险关注分组结果 | 可用于公司或对象分层展示 |
| `data/analysis/anomaly_detection_results.csv` | z-score 异常候选 | 可用于预警候选和人工复核 |
| `data/analysis/keyword_sentiment_analysis.csv` | 官方字段关键词关注分析 | 可用于主题关注，不代表社交媒体情绪 |
| `data/analysis/analysis_data_dictionary.csv` | 分析输出字段字典 | 方便可视化成员和后续模块稳定读取 |
| `data/analysis/analysis_summary.json` | 机器可读摘要 | 方便报告、前端或自动化流程读取 |
| `数据分析报告.md` | 分析结论和局限说明 | 可作为课程或项目报告主体 |
| `整体应用价值分析.md` | 应用方向、可行性和价值分析 | 可作为课程加分或商业化讨论材料 |

## 7. 脚本复跑方式

在 `数据分析skill复用测试/` 目录下运行：

```bash
python -m py_compile src/analysis/analyze_cleaned_data.py
python src/analysis/analyze_cleaned_data.py
```

脚本会重新读取 `data/processed/`，并覆盖生成 `data/analysis/` 下的分析结果。运行前应关闭 Excel、WPS 或其他正在打开分析 CSV 的程序，避免写入失败。

## 8. 迁移到其他项目的步骤

1. 保留目录结构 `data/processed/`、`data/analysis/`、`src/analysis/`。
2. 将新项目清洗后的数据放入 `data/processed/`。
3. 确认新项目已有 `data_dictionary.csv` 和质量摘要文件。
4. 按新字段修改 `analyze_cleaned_data.py` 中的输入文件名、数值字段、时间字段和分组字段。
5. 先更新《数据分析方案》，再运行脚本生成结果。
6. 检查 `analysis_data_dictionary.csv` 是否覆盖所有分析输出字段。
7. 根据结构化结果更新《数据分析报告》和《整体应用价值分析》。

## 9. 本次复用中的约束和人工判断

| 约束 | 处理方式 |
|---|---|
| 没有真实社交媒体或评论文本 | 不虚构舆情，改为官方字段关键词关注分析 |
| 相关性可能被公司规模、行业和市场环境共同影响 | 报告中明确说明相关性不等于因果 |
| 风险分组来自规则评分和分位数切分 | 仅作为高、中、低关注提示，不作为最终评级 |
| 异常检测只使用收益率和成交量 | 输出为预警候选，后续需结合新闻、财报或领域知识复核 |
| 最新研发费用存在少量缺失 | 不做主观插补，风险评分中按保守规则处理 |

## 10. 验证记录

| 检查项 | 结果 |
|---|---|
| 脚本语法检查 | 通过 |
| 完整运行分析脚本 | 通过 |
| 输出文件是否生成 | `data/analysis/` 下 8 个文件均已生成 |
| 分析数据字典字段覆盖 | 覆盖所有分析 CSV 输出字段 |
| 输出行数一致性 | `analysis_summary.json` 与实际结果一致 |
| 相关性样本量 | 公司级相关性样本量最高 43，少量研发字段为 42 |
| 聚类标签解释 | 已在报告中说明为高、中、低关注提示 |
| 异常结果解释 | 已在报告中说明为人工复核候选 |

## 11. 对后续复用者的建议

1. 不要只写分析结论，应同时交付结构化结果文件。
2. 每个输出 CSV 都应配套字段字典，方便可视化或后续模块读取。
3. 对相关性、聚类和异常检测保持保守解释，不写成因果结论。
4. 若没有真实文本数据，不要虚构舆情或情绪分析。
5. 每次迁移到新项目后，都应重新运行脚本并检查输出字段覆盖。
