from bs4 import BeautifulSoup

from parsers.normalizers import clean_text


def soup_from_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def extract_page_title(soup: BeautifulSoup) -> str:
    """提取文章标题；若无法识别文章标题，则回退到 HTML 标题。"""
    title_selectors = [".content h1", ".main h1", "h1", "h5 a", "h5"]
    for selector in title_selectors:
        node = soup.select_one(selector)
        if node:
            title = clean_text(node.get_text(" ", strip=True))
            if title and title != "中国疾病预防控制中心":
                return title
    if soup.title:
        return clean_text(soup.title.get_text(" ", strip=True))
    return ""


def extract_tables(soup: BeautifulSoup) -> list[list[list[str]]]:
    """提取页面中的所有 HTML 表格，并转换为纯文本二维数组。"""
    tables: list[list[list[str]]] = []
    for table in soup.find_all("table"):
        rows: list[list[str]] = []
        for tr in table.find_all("tr"):
            cells = [
                clean_text(cell.get_text(" ", strip=True))
                for cell in tr.find_all(["th", "td"])
            ]
            if any(cells):
                rows.append(cells)
        if rows:
            tables.append(rows)
    return tables
