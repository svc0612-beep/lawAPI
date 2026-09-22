# ============================================================
# Resolver 후보 점수 계산
# ============================================================

from typing import (
    Any,
    Dict,
)

from services.law.resolver_utils import (
    calculate_match_features,
)


# ============================================================
# 이름 하나의 점수
# ============================================================

def score_single_name(
    features: Dict[str, Any],
    exact_bonus: float,
    normalized_exact_bonus: float,
    contained_bonus: float
) -> float:

    if not features:
        return 0.0

    score = 0.0

    if features.get(
        "exact_raw"
    ):
        score += exact_bonus

    if features.get(
        "exact_normalized"
    ):
        score += normalized_exact_bonus

    if (
        features.get(
            "raw_contained"
        )
        and
        not features.get(
            "exact_raw"
        )
    ):

        user_raw = features.get(
            "user_raw",
            ""
        )

        candidate_raw = features.get(
            "candidate_raw",
            ""
        )

        ratio = (
            len(user_raw)
            /
            len(candidate_raw)
            if candidate_raw
            else 0
        )

        score += (
            contained_bonus
            +
            ratio * 25
        )

    if (
        features.get(
            "reverse_raw_contained"
        )
        and
        not features.get(
            "exact_raw"
        )
    ):

        candidate_raw = features.get(
            "candidate_raw",
            ""
        )

        user_raw = features.get(
            "user_raw",
            ""
        )

        ratio = (
            len(candidate_raw)
            /
            len(user_raw)
            if user_raw
            else 0
        )

        score += (
            15
            +
            ratio * 15
        )

    if features.get(
        "normalized_contained"
    ):

        score += (
            20
            +
            features.get(
                "normalized_coverage",
                0
            ) * 25
        )

    score += (
        features.get(
            "sequence_ratio",
            0
        )
        *
        25
    )

    score += (
        features.get(
            "bigram_ratio",
            0
        )
        *
        15
    )

    return score


# ============================================================
# 법령 후보 전체 점수
# ============================================================

def score_law_candidate(
    user_expression: str,
    law_name: str,
    abbreviation: str = "",
    original_rank: int = 999
) -> float:

    features = calculate_match_features(
        user_expression=user_expression,
        law_name=law_name,
        abbreviation=abbreviation
    )

    # 공식 법령명 점수
    law_score = score_single_name(

        features=features["law"],

        exact_bonus=120,

        normalized_exact_bonus=90,

        contained_bonus=50
    )

    # 공식 약칭 점수
    abbreviation_score = 0.0

    if features.get(
        "has_abbreviation"
    ):

        abbreviation_score = score_single_name(

            features=features[
                "abbreviation"
            ],

            exact_bonus=150,

            normalized_exact_bonus=120,

            contained_bonus=60
        )

    # 두 값을 더하지 않고 더 강한 쪽 사용
    score = max(
        law_score,
        abbreviation_score
    )

    # 검색 원본 순위는 보조 점수
    if original_rank <= 10:

        score += max(
            0,
            6 - original_rank * 0.4
        )

    return round(
        score,
        2
    )