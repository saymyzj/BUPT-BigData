# 本 Skill 复用说明

## 1. 复用目标

本次任务复用了 `skills/bigdata-data-cleaning/SKILL.md` 中定义的“大数据分析数据清洗与预处理工作流”，目标是在已有 `data/interim/` 数据基础上，形成标准化、可复现、可质检的数据清洗成果。

本 Skill 主要用于规范以下工作：

- 输入数据盘点。
- 清洗方案编写。
- 清洗脚本设计与实现。
- 字段标准化、类型转换、缺失值处理和重复值处理。
- 派生字段、聚合表和分析宽表构建。
- 数据字典和质量摘要生成。
- 清洗报告和验证记录整理。

## 2. 本次复用范围

本次在 `数据清洗skill复用测试` 文件夹中复用了该 Skill 的完整流程，而不是只复用单个函数或单一步骤。

| Skill 规范步骤 | 本次落实情况 |
|---|---|
| 阅读 README、采集方案或字段说明 | 已读取指定 `SKILL.md` 并盘点项目目录和输入数据 |
| 盘点输入数据文件、字段、行数、时间范围 | 已盘点 `rd_annual_sec.csv` 和 `stock_daily_market.csv` |
| 编写清洗方案 | 已生成 `数据清洗与预处理方案.md` |
| 设计清洗脚本 | 已生成 `src/cleaning/preprocess_data.py` |
| 字段清理、类型转换、去重和缺失值处理 | 已在脚本中按表封装清洗函数 |
| 生成派生字段、聚合表和宽表特征 | 已生成 `company_2024_features.csv` |
| 生成数据字典和质量摘要 | 已生成 `data_dictionary.csv` 和 `quality_summary.json` |
| 运行脚本并检查输出 | 已执行语法检查和完整脚本运行 |
| 编写清洗报告 | 已生成 `数据清洗与预处理报告.md` |
| 整理运行命令、输出清单和人工审核说明 | 已生成 `logs/validation_summary.md` 和本说明 |

## 3. 复用流程摘要

本次复用过程按以下顺序执行：

1. 读取 `skills/bigdata-data-cleaning/SKILL.md`，确认其作为本轮 SOP。
2. 进入 `数据清洗skill复用测试` 目录，检查已有数据结构。
3. 盘点 `data/interim/rd_annual_sec.csv` 和 `data/interim/stock_daily_market.csv` 的字段、行数、时间范围、重复值和缺失值。
4. 编写《数据清洗与预处理方案》，明确清洗原则、字段标准化、缺失值、去重、时间粒度和输出表设计。
5. 实现 `src/cleaning/preprocess_data.py`，按 Skill 要求封装通用函数和分表清洗函数。
6. 运行脚本生成 `data/processed/` 下的清洗数据、数据字典和质量摘要。
7. 运行验证命令，检查输出文件、行数、主键重复和数据字典覆盖情况。
8. 编写《数据清洗与预处理报告》和验证记录。

## 4. 关键提示词与人机协作摘要

用户要求：

```text
请你首先使用工具阅读并严格遵循 SKILL.md 这个文档中的所有规范和流程（作为你的 SOP）。
在数据清洗skill复用测试文件夹中完成该任务
```

执行时据此采取的协作方式：

- 优先读取并遵循指定 Skill 文档，而不是直接开始写脚本。
- 所有清洗输出均放入 `data/processed/`，不覆盖 `data/interim/` 输入数据。
- 先形成清洗方案，再写清洗脚本。
- 质量摘要、数据字典、清洗报告和验证记录作为必备交付物一并生成。
- 对无法主观判断的缺失值保持为空，并在报告中说明原因。

## 5. Skill 规范到代码实现的映射

| Skill 推荐组件 | 本次脚本中的实现 |
|---|---|
| `read_csv` / `write_csv` | 统一 CSV 读写、编码和字段顺序 |
| `clean_text` | 标准化文本空白和缺失占位符 |
| `parse_int` / `parse_float` | 解析整数、浮点数、百分号和带单位文本 |
| `parse_date` | 标准化日期为 `YYYY-MM-DD` |
| `deduplicate` | 按业务主键去重并记录删除数量 |
| `missing_count` | 统计各字段空值 |
| `clean_<table>` | `clean_rd_annual`、`clean_stock_daily` |
| `build_features` | 构建 `company_2024_features.csv` |
| `build_dictionary_rows` | 生成完整数据字典 |
| `run_preprocess` | 串联完整清洗流程 |

## 6. 复用产出清单

| 文件 | 说明 |
|---|---|
| `数据清洗与预处理方案.md` | 按 Skill 要求编写的清洗实施方案 |
| `src/cleaning/preprocess_data.py` | 可复现清洗脚本 |
| `data/processed/rd_annual_clean.csv` | 清洗后年度研发费用表 |
| `data/processed/stock_daily_clean.csv` | 清洗后股票日行情表 |
| `data/processed/company_2024_features.csv` | 2024 年公司级特征宽表 |
| `data/processed/data_dictionary.csv` | 覆盖全部输出字段的数据字典 |
| `data/processed/quality_summary.json` | 行数、重复、缺失和输出文件质量摘要 |
| `数据清洗与预处理报告.md` | 清洗过程、质量结果和后续建议 |
| `logs/validation_summary.md` | 验证命令和检查结果记录 |
| `本Skill复用说明.md` | 本文件，说明 Skill 复用过程 |

## 7. 可复用经验

本次流程可继续复用于同类课程或项目的数据清洗阶段。后续只需替换 `data/interim/` 输入数据，并按实际字段调整 `clean_<table>`、`build_features` 和 `build_dictionary_rows`，即可复用相同的目录结构、质量摘要格式、数据字典格式和报告结构。

## 8. 人工审核说明

本 Skill 能规范清洗流程并自动生成质量检查结果，但以下内容仍建议人工审核：

- 字段含义是否与课程或研究问题完全一致。
- 缺失值是否需要在后续建模或统计分析阶段插补。
- 行业分组、公司名称和 ticker 是否符合最终报告口径。
- 特征宽表中的关联逻辑是否满足具体分析假设。
- `HOLX` 未匹配到不晚于 2024 年的研发费用记录，是否需要补充采集或人工核验。
