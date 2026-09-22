"""Audit corpus breadth and run source-derived identity questions."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from legal_rag.config import Settings
from legal_rag.store import Store
from legal_rag.coverage import corpus_coverage, mechanical_question_evaluation, minimum_coverage_gate


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/rag_evaluation/legal_coverage.json")
    parser.add_argument("--question-output", default="data/rag_evaluation/mechanical_questions.json")
    parser.add_argument("--coverage-manifest", default="data/rag_evaluation/coverage_manifest.json")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    store = Store(Settings.from_env().database)
    coverage = corpus_coverage(store)
    manifest = json.loads(Path(args.coverage_manifest).read_text(encoding="utf-8"))
    coverage["minimum_coverage_gate"] = minimum_coverage_gate(coverage, manifest)
    questions = mechanical_question_evaluation(store, args.limit)
    coverage.update(created_at=datetime.now(timezone.utc).isoformat(),
                    question_evaluation={k: v for k, v in questions.items() if k != "rows"})
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(coverage, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(args.question_output).write_text(json.dumps(questions, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(coverage, ensure_ascii=False))
    # A perfect score over the remaining valid documents must not hide a
    # missing legal hierarchy or domain.  Coverage loss is a failing release
    # condition even when every generated identity question passes.
    if questions["failed"] or not coverage["coverage_complete"] or not coverage["minimum_coverage_gate"]["passed"]:
        raise SystemExit(1)
