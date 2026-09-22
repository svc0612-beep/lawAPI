# ============================================================
# Legal Effect Consequence - SECOND
#
# FIRST 이후 2차 후속 법적 효과 탐색.
# 기존 점수/조건/정렬/limit 로직을 그대로 유지한다.
# ============================================================

from typing import (
    Any,
    Dict,
    List,
)

from services.evidence.legal_effect_constants import (
    SECOND_LEVEL_LIMIT,
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
    PUNITIVE_EFFECT_TYPES,
    get_article_numbers,
    get_article_keys,
    get_effect_types,
    has_escalation_signal,
    has_escalation_title,
    has_specific_paragraph_reference,
)

def find_second_level_consequences(
    articles: List[Dict[str, Any]],
    question: str,
    direct_anchors: List[Dict[str, Any]],
    first_level: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    if not first_level:
        return []

    first_numbers = get_article_numbers(
        first_level
    )

    excluded_keys = (
        get_article_keys(
            direct_anchors
        )
        |
        get_article_keys(
            first_level
        )
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

        if key in excluded_keys:
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

        referenced_first = (
            references
            &
            first_numbers
        )

        escalation = (
            has_escalation_signal(
                article
            )
        )

        escalation_title = (
            has_escalation_title(
                article
            )
        )

        specific_paragraph_reference = (
            has_specific_paragraph_reference(
                text,
                referenced_first
            )
        )

        punitive = bool(
            set(
                effect_types
            )
            &
            PUNITIVE_EFFECT_TYPES
        )

        # ----------------------------------------------------
        # 핵심:
        #
        # A. 제목 자체가 실제 후속 절차(가산금/연체금/독촉/체납/징수)
        #    를 나타내고 본문에도 escalation 신호가 있으면 허용.
        #
        #    → 제37조 독촉 및 체납처분 포함
        #
        # B. FIRST 조문의 특정 항까지 직접 참조하는 제재 허용.
        #
        #    → 제86조 과태료 유지
        #
        # 단순히 본문에서 "독촉/체납"을 언급한
        # 제41조 시효의 중단은 제목 gate를 통과하지 못하므로 제외.
        # ----------------------------------------------------

        connected = (
            (
                escalation
                and
                escalation_title
            )
            or
            (
                bool(
                    referenced_first
                )
                and
                punitive
                and
                specific_paragraph_reference
            )
        )

        if not connected:
            continue

        if not has_strong_consequence_signal(
            article
        ):

            if "과징금" not in effect_types:
                continue

        score = 0.0

        if (
            escalation
            and
            escalation_title
        ):
            score += 40.0

        if (
            referenced_first
            and
            punitive
            and
            specific_paragraph_reference
        ):
            score += 45.0

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
                "referenced_first_level_articles": sorted(
                    referenced_first
                ),
                "escalation": escalation,
                "escalation_title": escalation_title,
                "specific_paragraph_reference": (
                    specific_paragraph_reference
                ),
                "punitive": punitive,
                "connection_level": 2,
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
        :SECOND_LEVEL_LIMIT
    ]
