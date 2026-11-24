"""Helper functions used to scrape shops"""
import json, time, requests
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

HEADERS = {
    "User-Agent" : "Mozilla/5.0 (course-demo; personal use)",
    "Accept-Language": "lt, en;q=0.8"
}


def get_html(url: str, params: dict[str, Any] | None = None, delay: float = 2.0) -> str:
    """Downloading one page and returning it's HTML text."""

    r = requests.get(url, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    time.sleep(delay)

    return r.text


def save_rows(rows: list[dict[str, Any]], store: str, name: str) -> Path:
    """Save a list of product dictionaries"""

    folder = DATA_DIR / store

    folder.mkdir(parents=True, exist_ok = True)
    path = folder / f"{name}.json"
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    return path