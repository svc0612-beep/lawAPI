"""Coverage taxonomy and mechanical, source-derived question evaluation."""
import math
import re
from collections import Counter, defaultdict
from .verify import document_errors


REQUIRED_HIERARCHIES = [
    "constitution", "statute", "presidential_decree", "prime_ministerial_order",
    "ministerial_order", "administrative_rule", "local_ordinance", "precedent",
]

REQUIRED_DOMAINS = [
    "constitutional", "civil", "criminal", "criminal_procedure", "civil_procedure",
    "administrative", "immigration", "education", "labor", "tax_customs", "health_welfare",
    "family_youth", "housing_land", "traffic_safety", "privacy_digital", "intellectual_property",
    "environment", "election", "consumer_commerce", "local_government", "maritime",
]

DOMAIN_RULES = [
    ("constitutional", ("헌법", "국기", "헌정")),
    ("criminal_procedure", ("형사소송",)),
    ("civil_procedure", ("민사소송", "가사소송")),
    ("criminal", ("형법", "소년법", "범죄", "특정범죄", "교통사고처리")),
    ("civil", ("민법", "상법", "가족관계")),
    ("immigration", ("출입국", "국적법", "난민법", "재외동포")),
    ("education", ("교육", "학교", "교과", "학원")),
    ("labor", ("근로", "노동", "산업안전", "퇴직급여", "중대재해")),
    ("tax_customs", ("국세", "지방세", "관세", "조세")),
    ("health_welfare", ("의료", "건강", "복지", "감염병", "사회보장", "장애인")),
    ("family_youth", ("아동", "청소년", "청년", "영유아")),
    ("housing_land", ("주택", "임대차", "건축", "국토", "토지", "전세")),
    ("traffic_safety", ("도로교통", "교통", "재난", "소방", "안전")),
    ("privacy_digital", ("개인정보", "정보통신", "전자금융", "통신비밀")),
    ("intellectual_property", ("특허", "저작권", "상표", "디자인보호")),
    ("environment", ("환경", "대기", "물환경", "폐기물")),
    ("election", ("선거", "정당",)),
    ("consumer_commerce", ("소비자", "전자상거래", "표시ㆍ광고")),
    ("local_government", ("지방자치", "조례", "시청", "군청", "구청")),
    ("maritime", ("해양", "선박", "수상레저", "항해")),
    ("administrative", ("행정", "정부조직", "법제업무", "공무원")),
]


def hierarchy(document):
    if document.kind == "precedent":
        return "precedent"
    if document.kind == "administrative_rule":
        return "administrative_rule"
    if document.kind == "local_ordinance":
        return "local_ordinance"
    name = document.metadata.get("law_name", "")
    law_type = document.metadata.get("law_type", "")
    if name == "대한민국헌법" or law_type == "헌법":
        return "constitution"
    if "대통령령" in law_type or name.endswith("시행령"):
        return "presidential_decree"
    if "총리령" in law_type:
        return "prime_ministerial_order"
    if "부령" in law_type:
        return "ministerial_order"
    if name.endswith("시행규칙"):
        return "ministerial_or_prime_ministerial_order_unresolved"
    return "statute"


def domain(document):
    text = " ".join([document.metadata.get("law_name", ""), document.title,
                     document.metadata.get("local_government", ""), document.metadata.get("issuing_authority", "")])
    for label, keywords in DOMAIN_RULES:
        if any(keyword in text for keyword in keywords):
            return label
    return "other"


def article_label(document, spaced=False):
    number = document.metadata.get("article_number")
    sub = int(document.metadata.get("sub_article_number") or 0)
    if spaced:
        return f"제 {number} 조" + (f"의 {sub}" if sub else "")
    return f"제{number}조" + (f"의{sub}" if sub else "")


def balanced_documents(documents, limit=None):
    groups = defaultdict(list)
    for document in sorted(documents, key=lambda d: d.id):
        groups[(hierarchy(document), domain(document), document.metadata.get("law_name", document.title))].append(document)
    output = []
    while groups and (limit is None or len(output) < limit):
        for key in list(groups):
            output.append(groups[key].pop(0))
            if not groups[key]:
                del groups[key]
            if limit is not None and len(output) >= limit:
                break
    return output


def corpus_coverage(store):
    all_documents = store.documents()
    valid = [d for d in all_documents if not document_errors(d)]
    hierarchies = Counter(hierarchy(d) for d in valid)
    domains = Counter(domain(d) for d in valid)
    laws = Counter(d.metadata.get("law_name") or "(precedent)" for d in valid)
    missing_hierarchies = [x for x in REQUIRED_HIERARCHIES if not hierarchies[x]]
    missing_domains = [x for x in REQUIRED_DOMAINS if not domains[x]]
    return {"documents_total": len(all_documents), "documents_valid": len(valid), "unique_norms": len(laws),
            "hierarchies": dict(hierarchies), "domains": dict(domains), "top_norms": laws.most_common(30),
            "missing_hierarchies": missing_hierarchies, "missing_domains": missing_domains,
            "coverage_complete": not missing_hierarchies and not missing_domains}


def minimum_coverage_gate(coverage, manifest):
    """Detect material corpus shrinkage against a versioned known-good snapshot.

    This is a data-loss alarm, not a legal accuracy score.  Small source-driven
    count changes are allowed, while disappearance of a hierarchy or a large
    expiry wave fails the gate.
    """
    drop = manifest.get("max_allowed_drop_fraction")
    if not isinstance(drop, (int, float)) or not 0 <= drop < 1:
        raise ValueError("invalid_coverage_drop_fraction")

    deficits = []

    def check(dimension, name, baseline, actual):
        if not isinstance(baseline, int) or baseline < 0:
            raise ValueError("invalid_coverage_baseline")
        minimum = math.ceil(baseline * (1 - drop))
        if actual < minimum:
            deficits.append({"dimension": dimension, "name": name, "baseline": baseline,
                             "minimum": minimum, "actual": actual})

    check("summary", "documents_valid", manifest["documents_valid"], coverage.get("documents_valid", 0))
    for name, baseline in manifest.get("hierarchies", {}).items():
        check("hierarchy", name, baseline, coverage.get("hierarchies", {}).get(name, 0))
    for name, baseline in manifest.get("domains", {}).items():
        check("domain", name, baseline, coverage.get("domains", {}).get(name, 0))
    return {"passed": not deficits, "baseline_created_at": manifest.get("baseline_created_at", ""),
            "max_allowed_drop_fraction": drop, "deficits": deficits}


def mechanical_question_evaluation(store, limit=None):
    """Evaluate source identity. These are not natural-question/legal-answer gold."""
    docs = [d for d in store.documents() if not document_errors(d) and d.kind in {"statute", "local_ordinance"}
            and d.metadata.get("law_name") and d.metadata.get("article_number") is not None]
    docs = balanced_documents(docs, limit)
    from .scope import build_exact_index
    index = build_exact_index(store.documents())
    rows, counts = [], Counter()
    templates = [
        ("exact_article", lambda d: f"{d.metadata['law_name']} {article_label(d)} 원문을 보여줘"),
        ("spaced_article", lambda d: f"{d.metadata['law_name']} {article_label(d, True)} 내용은?"),
        ("article_identity_adversarial", lambda d: f"다른 법 말고 {d.metadata['law_name']} {article_label(d)}만 찾아줘"),
    ]
    for document in docs:
        for question_type, make_question in templates:
            question = make_question(document)
            # The exact identity parser is the contract under test. Use a tiny
            # adapter rather than invoking Qwen thousands of times.
            from .scope import exact_request
            selected = exact_request(question, index=index)
            passed = selected is not None and [d.id for d in selected] == [document.id]
            counts[(question_type, "passed" if passed else "failed")] += 1
            rows.append({"question_type": question_type, "question": question, "expected_id": document.id,
                         "selected_ids": [d.id for d in selected] if selected is not None else None,
                         "hierarchy": hierarchy(document), "domain": domain(document), "passed": passed})
    non_articles = [d for d in store.documents() if not document_errors(d) and d.kind in {"administrative_rule", "precedent"}]
    for document in balanced_documents(non_articles):
        if document.kind == "administrative_rule":
            questions = [("administrative_rule_title", f"{document.metadata['issuing_authority']} {document.metadata['rule_type']} {document.title} 원문")]
        else:
            questions = [("precedent_case_identity", f"{document.metadata['court']} {document.metadata['case_number']} 판례")]
        for question_type, question in questions:
            selected_ids = [h.document.id for h in store.lexical(question, 24)]
            passed = document.id in selected_ids
            counts[(question_type, "passed" if passed else "failed")] += 1
            rows.append({"question_type": question_type, "question": question, "expected_id": document.id,
                         "selected_ids": selected_ids, "hierarchy": hierarchy(document),
                         "domain": domain(document), "passed": passed})
    by_hierarchy, by_domain = defaultdict(Counter), defaultdict(Counter)
    for row in rows:
        by_hierarchy[row["hierarchy"]]["total"] += 1
        by_hierarchy[row["hierarchy"]]["passed" if row["passed"] else "failed"] += 1
        by_domain[row["domain"]]["total"] += 1
        by_domain[row["domain"]]["passed" if row["passed"] else "failed"] += 1
    return {"type": "mechanical_source_identity_questions", "legal_answer_correctness_evaluated": False,
            "natural_language_semantics_evaluated": False, "total": len(rows),
            "passed": sum(r["passed"] for r in rows), "failed": sum(not r["passed"] for r in rows),
            "question_types": {f"{k[0]}_{k[1]}": v for k, v in counts.items()},
            "by_hierarchy": {k: dict(v) for k, v in by_hierarchy.items()},
            "by_domain": {k: dict(v) for k, v in by_domain.items()}, "rows": rows}
