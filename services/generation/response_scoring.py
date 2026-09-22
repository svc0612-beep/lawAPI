# ============================================================
# Response Scoring
#
# 역할:
# - 자연어 질문의 간단한 토큰 처리
# - aiSearch fallback 문장/조문 점수 계산
# - 특정 법률명/조문번호 하드코딩 금지
# ============================================================

import re

from typing import (
    Any,
    Dict,
    List,
)

from services.generation.response_utils import (
    clean_text,
)


CORE_TEXT_LIMIT = 430


STOP_WORDS = {
    "관련",
    "대한",
    "대해",
    "대해서",
    "알려줘",
    "알려",
    "뭐야",
    "무엇",
    "어떻게",
    "어떻게돼",
    "어떻게되",
    "하면",
    "하는",
    "회사에서",
    "회사",
    "경우",
    "있어",
    "있나요",
    "되는",
    "되나요",
}


LEGAL_EFFECT_TERMS = (
    "의무",
    "하여야 한다",
    "해야 한다",
    "금지",
    "아니 된다",
    "부담금",
    "가산금",
    "연체금",
    "독촉",
    "체납처분",
    "과태료",
    "벌금",
    "징역",
    "처한다",
    "손해배상",
    "배상",
    "취소",
    "정지",
    "위반",
)


CONSEQUENCE_QUESTION_TERMS = (
    "안 하면",
    "안하면",
    "위반",
    "처벌",
    "벌금",
    "과태료",
    "어떻게 돼",
    "어떻게돼",
    "어떻게 되",
    "책임",
    "문제",
)


def normalize_for_match(
    value: Any
) -> str:

    text = clean_text(
        value
    ).lower()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def extract_question_tokens(
    question: str
) -> List[str]:

    question = normalize_for_match(
        question
    )

    if not question:
        return []

    raw_tokens = re.findall(
        r"[가-힣A-Za-z0-9]+",
        question
    )

    results = []

    for token in raw_tokens:

        token = token.strip()

        if len(
            token
        ) < 2:
            continue

        if token in STOP_WORDS:
            continue

        if token not in results:
            results.append(
                token
            )

    return results


def is_consequence_question(
    question: str
) -> bool:

    question = normalize_for_match(
        question
    )

    return any(
        term in question
        for term in CONSEQUENCE_QUESTION_TERMS
    )


def count_token_matches(
    tokens: List[str],
    text: str
) -> int:

    text = normalize_for_match(
        text
    )

    if not text:
        return 0

    return sum(
        1
        for token in tokens
        if token in text
    )


def count_legal_effect_terms(
    text: str
) -> int:

    text = normalize_for_match(
        text
    )

    if not text:
        return 0

    return sum(
        1
        for term in LEGAL_EFFECT_TERMS
        if term in text
    )


def split_legal_text(
    text: str
) -> List[str]:

    text = clean_text(
        text
    )

    if not text:
        return []

    text = re.sub(
        r"(?=[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳])",
        "\n",
        text,
    )

    parts = re.split(
        r"(?<=[.!?])\s+|\n+",
        text,
    )

    results = []

    for part in parts:

        part = clean_text(
            part
        )

        if not part:
            continue

        if part not in results:
            results.append(
                part
            )

    return results


def score_statement(
    statement: str,
    question: str,
    title: str = ""
) -> float:

    statement = clean_text(
        statement
    )

    if not statement:
        return -1.0

    question_tokens = (
        extract_question_tokens(
            question
        )
    )

    title_tokens = (
        extract_question_tokens(
            title
        )
    )

    score = 0.0

    score += (
        count_token_matches(
            question_tokens,
            statement
        )
        *
        5.0
    )

    score += (
        count_token_matches(
            title_tokens,
            statement
        )
        *
        2.0
    )

    score += (
        count_legal_effect_terms(
            statement
        )
        *
        3.0
    )

    if is_consequence_question(
        question
    ):

        score += (
            count_legal_effect_terms(
                statement
            )
            *
            2.0
        )

    return score


def extract_core_statement(
    evidence: Dict[str, Any],
    question: str
) -> str:

    if not isinstance(
        evidence,
        dict
    ):
        return ""

    article_text = clean_text(
        evidence.get(
            "article_text"
        )
        or
        evidence.get(
            "full_text"
        )
    )

    title = clean_text(
        evidence.get(
            "article_title"
        )
    )

    if not article_text:
        return ""

    statements = split_legal_text(
        article_text
    )

    if not statements:

        result = article_text[
            :CORE_TEXT_LIMIT
        ]

        if len(
            article_text
        ) > CORE_TEXT_LIMIT:

            result = (
                result.rstrip()
                +
                "..."
            )

        return result

    scored = []

    for index, statement in enumerate(
        statements
    ):

        score = score_statement(
            statement=statement,
            question=question,
            title=title,
        )

        scored.append(
            (
                score,
                index,
                statement,
            )
        )

    scored.sort(
        key=lambda item: (
            -item[0],
            item[1],
        )
    )

    best = scored[
        0
    ][2]

    if len(
        best
    ) > CORE_TEXT_LIMIT:

        best = (
            best[
                :CORE_TEXT_LIMIT
            ].rstrip()
            +
            "..."
        )

    return best


def score_law_item(
    item: dict,
    question: str
) -> float:

    if not isinstance(
        item,
        dict
    ):
        return -1.0

    tokens = extract_question_tokens(
        question
    )

    law_name = clean_text(
        item.get(
            "law_name"
        )
    )

    title = clean_text(
        item.get(
            "article_title"
        )
    )

    article_text = clean_text(
        item.get(
            "article_text"
        )
    )

    score = 0.0

    score += (
        count_token_matches(
            tokens,
            law_name
        )
        *
        3.0
    )

    score += (
        count_token_matches(
            tokens,
            title
        )
        *
        9.0
    )

    score += (
        count_token_matches(
            tokens,
            article_text
        )
        *
        2.5
    )

    if is_consequence_question(
        question
    ):

        score += (
            count_legal_effect_terms(
                title
            )
            *
            5.0
        )

    return score
