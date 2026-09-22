# ============================================================
# Reranker 관련성 통과 규칙
#
# 핵심 원칙
# - fallback 여부와 무관하게 실제 질의 토큰 일치가 최소 1개 필요
# - aiSearch 원본 순위만으로 coverage=0 후보를 통과시키지 않음
# ============================================================


def is_relevant(
    scoring: dict,
    fallback_mode: bool = False
):

    score = scoring.get(
        "score",
        0
    )

    coverage = scoring.get(
        "coverage",
        0
    )

    original_rank = scoring.get(
        "original_rank",
        999
    )

    matched_tokens = scoring.get(
        "matched_tokens",
        []
    )

    # ========================================================
    # 1. 실제 문자열 근거가 하나도 없으면 제거
    # ========================================================

    if (
        coverage <= 0
        or
        not matched_tokens
    ):

        return False

    # ========================================================
    # 2. fallback
    #
    # 표현 차이 때문에 일반 검색보다 문턱은 낮게 유지하되,
    # 최소한 실제 토큰 일치는 반드시 요구한다.
    # ========================================================

    if fallback_mode:

        if score >= 7:
            return True

        if (
            original_rank <= 5
            and
            coverage >= 0.5
        ):

            return True

        return False

    # ========================================================
    # 3. 일반 자유검색
    # ========================================================

    if score < 8:
        return False

    return True
