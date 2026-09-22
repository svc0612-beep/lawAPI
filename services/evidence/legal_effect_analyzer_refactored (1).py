# ============================================================
# Legal Effect Analyzer
#
# 역할:
# - Direct 근거 탐색
# - Direct Anchor 선정
# - 1차/2차 법적 효과 탐색
# - 최종 결과 조립
#
# 세부 로직은 아래 모듈로 분리한다.
# ============================================================

from typing import Any, Dict, List, Optional

from services.evidence.legal_effect_constants import (
    DIRECT_BASIS_LIMIT,
    FIRST_LEVEL_LIMIT,
    SECOND_LEVEL_LIMIT,
    DIRECT_ANCHOR_RATIO,
    QUESTION_STOP_WORDS,
    LEGAL_ROLE_ALIASES,
    KNOWN_LEGAL_SUBJECTS,
    TITLE_DIRECT_TERMS,
    NORMATIVE_TERMS,
    LEGAL_EFFECT_TERMS,
    STRONG_CONSEQUENCE_TERMS,
    CONSEQUENCE_TITLE_TERMS,
    CONCEPT_STOP_WORDS,
)

from services.evidence.legal_effect_utils import (
    clean_text,
    normalize_for_match,
    normalize_law_name,
    safe_int,
    make_article_key,
    extract_question_tokens,
    extract_question_roles,
    get_article_text,
    get_article_lead_text,
    count_matches,
    detect_title_roles,
    detect_normative_roles,
    detect_effect_types,
    has_strong_consequence_signal,
    extract_article_references,
    extract_concept_tokens,
    get_title_subjects,
    has_subject_conflict,
)

from services.evidence.legal_effect_direct import (
    build_seed_article_map,
    score_direct_article,
    find_direct_basis_articles,
    select_direct_anchors,
)

from services.evidence.legal_effect_consequence import (
    get_article_numbers,
    build_item_concepts,
    find_first_level_consequences,
    find_second_level_consequences,
    deduplicate_items,
)


def analyze_legal_effects(
    question: str,
    full_law: Dict[str, Any],
    seed_laws: Optional[List[Dict[str, Any]]] = None,
    primary_law_name: str = "",
) -> Dict[str, Any]:
    """공식 법령 전체 조문을 기반으로 법적 효과 흐름을 분석한다."""

    if not isinstance(full_law, dict):
        return {
            "status": "error",
            "direct_basis": [],
            "direct_anchors": [],
            "first_level_consequences": [],
            "second_level_consequences": [],
            "consequence_basis": [],
        }

    articles = full_law.get("articles", [])
    if not isinstance(articles, list):
        articles = []

    if not primary_law_name:
        primary_law_name = clean_text(full_law.get("law_name"))

    seed_map = build_seed_article_map(
        seed_laws=seed_laws if isinstance(seed_laws, list) else [],
        primary_law_name=primary_law_name,
    )

    direct_basis = find_direct_basis_articles(
        articles=articles,
        question=question,
        seed_map=seed_map,
    )

    direct_anchors = select_direct_anchors(direct_basis)

    first_level = find_first_level_consequences(
        articles=articles,
        question=question,
        direct_anchors=direct_anchors,
        seed_map=seed_map,
    )

    second_level = find_second_level_consequences(
        articles=articles,
        question=question,
        direct_anchors=direct_anchors,
        first_level=first_level,
    )

    consequence_basis = deduplicate_items(first_level + second_level)

    return {
        "status": "success",
        "law_name": clean_text(primary_law_name),
        "direct_basis": direct_basis,
        "direct_anchors": direct_anchors,
        "first_level_consequences": first_level,
        "second_level_consequences": second_level,
        "consequence_basis": consequence_basis,
        "direct_basis_count": len(direct_basis),
        "direct_anchor_count": len(direct_anchors),
        "first_level_count": len(first_level),
        "second_level_count": len(second_level),
        "consequence_basis_count": len(consequence_basis),
        "seed_article_count": len(seed_map),
    }
