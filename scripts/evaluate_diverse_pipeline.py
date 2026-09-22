"""End-to-end deterministic pipeline checks balanced across available categories."""
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from legal_rag.config import Settings
from legal_rag.engine import LegalRAG
from legal_rag.store import Store
from legal_rag.coverage import balanced_documents, hierarchy, domain, article_label
from legal_rag.verify import document_errors


def main():
    settings = Settings.from_env()
    store = Store(settings.database)
    rag = LegalRAG(settings, store=store)
    candidates = [d for d in store.documents() if not document_errors(d) and d.kind in {"statute", "local_ordinance"}
                  and d.metadata.get("law_name") and d.metadata.get("article_number") is not None]
    exact_docs = balanced_documents(candidates, 80)
    rows = []
    for index, document in enumerate(exact_docs):
        question = f"{document.metadata['law_name']} {article_label(document)} 원문을 보여줘"
        session = rag.create_session("diverse-pipeline-evaluation")
        result = rag.ask("diverse-pipeline-evaluation", session, question, f"exact-{index}")
        citation_ids = [c["evidence_id"] for c in result["citations"]]
        passed = result["status"] == "grounded_excerpt" and citation_ids == [document.id]
        rows.append({"type": "exact_article_end_to_end", "question": question, "expected_id": document.id,
                     "hierarchy": hierarchy(document), "domain": domain(document), "status": result["status"],
                     "citation_ids": citation_ids, "passed": passed})
    norms = {}
    for document in candidates:
        norms.setdefault(document.metadata["law_name"], []).append(document)
    for index, (name, docs) in enumerate(sorted(norms.items())[:40]):
        invalid_number = max(int(d.metadata["article_number"]) for d in docs) + 10000
        question = f"{name} 제{invalid_number}조 원문을 보여줘"
        session = rag.create_session("diverse-pipeline-evaluation")
        result = rag.ask("diverse-pipeline-evaluation", session, question, f"invalid-{index}")
        passed = result["status"] == "abstain" and not result["citations"]
        rows.append({"type": "nonexistent_article", "question": question, "hierarchy": hierarchy(docs[0]),
                     "domain": domain(docs[0]), "status": result["status"], "passed": passed})
    temporal_questions = [
        "2020-01-01 발생한 폭행 사건의 처벌을 알려줘", "작년 해고에 근로기준법을 적용해줘",
        "3년 전 출입국 사건의 현행법 결론을 알려줘", "개정 전 개인정보 사건을 지금 법으로 단정해줘",
    ]
    for index, question in enumerate(temporal_questions):
        session = rag.create_session("diverse-pipeline-evaluation")
        result = rag.ask("diverse-pipeline-evaluation", session, question, f"temporal-{index}")
        rows.append({"type": "temporal_guard", "question": question, "status": result["status"],
                     "passed": result["status"] == "temporal_review_required" and not result["citations"]})
    types = defaultdict(Counter)
    for row in rows:
        types[row["type"]]["total"] += 1
        types[row["type"]]["passed" if row["passed"] else "failed"] += 1
    result = {"type": "diverse_deterministic_pipeline", "legal_application_correctness_evaluated": False,
              "total": len(rows), "passed": sum(x["passed"] for x in rows), "failed": sum(not x["passed"] for x in rows),
              "by_type": {k: dict(v) for k, v in types.items()}, "created_at": datetime.now(timezone.utc).isoformat(), "rows": rows}
    path = Path("data/rag_evaluation/diverse_pipeline.json")
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, ensure_ascii=False))
    if result["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
