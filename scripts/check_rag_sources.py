"""Bounded live source integration check. Never prints credentials or raw errors."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_rag.config import Settings
from legal_rag.store import Store
from legal_rag.ingest import OfficialAPIRetriever

if __name__ == "__main__":
    result = OfficialAPIRetriever(Store(Settings.from_env().database), max_laws=1).refresh("폭행")
    result["checked_at"] = datetime.now(timezone.utc).isoformat()
    path = Path("data/rag_evaluation/live_sources.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
