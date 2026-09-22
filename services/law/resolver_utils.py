# ============================================================
# Resolver 공통 문자열 / 유사도 유틸리티
#
# 특정 법령명 하드코딩 없음
# ============================================================

import re

from difflib import SequenceMatcher

from typing import (
    Any,
    Dict,
)


# ============================================================
# 기본 문자열 정리
# ============================================================

def normalize_text(
    value: Any
) -> str:

    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value)
    ).strip()


# ============================================================
# 비교용 문자열
# ============================================================

def compact_text(
    value: Any
) -> str:

    text = normalize_text(
        value
    )

    text = re.sub(
        r"[^가-힣A-Za-z0-9]",
        "",
        text
    )

    return text.lower()


# ============================================================
# 법령명 비교용 정규화
#
# 특정 법령 전용 규칙 없음
# 일반적인 연결 표현만 제거
# ============================================================

def normalize_law_name_for_matching(
    value: Any
) -> str:

    text = compact_text(
        value
    )

    generic_parts = [
        "에관한",
        "에대한",
        "및",
        "법률",
    ]

    for part in generic_parts:

        text = text.replace(
            part,
            ""
        )

    # 마지막 "법"만 제거
    if (
        text.endswith("법")
        and
        len(text) > 1
    ):

        text = text[:-1]

    return text


# ============================================================
# Bigram 생성
# ============================================================

def make_bigrams(
    text: str
) -> set:

    text = compact_text(
        text
    )

    if not text:
        return set()

    if len(text) == 1:
        return {text}

    return {
        text[index:index + 2]
        for index in range(
            len(text) - 1
        )
    }


# ============================================================
# Bigram 유사도
# ============================================================

def bigram_similarity(
    left: str,
    right: str
) -> float:

    left_set = make_bigrams(
        left
    )

    right_set = make_bigrams(
        right
    )

    if (
        not left_set
        or
        not right_set
    ):
        return 0.0

    intersection = len(
        left_set
        &
        right_set
    )

    union = len(
        left_set
        |
        right_set
    )

    if union <= 0:
        return 0.0

    return (
        intersection
        /
        union
    )


# ============================================================
# 사용자 표현 ↔ 후보 이름 하나 비교
# ============================================================

def calculate_single_match_features(
    user_expression: str,
    candidate_value: str
) -> Dict[str, Any]:

    user_raw = compact_text(
        user_expression
    )

    candidate_raw = compact_text(
        candidate_value
    )

    user_normalized = (
        normalize_law_name_for_matching(
            user_expression
        )
    )

    candidate_normalized = (
        normalize_law_name_for_matching(
            candidate_value
        )
    )

    exact_raw = (
        bool(user_raw)
        and
        user_raw == candidate_raw
    )

    exact_normalized = (
        bool(user_normalized)
        and
        user_normalized
        == candidate_normalized
    )

    raw_contained = (
        bool(user_raw)
        and
        bool(candidate_raw)
        and
        user_raw in candidate_raw
    )

    reverse_raw_contained = (
        bool(user_raw)
        and
        bool(candidate_raw)
        and
        candidate_raw in user_raw
    )

    normalized_contained = (
        bool(user_normalized)
        and
        bool(candidate_normalized)
        and
        user_normalized
        in candidate_normalized
    )

    reverse_normalized_contained = (
        bool(user_normalized)
        and
        bool(candidate_normalized)
        and
        candidate_normalized
        in user_normalized
    )

    if candidate_normalized:

        normalized_coverage = (
            len(user_normalized)
            /
            len(candidate_normalized)
        ) if user_normalized else 0.0

    else:

        normalized_coverage = 0.0

    sequence_ratio = SequenceMatcher(
        None,
        user_normalized or user_raw,
        candidate_normalized or candidate_raw
    ).ratio()

    bigram_ratio = bigram_similarity(
        user_normalized or user_raw,
        candidate_normalized or candidate_raw
    )

    return {

        "user_raw":
            user_raw,

        "candidate_raw":
            candidate_raw,

        "user_normalized":
            user_normalized,

        "candidate_normalized":
            candidate_normalized,

        "exact_raw":
            exact_raw,

        "exact_normalized":
            exact_normalized,

        "raw_contained":
            raw_contained,

        "reverse_raw_contained":
            reverse_raw_contained,

        "normalized_contained":
            normalized_contained,

        "reverse_normalized_contained":
            reverse_normalized_contained,

        "normalized_coverage":
            round(
                normalized_coverage,
                4
            ),

        "sequence_ratio":
            round(
                sequence_ratio,
                4
            ),

        "bigram_ratio":
            round(
                bigram_ratio,
                4
            ),
    }


# ============================================================
# 공식 법령명 + 공식 약칭 비교
# ============================================================

def calculate_match_features(
    user_expression: str,
    law_name: str,
    abbreviation: str = ""
) -> Dict[str, Any]:

    law_features = (
        calculate_single_match_features(
            user_expression=user_expression,
            candidate_value=law_name
        )
    )

    abbreviation_features = (
        calculate_single_match_features(
            user_expression=user_expression,
            candidate_value=abbreviation
        )
        if abbreviation
        else {}
    )

    return {

        "law":
            law_features,

        "abbreviation":
            abbreviation_features,

        "has_abbreviation":
            bool(abbreviation),
    }