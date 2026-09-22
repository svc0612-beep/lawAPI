"""Validate source identity and expose the limits of the retrieved material."""
import re
from services.evidence.verified_retrieval import valid_current_law, evidence_row, current_date
from services.law.full_text import get_full_law
from services.law.reranker_tokens import tokenize_query
from services.law.search_hints import compact


def finalize_evidence(result):
    metadata = result.setdefault("metadata", {})
    if metadata.get("retrieval_mode") != "verified_originals":
        verified = []
        candidates = list(result.get("laws") or [])
        requested = result.get("article")
        if isinstance(requested, dict):
            match = re.search(r"(?:제)?(\d+)조(?:의(\d+))?", requested.get("article", ""))
            if match:
                candidates = [dict(requested, article_number=int(match[1]), sub_article_number=int(match[2] or 0))]
        originals = {}
        for row in candidates[:8]:
            name = row.get("law_name", "")
            if name not in originals:
                if len(originals) >= 3:
                    continue
                try:
                    law = get_full_law(name)
                    originals[name] = law if valid_current_law(law, name) else None
                except Exception:
                    originals[name] = None
            law = originals[name]
            if not law:
                continue
            # Do not silently substitute a different retrieved edition.
            if row.get("mst") and str(row["mst"]) != str(law["mst"]):
                continue
            for article in law["articles"]:
                if article.get("effective_date") and article["effective_date"] > current_date():
                    continue
                if (article["article_number"], article.get("sub_article_number", 0)) == (row.get("article_number"), row.get("sub_article_number", 0) or 0):
                    if not requested:
                        tokens = tokenize_query(result.get("original_question", ""))
                        body = compact(article.get("full_text", ""))
                        coverage = sum(compact(t) in body for t in tokens) / len(tokens) if tokens else 0
                        if coverage < 0.75:
                            continue
                    verified.append(evidence_row(law, article, "requested" if requested else "candidate"))
                    if requested and requested.get("paragraph_number"):
                        n = requested["paragraph_number"]
                        paragraphs = article.get("paragraphs", [])
                        metadata["requested_paragraph_available"] = 1 <= n <= len(paragraphs)
                    break
        metadata["retrieval_mode"] = "verified_candidates"
        metadata["legal_applicability_confirmed"] = False
        result["verified_laws"] = verified
    else:
        result["verified_laws"] = list(result.get("laws") or [])
    failed = [s for s in result.get("source_status", []) if s.get("status") in ("error", "partial")]
    full_request_verified = result.get("question_type") == "법령_전체조회" and metadata.get("full_law_verified")
    if failed or (not result["verified_laws"] and not full_request_verified):
        if result.get("status") != "error":
            result["status"] = "partial"
    metadata["verification"] = {
        "original_article_count": len(result["verified_laws"]),
        "failed_source_count": len(failed),
        "applicability": "not_determined",
        "historical_law_checked": False,
    }
    return result
