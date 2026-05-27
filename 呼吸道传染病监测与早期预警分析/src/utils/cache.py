import hashlib
from pathlib import Path
from urllib.parse import urlparse


class RawCache:
    """保存原始 HTML/PDF/Excel 文件，便于复用本地缓存。"""

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def path_for_url(self, url: str, subdir: str, default_suffix: str = ".html") -> Path:
        parsed = urlparse(url)
        suffix = Path(parsed.path).suffix or default_suffix
        if suffix.lower() not in {".html", ".htm", ".pdf", ".xls", ".xlsx", ".csv"}:
            suffix = default_suffix
        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
        safe_name = Path(parsed.path).stem or "index"
        safe_name = "".join(ch if ch.isalnum() else "_" for ch in safe_name)[:40]
        directory = self.root_dir / subdir
        directory.mkdir(parents=True, exist_ok=True)
        return directory / f"{safe_name}_{digest}{suffix}"

    @staticmethod
    def has_file(path: Path) -> bool:
        return path.exists() and path.stat().st_size > 0

    @staticmethod
    def write_bytes(path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    @staticmethod
    def write_url(path: Path, url: str) -> None:
        path.with_suffix(path.suffix + ".url").write_text(url, encoding="utf-8")

    @staticmethod
    def read_url(path: Path) -> str:
        url_path = path.with_suffix(path.suffix + ".url")
        if not url_path.exists():
            return ""
        return url_path.read_text(encoding="utf-8").strip()

    @staticmethod
    def read_text(path: Path) -> str:
        return path.read_text(encoding="utf-8", errors="ignore")
