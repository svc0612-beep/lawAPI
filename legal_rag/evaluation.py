"""External reviewed gold validation and retrieval metrics. No self-grading as truth."""
import json
import math
from collections import defaultdict
from pathlib import Path


def load_gold(path):
    rows, seen, groups, questions = [], set(), {}, {}
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        required = {"id", "question", "domain", "scenario_group", "split", "relevant_documents", "reviewer", "reviewed_at", "answerable"}
        if not required.issubset(row):
            raise ValueError(f"gold_missing_fields_line_{line_number}")
        if any(not isinstance(row[k], str) or not row[k].strip() for k in required - {"relevant_documents", "answerable"}):
            raise ValueError("gold_invalid_string_fields")
        if type(row["answerable"]) is not bool or row["split"] not in {"train", "dev", "test"}:
            raise ValueError("gold_invalid_split_or_answerability")
        if row["id"] in seen:
            raise ValueError("gold_duplicate_id")
        seen.add(row["id"])
        group = row["scenario_group"]
        if group in groups and groups[group] != row["split"]:
            raise ValueError("gold_scenario_split_leakage")
        groups[group] = row["split"]
        normalized = "".join(row["question"].split())
        if normalized in questions:
            raise ValueError("gold_duplicate_question")
        questions[normalized] = row["split"]
        relevant = row["relevant_documents"]
        if not isinstance(relevant, dict) or any(not isinstance(k, str) or type(v) is not int or v not in {1, 2, 3} for k, v in relevant.items()):
            raise ValueError("gold_invalid_relevance_labels")
        if row["answerable"] and not relevant:
            raise ValueError("gold_answerable_without_evidence")
        rows.append(row)
    if not rows:
        raise ValueError("gold_empty")
    return rows


def retrieval_metrics(ids, relevant, k=24):
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate_retrieval_result")
    if not relevant:
        return {"recall": None, "mrr": None, "ndcg": None}
    chosen = ids[:k]
    ranks = [i for i, key in enumerate(chosen, 1) if key in relevant]
    dcg = sum((2 ** relevant.get(key, 0) - 1)/math.log2(i + 1) for i, key in enumerate(chosen, 1))
    ideal = sum((2 ** grade - 1)/math.log2(i + 1) for i, grade in enumerate(sorted(relevant.values(), reverse=True)[:k], 1))
    return {"recall": len(ranks)/len(relevant), "mrr": 1/min(ranks) if ranks else 0,
            "ndcg": dcg/ideal if ideal else 0}


def evaluate_gold_retrieval(store, rows, split="test", k=24):
    from .verify import document_errors
    results = []
    for row in rows:
        if row["split"] != split:
            continue
        missing = [key for key in row["relevant_documents"] if not store.get(key)]
        hits = [h for h in store.lexical(row["question"], k) if not document_errors(h.document)]
        ids = [h.document.id for h in hits]
        results.append({"id": row["id"], "domain": row["domain"], "answerable": row["answerable"],
                        "missing_expected_documents": missing, "retrieved_ids": ids,
                        **retrieval_metrics(ids, row["relevant_documents"], k)})
    if not results:
        raise ValueError("no_gold_for_requested_split")
    domains = defaultdict(list)
    for result in results:
        domains[result["domain"]].append(result)
    def aggregate(items):
        return {key: sum(r[key] for r in items if r[key] is not None)/sum(r[key] is not None for r in items)
                if any(r[key] is not None for r in items) else None for key in ("recall", "mrr", "ndcg")}
    return {"type": "externally_reviewed_retrieval_gold", "split": split, "k": k, "total": len(results),
            "review_authenticity": "operator_must_verify", "answer_correctness_evaluated": False,
            "metrics": aggregate(results), "by_domain": {k: aggregate(v) for k, v in domains.items()}, "rows": results}


def release_gate(*, expert_reviewed_answers=0, unsafe_publications=0, nanet_authenticated=False,
                 historical_application_verified=False, natural_question_retrieval_validated=False,
                 hierarchy_coverage_complete=False, domain_coverage_complete=False,
                 source_effective_dates_verified=False):
    blockers = []
    if expert_reviewed_answers < 10000:
        blockers.append("independent_legal_answer_evaluation_below_requested_10000")
    if unsafe_publications:
        blockers.append("unsafe_publication_detected")
    if not nanet_authenticated:
        blockers.append("nanet_live_authentication_not_verified")
    if not historical_application_verified:
        blockers.append("historical_law_and_transitional_provisions_not_verified")
    if not natural_question_retrieval_validated:
        blockers.append("natural_question_retrieval_not_validated")
    if not hierarchy_coverage_complete:
        blockers.append("legal_hierarchy_coverage_incomplete")
    if not domain_coverage_complete:
        blockers.append("legal_domain_coverage_incomplete")
    if not source_effective_dates_verified:
        blockers.append("source_effective_dates_not_verified")
    return {"production_ready": not blockers, "blockers": blockers,
            "note": "Passing a numerical threshold never proves zero errors; these are minimum project acceptance conditions."}
