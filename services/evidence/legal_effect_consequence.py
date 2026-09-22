# ============================================================
# Legal Effect Consequence
#
# Direct Anchor 이후 실제 법적 효과 연결의 public entry.
#
# 역할 분리:
# - legal_effect_consequence_utils.py  : 공통 판정/참조 유틸
# - legal_effect_consequence_first.py  : FIRST 탐색
# - legal_effect_consequence_second.py : SECOND 탐색
#
# 기존 import 호환성을 위해 public 함수/상수를 re-export한다.
# ============================================================

from typing import (
    Any,
    Dict,
    List,
)

from services.evidence.legal_effect_utils import (
    make_article_key,
)

from services.evidence.legal_effect_consequence_utils import (
    CONSEQUENCE_TITLE_TERMS,
    CRIMINAL_TITLE_SUFFIXES,
    ESCALATION_TITLE_TERMS,
    ESCALATION_TERMS,
    PUNITIVE_EFFECT_TYPES,
    get_article_numbers,
    get_article_keys,
    build_item_concepts,
    split_article_units,
    find_query_connected_units,
    get_effect_types,
    has_consequence_title,
    has_escalation_title,
    has_escalation_signal,
    has_specific_paragraph_reference,
)

from services.evidence.legal_effect_consequence_first import (
    find_first_level_consequences,
)

from services.evidence.legal_effect_consequence_second import (
    find_second_level_consequences,
)


def deduplicate_items(
    items: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    results = []
    seen = set()

    for item in items:

        if not isinstance(item, dict):
            continue

        article = item.get(
            "article",
            {}
        )

        if not isinstance(article, dict):
            continue

        key = make_article_key(
            article.get(
                "article_number"
            ),
            article.get(
                "sub_article_number",
                0
            ),
        )

        if not key:
            continue

        if key in seen:
            continue

        seen.add(key)
        results.append(item)

    return results
