"""Read-only service probes. Never print request URLs, keys or exception strings."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.library.search import search_library
from services.law.full_text import get_full_law

for label, call in [
    ("nanet-search", lambda: search_library("기본권", display_lines=2)),
    ("constitution", lambda: get_full_law("대한민국헌법")),
]:
    try:
        result = call()
        if isinstance(result, list):
            print(label, "count", len(result), "fields", list(result[0]) if result else [])
        else:
            print(label, result.get("status"), result.get("law_name"), result.get("article_count"))
            Path("data/constitution_probe.json").write_text(__import__("json").dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        print(label, "FAILED", type(exc).__name__)
