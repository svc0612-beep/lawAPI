# ============================================================
# 법률 응답 공통 유틸리티
#
# 역할
# - 텍스트 정리
# - 날짜 표시
# - 조문 번호 표시
# - LLM 쉬운 설명 정리
# ============================================================

import re


# ============================================================
# 1. 텍스트 정리
# ============================================================

def clean_text(
    value
):

    if value is None:
        return ""

    return str(
        value
    ).strip()


# ============================================================
# 2. 날짜 정리
# ============================================================

def format_date(
    value
):

    text = clean_text(
        value
    )

    if not text:
        return ""

    digits = re.sub(
        r"\D",
        "",
        text
    )

    if len(digits) >= 8:

        return (
            f"{digits[0:4]}."
            f"{digits[4:6]}."
            f"{digits[6:8]}"
        )

    return text


# ============================================================
# 3. 조문 표시
# ============================================================

def make_article_label(
    article_number,
    sub_article_number=0
):

    if article_number is None:
        return ""

    try:

        article_number = int(
            article_number
        )

    except (
        TypeError,
        ValueError
    ):

        return ""

    try:

        sub_article_number = int(
            sub_article_number
            or 0
        )

    except (
        TypeError,
        ValueError
    ):

        sub_article_number = 0

    if sub_article_number:

        return (
            f"제{article_number}조의"
            f"{sub_article_number}"
        )

    return (
        f"제{article_number}조"
    )


# ============================================================
# 4. LLM 쉬운 설명 정리
# ============================================================

def clean_llm_explanation(
    value
):

    text = clean_text(
        value
    )

    if not text:
        return ""

    # ========================================================
    # 혹시 모델이 제목을 출력하면 제거
    # ========================================================

    unwanted_headers = [

        "[답변]",
        "[쉽게 설명하면]",
        "[근거 법령]",
        "[관련 법령]",
        "[관련 판례]",
        "[법령해석례]",
        "[국회도서관 참고자료]",
        "[출처]",
    ]

    # 현재 기존 로직과의 호환성을 위해 유지
    _ = unwanted_headers

    # 출처 계열 제목이 나오면
    # 그 이후는 버린다.
    cut_headers = [

        "[근거 법령]",
        "[관련 법령]",
        "[관련 판례]",
        "[법령해석례]",
        "[국회도서관 참고자료]",
        "[출처]",
    ]

    positions = []

    for header in cut_headers:

        position = text.find(
            header
        )

        if position >= 0:

            positions.append(
                position
            )

    if positions:

        text = text[
            :min(
                positions
            )
        ]

    # 설명용 제목만 제거
    text = text.replace(
        "[답변]",
        ""
    )

    text = text.replace(
        "[쉽게 설명하면]",
        ""
    )

    return text.strip()