# ============================================================
# Legal Effect Consequence
#
# Direct Anchor 이후 실제 법적 효과만 연결한다.
#
# 핵심 원칙
#
# FIRST
# - Direct 조문을 참조하면서 실제 결과 제목을 가진 조문
#   또는
# - 질문 Action + Object가 같은 조문 단위에서 직접 연결되고
#     실제 결과 제목을 가진 조문
#
# SECOND
# - FIRST 조문을 직접 참조하는 실제 후속 절차
#   또는
# - 제목 자체가 연체/독촉/체납/징수 등 후속 절차를 명확히 나타내는 조문
#   또는
# - FIRST 조문의 특정 "항"까지 직접 참조하는 제재
#
# 특정 법률명 / 특정 조문번호 하드코딩 금지
# ============================================================

import re

from typing import (
    Any,
    Dict,
    List,
    Set,
)

from services.evidence.legal_effect_constants import (
    FIRST_LEVEL_LIMIT,
    SECOND_LEVEL_LIMIT,
)

from services.evidence.legal_effect_utils import (
    clean_text,
    safe_int,
    make_article_key,
    extract_question_roles,
    get_article_text,
    get_article_lead_text,
    detect_effect_types,
    has_strong_consequence_signal,
    extract_article_references,
    extract_concept_tokens,
    has_subject_conflict,
)

from services.evidence.question_action_matcher import (
    score_question_connection,
)


# ============================================================
# 1. 실제 결과 제목으로 인정할 표현
# ============================================================

CONSEQUENCE_TITLE_TERMS = (
    "손해배상",
    "배상책임",
    "과징금",
    "과태료",
    "부담금",
    "가산금",
    "연체금",
    "징수",
    "체납",
    "독촉",
    "벌칙",
    "처벌",
    "금지청구",
)


# ============================================================
# 2. 형사 결과 제목
# ============================================================

CRIMINAL_TITLE_SUFFIXES = (
    "죄",
)


# ============================================================
# 3. SECOND 후속 절차 제목
#
# 본문에 단순 언급되는 것과 구분하기 위해
# 제목 자체에 아래 표현이 있어야
# "절차가 실제로 이어지는 조문"으로 인정한다.
# ============================================================

ESCALATION_TITLE_TERMS = (
    "가산금",
    "연체금",
    "독촉",
    "체납",
    "징수",
)


# ============================================================
# 4. 후속 절차 신호
# ============================================================

ESCALATION_TERMS = (
    "납부하지 아니",
    "납부하지 않",
    "납부기한",
    "가산금",
    "연체금",
    "독촉",
    "체납",
    "강제징수",
    "징수할 수 있다",
    "징수한다",
    "징수하여야",
    "국세 체납처분",
    "국세강제징수",
)


# ============================================================
# 5. 제재 Effect
# ============================================================

PUNITIVE_EFFECT_TYPES = {
    "형사처벌",
    "과태료",
}


# ============================================================
# 6. 조문번호 집합
# ============================================================

def get_article_numbers(
    items: List[Dict[str, Any]]
) -> Set[int]:

    results = set()

    for item in items:

        if not isinstance(item, dict):
            continue

        article = item.get(
            "article",
            {}
        )

        if not isinstance(article, dict):
            continue

        number = safe_int(
            article.get(
                "article_number"
            ),
            0
        )

        if number > 0:
            results.add(number)

    return results


# ============================================================
# 7. 조문 Key 집합
# ============================================================

def get_article_keys(
    items: List[Dict[str, Any]]
) -> Set[str]:

    results = set()

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

        if key:
            results.add(key)

    return results


# ============================================================
# 8. Concept 집합
#
# 기존 import 호환용.
# consequence 핵심 연결 기준으로는 사용하지 않는다.
# ============================================================

def build_item_concepts(
    items: List[Dict[str, Any]]
) -> Set[str]:

    results = set()

    for item in items:

        if not isinstance(item, dict):
            continue

        article = item.get(
            "article",
            {}
        )

        if not isinstance(article, dict):
            continue

        title = clean_text(
            article.get(
                "article_title"
            )
        )

        lead = get_article_lead_text(
            article,
            max_length=1200
        )

        results.update(
            extract_concept_tokens(
                f"{title} {lead}"
            )
        )

    return results


# ============================================================
# 9. 조문 의미 단위 분리
# ============================================================

def split_article_units(
    article: Dict[str, Any]
) -> List[str]:

    text = clean_text(
        get_article_text(
            article
        )
    )

    if not text:
        return []

    text = re.sub(
        r"(?=[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳])",
        "\n",
        text,
    )

    parts = re.split(
        r"\n+",
        text
    )

    results = []

    for part in parts:

        part = clean_text(part)

        if not part:
            continue

        if len(part) <= 700:
            results.append(part)
            continue

        sentences = re.split(
            r"(?<=[다요음함됨임])\.\s+",
            part
        )

        for sentence in sentences:

            sentence = clean_text(
                sentence
            )

            if sentence:
                results.append(
                    sentence
                )

    return results or [text]


# ============================================================
# 10. 질문 Action + Object가 같은 단위에서 연결되는지
# ============================================================

def find_query_connected_units(
    question: str,
    article: Dict[str, Any]
) -> List[str]:

    results = []

    for unit in split_article_units(
        article
    ):

        match = score_question_connection(
            question=question,
            title="",
            body=unit,
        )

        if bool(
            match.get(
                "combined_match"
            )
        ):
            results.append(unit)

    return results


# ============================================================
# 11. Effect Type
# ============================================================

def get_effect_types(
    article: Dict[str, Any]
) -> List[str]:

    text = get_article_text(
        article
    )

    results = list(
        detect_effect_types(
            text
        )
    )

    if (
        "과징금" in text
        and
        "과징금" not in results
    ):
        results.append(
            "과징금"
        )

    return results


# ============================================================
# 12. 제목이 실제 법적 결과를 나타내는지
# ============================================================

def has_consequence_title(
    article: Dict[str, Any]
) -> bool:

    title = clean_text(
        article.get(
            "article_title"
        )
    )

    if not title:
        return False

    if any(
        term in title
        for term in CONSEQUENCE_TITLE_TERMS
    ):
        return True

    if any(
        title.endswith(suffix)
        for suffix in CRIMINAL_TITLE_SUFFIXES
    ):
        return True

    return False


# ============================================================
# 13. 제목이 실제 후속 절차를 나타내는지
# ============================================================

def has_escalation_title(
    article: Dict[str, Any]
) -> bool:

    title = clean_text(
        article.get(
            "article_title"
        )
    )

    if not title:
        return False

    return any(
        term in title
        for term in ESCALATION_TITLE_TERMS
    )


# ============================================================
# 14. 실제 후속 징수/체납 신호
# ============================================================

def has_escalation_signal(
    article: Dict[str, Any]
) -> bool:

    text = get_article_text(
        article
    )

    return any(
        term in text
        for term in ESCALATION_TERMS
    )


# ============================================================
# 15. 특정 "항"까지 참조하는지
# ============================================================

def has_specific_paragraph_reference(
    text: str,
    target_numbers: Set[int]
) -> bool:

    text = clean_text(text)

    if not text:
        return False

    for number in target_numbers:

        pattern = (
            rf"제\s*{number}\s*조"
            rf"(?:의\s*\d+)?"
            rf"\s*제\s*\d+\s*항"
        )

        if re.search(
            pattern,
            text
        ):
            return True

    return False


# ============================================================
# 16. FIRST
# ============================================================

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


# ============================================================
# 17. SECOND
# ============================================================

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


# ============================================================
# 18. 중복 제거
# ============================================================

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
