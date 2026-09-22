"""Conservative original-text retrieval. No penalties or outcomes are generated.

Profiles propose candidates. Article selection is lexical retrieval, explicitly not
a determination that a provision applies to the user's facts.
"""
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import re
from urllib.parse import urlencode

from services.law.search_hints import compact, match_profiles, search_hints
from services.law.full_text import get_full_law
from services.evidence.precedent import search_precedents


def law_link(mst):
    return "https://www.law.go.kr/법령/" if not str(mst).isdigit() else "https://www.law.go.kr/LSW/lsInfoP.do?" + urlencode({"lsiSeq": mst})


def current_date():
    return datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d")


def valid_current_law(law, requested):
    try:
        datetime.strptime(str(law.get("effective_date", "")), "%Y%m%d")
    except (AttributeError, ValueError, TypeError):
        return False
    return (isinstance(law, dict) and law.get("status") == "success"
            and compact(law.get("law_name")) == compact(requested)
            and str(law.get("mst", "")).isdigit()
            and re.fullmatch(r"\d{8}", str(law.get("effective_date", ""))) is not None
            and law["effective_date"] <= current_date() and bool(law.get("articles")))


def article_score(article, anchors):
    title = compact(article.get("article_title"))
    context = title + compact(" ".join(article.get("section_headers", [])))
    text = compact(article.get("full_text"))
    if not text or "삭제" == text or "삭제" in title:
        return 0
    scores = []
    for group in anchors:
        terms = [compact(t) for t in group]
        if all(t in title for t in terms):
            first_title = compact(re.split(r"[,，ㆍ·]", article.get("article_title", ""))[0])
            exact_bonus = 50 if first_title == "".join(terms) else 0
            scores.append(100 + exact_bonus + len(terms) * 5 - len(title) * .1)
        elif all(t in context for t in terms):
            scores.append(90 + len(terms) * 5 - len(title) * .1)
        elif all(t in text for t in terms):
            scores.append(10 + len(terms) - len(text) / 100000)
    return max(scores, default=0)


def references(text):
    refs = {(int(a), int(b or 0)) for a, b in re.findall(r"제\s*(\d+)\s*조(?:\s*의\s*(\d+))?", text)}
    for start, end in re.findall(r"제\s*(\d+)\s*조부터\s*제\s*(\d+)\s*조까지", text):
        if 0 <= int(end) - int(start) <= 50:
            refs.update((n, 0) for n in range(int(start), int(end) + 1))
    return refs


def evidence_row(law, article, role):
    text = article["full_text"]
    return {"source": "법제처", "law_name": law["law_name"], "law_id": law.get("law_id", ""),
            "mst": law["mst"], "effective_date": article.get("effective_date") or law["effective_date"],
            "article_number": article["article_number"], "sub_article_number": article.get("sub_article_number", 0),
            "article_title": article.get("article_title", ""), "article_text": text,
            "official_link": law_link(law["mst"]), "role": role,
            "verification": "official_original_text", "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}


def select_original_articles(law, anchors):
    articles = [a for a in law["articles"] if a.get("full_text") and
                (not a.get("effective_date") or a["effective_date"] <= current_date())]
    direct = []
    for anchor in anchors:
        ranked = sorted(((article_score(a, (anchor,)), a) for a in articles), key=lambda x: -x[0])
        if ranked and ranked[0][0] > 0 and ranked[0][1] not in direct:
            direct.append(ranked[0][1])
    direct = direct[:8]
    selected = [evidence_row(law, a, "direct") for a in direct]
    keys = {(a["article_number"], a.get("sub_article_number", 0)) for a in direct}
    for article in articles:
        key = (article["article_number"], article.get("sub_article_number", 0))
        if key in keys:
            continue
        title = article.get("article_title", "")
        if not any(t in title for t in ("벌칙", "과태료", "양벌", "벌금")):
            continue
        # An explicit reference is only a candidate relation. Never infer that
        # all sanctions in the article apply; render the whole provision.
        if references(article["full_text"]) & keys:
            selected.append(evidence_row(law, article, "sanction_reference"))
    return selected


def collect_verified_topic(question):
    profiles = match_profiles(question)
    hints = search_hints(question)
    if not profiles:
        return None
    laws, statuses, full_laws = [], [], []
    names = hints["law_names"][:5]
    for name in names:
        try:
            law = get_full_law(name)
            if not valid_current_law(law, name):
                raise ValueError("unverified law identity/date/body")
            anchors = [a for p in profiles for a in p["laws"].get(name, ())]
            rows = select_original_articles(law, anchors)
            laws.extend(rows)
            full_laws.append(law)
            statuses.append(dict(source="법제처", endpoint="verified-law-original", status="success" if rows else "not_found", result_count=len(rows), message=name))
        except Exception:
            statuses.append(dict(source="법제처", endpoint="verified-law-original", status="error", result_count=0, message=name + " 원문 확인 실패"))
    precedents = []
    for term in hints["terms"][:2]:
        try:
            rows = search_precedents(term, display=3, detail_limit=3)
            precedents.extend(rows)
            state = "success" if rows else "not_found"
            if any(not r.get("detail_verified") for r in rows):
                state = "partial"
            statuses.append(dict(source="법제처", endpoint="prec", status=state, result_count=len(rows), message=term + (" 일부 판례 상세 검증 미완료" if state == "partial" else "")))
        except Exception:
            statuses.append(dict(source="법제처", endpoint="prec", status="error", result_count=0, message=term + " 판례 조회 실패"))
    seen = set()
    precedents = [p for p in precedents if p.get("precedent_id") and not (p["precedent_id"] in seen or seen.add(p["precedent_id"]))]
    return dict(status="success" if laws else "partial", question_type="관련_법령탐색", original_question=question,
                search_query=" ".join(hints["terms"]), evidence_found=bool(laws or precedents), article=None,
                laws=laws, law_candidates=[], precedents=precedents, interpretations=[], library_items=[],
                full_law=full_laws[0] if len(full_laws) == 1 else None, source_status=statuses,
                metadata={"retrieval_mode": "verified_originals", "search_hints": hints,
                          "coverage_limited": len(hints["law_names"]) > len(names),
                          "checked_at": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(),
                          "additional_questions": list(dict.fromkeys(q for p in profiles for q in p["questions"])),
                          "primary_law_confirmed": False, "legal_applicability_confirmed": False})


def collect_verified_explicit(question, analysis):
    """Exact article/full-text requests cannot fall back to a different article."""
    name = analysis.get("law_name") or ""
    result = dict(status="partial", question_type=analysis["question_type"], original_question=question,
                  search_query=name, evidence_found=False, article=None, laws=[], law_candidates=[],
                  precedents=[], interpretations=[], library_items=[], full_law=None, source_status=[],
                  metadata={"retrieval_mode": "verified_originals", "legal_applicability_confirmed": False,
                            "primary_law_confirmed": False})
    try:
        law = get_full_law(name)
        if not valid_current_law(law, name):
            raise ValueError("unverified original")
        result["full_law"] = law
        result["metadata"]["full_law_verified"] = True
        if analysis["question_type"] == "법령_전체조회":
            result["status"] = "success"
        else:
            wanted = (analysis["article_number"], analysis.get("sub_article_number", 0))
            for row in law["articles"]:
                if (row["article_number"], row.get("sub_article_number", 0)) != wanted:
                    continue
                if row.get("effective_date") and row["effective_date"] > current_date():
                    continue
                result["laws"] = [evidence_row(law, row, "requested")]
                paragraph = analysis.get("paragraph_number")
                if paragraph:
                    result["metadata"]["requested_paragraph_available"] = 1 <= paragraph <= len(row.get("paragraphs", []))
                result["status"] = "success"
                break
        state = "success" if result["status"] == "success" else "not_found"
        result["source_status"].append(dict(source="법제처", endpoint="exact-original", status=state,
                                           result_count=len(result["laws"]), message="요청 조문을 찾지 못했습니다." if state == "not_found" else name))
    except Exception:
        result["source_status"].append(dict(source="법제처", endpoint="exact-original", status="error", result_count=0, message="요청 법령의 원문을 확인하지 못했습니다."))
    return result
