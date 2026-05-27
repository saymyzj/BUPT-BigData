import re
from typing import Optional


_FOOTNOTE_PATTERN = re.compile(r"[\s\u3000]*\d+$")
_NON_NUMERIC_PATTERN = re.compile(r"[^0-9.\-]")


def clean_text(value: object) -> str:
    """清理从 HTML 或 PDF 表格中提取出的文本空白。"""
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def clean_disease_name(value: object) -> str:
    """清理病种名称末尾的脚注数字。"""
    text = clean_text(value)
    text = _FOOTNOTE_PATTERN.sub("", text)
    return text.strip()


def parse_int(value: object) -> Optional[int]:
    """从官方表格单元格中解析整数。"""
    text = clean_text(value).replace(",", "")
    if not text or text in {"-", "—", "--"}:
        return None
    text = _NON_NUMERIC_PATTERN.sub("", text)
    if not text:
        return None
    return int(float(text))


def parse_float(value: object) -> Optional[float]:
    """从官方表格单元格中解析小数或百分数数值。"""
    text = clean_text(value).replace(",", "").replace("%", "")
    if not text or text in {"-", "—", "--"}:
        return None
    text = _NON_NUMERIC_PATTERN.sub("", text)
    if not text:
        return None
    return float(text)


def clean_ranked_pathogen(value: object) -> str:
    """清理排名表中病原体名称前面的序号符号。"""
    text = clean_text(value)
    return re.sub(r"^[①②③④⑤⑥⑦⑧⑨⑩\d.、\s]+", "", text).strip()


def infer_disease_category(disease_name: str) -> str:
    """根据合计行推断当前病种分类。"""
    if "甲乙丙类" in disease_name:
        return "甲乙丙类总计"
    if "甲乙类" in disease_name:
        return "甲乙类合计"
    if "丙类" in disease_name:
        return "丙类合计"
    if "其他传染病合计" in disease_name:
        return "重点监测其他传染病合计"
    return ""
