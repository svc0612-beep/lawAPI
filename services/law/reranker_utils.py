# ============================================================
# Reranker 공통 문자열 유틸리티
# ============================================================

import re


def normalize_text(
    value
):

    if value is None:
        return ""

    text = str(
        value
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def compact_text(
    value
):

    text = normalize_text(
        value
    )

    text = re.sub(
        r"[^가-힣A-Za-z0-9]",
        "",
        text
    )

    return text.lower()


def partial_match_score(
    query_token: str,
    target_text: str
):

    query_token = compact_text(
        query_token
    )

    target_text = compact_text(
        target_text
    )

    if not query_token:
        return 0.0

    if not target_text:
        return 0.0

    # ========================================================
    # 완전 포함
    # ========================================================

    if query_token in target_text:
        return 1.0

    # ========================================================
    # target이 query 안에 포함
    #
    # 너무 짧은 문자열은 오탐 위험이 있으므로
    # 최소 2글자 이상
    # ========================================================

    if (
        len(target_text) >= 2
        and
        target_text in query_token
    ):

        ratio = (
            len(target_text)
            /
            len(query_token)
        )

        if ratio >= 0.5:
            return ratio

    # ========================================================
    # 가장 긴 공통 연속 부분문자열
    #
    # 의미 사전 사용 없음
    # ========================================================

    min_len = min(
        len(query_token),
        len(target_text)
    )

    if min_len < 2:
        return 0.0

    best = 0

    for start in range(
        len(query_token)
    ):

        for end in range(
            start + 2,
            len(query_token) + 1
        ):

            part = query_token[
                start:end
            ]

            if (
                len(part) > best
                and
                part in target_text
            ):

                best = len(
                    part
                )

    if best <= 0:
        return 0.0

    ratio = (
        best
        /
        len(query_token)
    )

    if ratio >= 0.5:
        return ratio

    return 0.0