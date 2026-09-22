# ============================================================
# Legal Effect Consequence Utils
#
# legal_effect_consequence.py에서 분리한 공통 유틸.
# 기존 점수/조건/판정 로직은 변경하지 않는다.
# ============================================================

import re

from typing import (
    Any,
    Dict,
    List,
    Set,
)

from services.evidence.legal_effect_utils import (
    clean_text,
    safe_int,
    make_article_key,
    get_article_text,
    get_article_lead_text,
    detect_effect_types,
    extract_concept_tokens,
)

from services.evidence.question_action_matcher import (
    score_question_connection,
)


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


CRIMINAL_TITLE_SUFFIXES = (
    "죄",
)


ESCALATION_TITLE_TERMS = (
    "가산금",
    "연체금",
    "독촉",
    "체납",
    "징수",
)


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


PUNITIVE_EFFECT_TYPES = {
    "형사처벌",
    "과태료",
}

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
