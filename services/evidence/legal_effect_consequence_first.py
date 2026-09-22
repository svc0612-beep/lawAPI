# ============================================================
# Legal Effect Consequence - FIRST
#
# Direct Anchor 이후 1차 법적 효과 탐색.
# 기존 점수/조건/정렬/limit 로직을 그대로 유지한다.
# ============================================================

from typing import (
    Any,
    Dict,
    List,
)

from services.evidence.legal_effect_constants import (
    FIRST_LEVEL_LIMIT,
)

from services.evidence.legal_effect_utils import (
    safe_int,
    make_article_key,
    extract_question_roles,
    get_article_text,
    has_strong_consequence_signal,
    extract_article_references,
    has_subject_conflict,
)

from services.evidence.legal_effect_consequence_utils import (
    get_article_numbers,
    get_article_keys,
    get_effect_types,
    find_query_connected_units,
    has_consequence_title,
)

def find_first_level_consequences(
    articles: List[Dict[str, Any]],
    question: str,
    direct_anchors: List[Dict[str, Any]],
    seed_map: Dict[str, Dict[str, Any]]
) -> List[Dict[str, Any]]:

    if not direct_anchors:
        return []

    direct_numbers = get_article_numbers(
        direct_anchors
    )

    direct_keys = get_article_keys(
        direct_anchors
    )

    question_roles = extract_question_roles(
        question
    )

    results = []

    for article in articles:

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

        if key in direct_keys:
            continue

        if has_subject_conflict(
            article,
            question_roles
        ):
            continue

        effect_types = get_effect_types(
            article
        )

        if not effect_types:
            continue

        text = get_article_text(
            article
        )

        own_number = safe_int(
            article.get(
                "article_number"
            ),
            0
        )

        references = extract_article_references(
            text,
            own_article_number=(
                own_number
                if own_number
                else None
            ),
        )

        referenced_direct = (
            references
            &
            direct_numbers
        )

        query_units = find_query_connected_units(
            question=question,
            article=article,
        )

        query_connected = bool(
            query_units
        )

        consequence_title = (
            has_consequence_title(
                article
            )
        )

        # ----------------------------------------------------
        # 핵심:
        #
        # query_connected 만으로는 통과하지 않는다.
        # "실제 결과 제목"까지 있어야 FIRST가 된다.
        #
        # 이 규칙으로 특허 제131조(신용회복)는 빠지고,
        # 제128조 손해배상 / 제225조 침해죄는 유지된다.
        # ----------------------------------------------------

        connected = (
            consequence_title
            and
            (
                bool(
                    referenced_direct
                )
                or
                query_connected
            )
        )

        if not connected:
            continue

        if not has_strong_consequence_signal(
            article
        ):

            if (
                "과징금" not in effect_types
                and
                "손해배상" not in effect_types
            ):
                continue

        is_seed = (
            key in seed_map
        )

        score = 0.0

        if referenced_direct:
            score += 40.0

        if query_connected:
            score += 35.0

        if consequence_title:
            score += 20.0

        if is_seed:
            score += 5.0

        score += (
            len(
                effect_types
            )
            *
            2.0
        )

        results.append(
            {
                "article": article,
                "score": score,
                "effect_types": effect_types,
                "references": sorted(
                    references
                ),
                "referenced_direct_articles": sorted(
                    referenced_direct
                ),
                "query_connected": query_connected,
                "query_connected_units": query_units[:3],
                "consequence_title": consequence_title,
                "seed": is_seed,
                "connection_level": 1,
            }
        )

    results.sort(
        key=lambda item: (
            -float(
                item.get(
                    "score",
                    0
                )
                or
                0
            ),
            safe_int(
                item.get(
                    "article",
                    {}
                ).get(
                    "article_number"
                ),
                999999
            ),
        )
    )

    return results[
        :FIRST_LEVEL_LIMIT
    ]
