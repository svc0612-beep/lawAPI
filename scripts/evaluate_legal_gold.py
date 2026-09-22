"""Use only with independently reviewed JSONL. Does not invent legal ground truth."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_rag.config import Settings
from legal_rag.store import Store
from legal_rag.evaluation import load_gold, evaluate_gold_retrieval

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("gold")
    parser.add_argument("--split", choices=["train", "dev", "test"], default="test")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = evaluate_gold_retrieval(Store(Settings.from_env().database), load_gold(args.gold), args.split)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, ensure_ascii=False))
