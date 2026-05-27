from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
LOG_DIR = PROJECT_ROOT / "logs"
CONFIG_DIR = PROJECT_ROOT / "src" / "config"


def ensure_project_dirs() -> None:
    """创建爬虫和解析流程需要使用的项目输出目录。"""
    for directory in (RAW_DIR, INTERIM_DIR, PROCESSED_DIR, LOG_DIR):
        directory.mkdir(parents=True, exist_ok=True)
