# ============================================================
# 법률 Evidence 컨텍스트 공통 유틸
#
# 역할
# - 텍스트 정규화
# - 비어 있는 값 확인
# - 조문 표시명 생성
# ============================================================


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
# 2. 비어 있는 값인지 확인
# ============================================================

def has_text(
    value
):

    return bool(
        normalize_text(
            value
        )
    )


# ============================================================
# 3. 조문 표시명 생성
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

    if sub_article_number > 0:

        return (
            f"제{article_number}조의"
            f"{sub_article_number}"
        )

    return (
        f"제{article_number}조"
    )