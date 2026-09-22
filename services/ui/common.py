# ============================================================
# LawMate UI 공통 유틸
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
# 2. 날짜 표시
#
# 20251111121100
# 20251111
# 2025.11.11
#
# 모두 가능한 범위에서 2025.11.11 형태로 표시한다.
# ============================================================

def format_date(
    value
):

    text = clean_text(
        value
    )

    if not text:
        return "-"

    match = re.search(
        r"(\d{4})(\d{2})(\d{2})",
        text
    )

    if not match:
        return text

    return (
        f"{match.group(1)}."
        f"{match.group(2)}."
        f"{match.group(3)}"
    )


# ============================================================
# 3. 조문 표시명
# ============================================================

def make_article_label(
    article_number,
    sub_article_number=0
):

    if article_number is None:
        return "조문"

    try:

        article_number = int(
            article_number
        )

    except (
        TypeError,
        ValueError
    ):

        return f"제{article_number}조"

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
# 4. 법령 전문 내부 검색
# ============================================================

def contains_keyword(
    article,
    keyword
):

    keyword = clean_text(
        keyword
    ).lower()

    if not keyword:
        return True

    targets = [

        clean_text(
            article.get(
                "article_title"
            )
        ),

        clean_text(
            article.get(
                "full_text"
            )
        ),

        clean_text(
            article.get(
                "article_content"
            )
        ),
    ]

    combined = " ".join(
        targets
    ).lower()

    return keyword in combined