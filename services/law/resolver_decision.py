# ============================================================
# Resolver 자동 확정 판단
#
# 핵심:
#
# 공식 법령명 정확 일치
# → 확정
#
# 공식 약칭 정확 일치
# → 확정
#
# 약칭 일부 일치
# → 매우 엄격하게 판단
#
# 짧거나 애매한 표현
# → ambiguous
# ============================================================

from typing import (
    Any,
    Dict,
    Optional,
)


def can_auto_resolve(
    top: Dict[str, Any],
    second: Optional[
        Dict[str, Any]
    ] = None
) -> bool:

    if not top:
        return False

    features = top.get(
        "match_features",
        {}
    )

    law_features = features.get(
        "law",
        {}
    )

    abbreviation_features = features.get(
        "abbreviation",
        {}
    )

    top_score = top.get(
        "resolver_score",
        0
    )

    second_score = (
        second.get(
            "resolver_score",
            0
        )
        if second
        else 0
    )

    score_gap = (
        top_score
        -
        second_score
    )

    # ========================================================
    # 1. 공식 법령명 완전 일치
    # ========================================================

    if law_features.get(
        "exact_raw"
    ):
        return True

    # ========================================================
    # 2. 공식 약칭 완전 일치
    # ========================================================

    if abbreviation_features.get(
        "exact_raw"
    ):
        return True

    # ========================================================
    # 3. 공식 약칭 정규화 후 완전 일치
    # ========================================================

    if abbreviation_features.get(
        "exact_normalized"
    ):
        return True

    # ========================================================
    # 4. 공식 법령명 정규화 후 완전 일치
    # ========================================================

    if law_features.get(
        "exact_normalized"
    ):
        return True

    # ========================================================
    # 5. 공식 법령명 부분 포함
    # ========================================================

    if law_features.get(
        "raw_contained"
    ):

        user_raw = law_features.get(
            "user_raw",
            ""
        )

        candidate_raw = law_features.get(
            "candidate_raw",
            ""
        )

        coverage = (
            len(user_raw)
            /
            len(candidate_raw)
            if candidate_raw
            else 0
        )

        if (
            top_score >= 65
            and
            coverage >= 0.30
            and
            (
                score_gap >= 8
                or
                second is None
            )
        ):

            return True

    # ========================================================
    # 6. 공식 약칭 부분 포함
    #
    # 예:
    # 형사법
    # ⊂ 주한미군형사법
    #
    # 이런 경우 자동 확정 방지
    # ========================================================

    if abbreviation_features.get(
        "raw_contained"
    ):

        user_raw = abbreviation_features.get(
            "user_raw",
            ""
        )

        abbreviation_raw = (
            abbreviation_features.get(
                "candidate_raw",
                ""
            )
        )

        coverage = (
            len(user_raw)
            /
            len(abbreviation_raw)
            if abbreviation_raw
            else 0
        )

        if (
            coverage >= 0.80
            and
            top_score >= 80
            and
            (
                score_gap >= 15
                or
                second is None
            )
        ):

            return True

    # ========================================================
    # 7. 유사도 기반 자동 확정
    #
    # 짧은 표현은 자동 확정 금지
    # ========================================================

    user_normalized = law_features.get(
        "user_normalized",
        ""
    )

    if len(
        user_normalized
    ) < 4:

        return False

    normalized_coverage = (
        law_features.get(
            "normalized_coverage",
            0
        )
    )

    sequence_ratio = (
        law_features.get(
            "sequence_ratio",
            0
        )
    )

    if (
        top_score >= 75
        and
        normalized_coverage >= 0.45
        and
        sequence_ratio >= 0.60
        and
        score_gap >= 15
    ):

        return True

    return False