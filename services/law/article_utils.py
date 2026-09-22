# ============================================================
# 법령 조문 조회 공통 유틸리티
# ============================================================


# ============================================================
# JO 코드 생성
#
# 제1조
# → 000100
#
# 제10조
# → 001000
#
# 제10조의2
# → 001002
# ============================================================

def make_jo_code(
    article_number: int,
    sub_article_number: int = 0
):

    article_number = int(
        article_number
    )

    sub_article_number = int(
        sub_article_number
        or 0
    )

    return (
        f"{article_number:04d}"
        f"{sub_article_number:02d}"
    )


# ============================================================
# list 형태 보장
# ============================================================

def ensure_list(
    value
):

    if value is None:
        return []

    if isinstance(
        value,
        list
    ):
        return value

    if isinstance(
        value,
        dict
    ):
        return [
            value
        ]

    return []