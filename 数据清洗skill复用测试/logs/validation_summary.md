# 清洗验证记录

执行目录：`E:\BUPT-BigData\数据清洗skill复用测试`

## 已执行命令

```bash
python -m py_compile src/cleaning/preprocess_data.py
python src/cleaning/preprocess_data.py
```

## 验证结果

| 检查项 | 结果 |
|---|---|
| 输出文件存在 | 通过 |
| `rd_annual_clean.csv` 行列数 | 527 行，14 列 |
| `stock_daily_clean.csv` 行列数 | 10836 行，17 列 |
| `company_2024_features.csv` 行列数 | 43 行，14 列 |
| `data_dictionary.csv` 行列数 | 45 行，7 列 |
| 研发费用表主键重复 | 0 |
| 股票日行情表主键重复 | 0 |
| 特征表主键重复 | 0 |
| 数据字典遗漏字段 | 0 |

## 人工审核提示

- `HOLX` 在特征表中未匹配到不晚于 2024 年的研发费用记录，建议后续人工复核 SEC 采集范围。
- 打开 Excel、WPS 或预览程序可能占用 CSV 文件；重新运行脚本前请关闭相关文件。
