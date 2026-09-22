# ============================================================
# 국회도서관 공통 유틸
#
# 역할
# - 텍스트 정리
# - 키워드 문자열 분리
# ============================================================

import re


# ============================================================
# 1. 텍스트 정리
# ============================================================

def normalize_text(
    value
):

    if value is None:

        return ""

    return str(
        value
    ).strip()


# ============================================================
# 2. 키워드 문자열 → 리스트
# ============================================================

def split_keywords(
    keyword_text: str
):

    keyword_text = normalize_text(
        keyword_text
    )

    if not keyword_text:

        return []

    keyword_text = re.sub(
        r"\s+",
        " ",
        keyword_text
    ).strip()

    return [

        token

        for token in keyword_text.split(
            " "
        )

        if token
    ]