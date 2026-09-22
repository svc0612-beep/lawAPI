# ============================================================
# aiSearch 응답 Parser
#
# 역할
#
# 1. 실제 aiSearch 조문 판별
# 2. 중첩 응답에서 실제 조문만 재귀 탐색
# 3. 결과 1건 정규화
# 4. 전체 결과 정규화
# ============================================================

from services.law.ai_search_utils import (
    normalize_text,
    safe_int,
)


# ============================================================
# 실제 aiSearch 조문 여부
# ============================================================

def is_ai_search_item(
    item
):

    if not isinstance(
        item,
        dict
    ):

        return False

    has_law_name = (
        "법령명" in item
        or
        "법령명한글" in item
    )

    has_article_data = (
        "조문내용" in item
        or
        "조문번호" in item
    )

    return (
        has_law_name
        and
        has_article_data
    )


# ============================================================
# 응답 전체에서 실제 aiSearch 조문 재귀 탐색
# ============================================================

def extract_ai_search_list(
    data
):

    results = []

    def walk(
        value
    ):

        # ====================================================
        # dict
        # ====================================================

        if isinstance(
            value,
            dict
        ):

            if is_ai_search_item(
                value
            ):

                results.append(
                    value
                )

                return

            for child in value.values():

                walk(
                    child
                )

        # ====================================================
        # list
        # ====================================================

        elif isinstance(
            value,
            list
        ):

            for child in value:

                walk(
                    child
                )

    walk(
        data
    )

    return results


# ============================================================
# 결과 1건 정규화
# ============================================================

def normalize_ai_search_item(
    item: dict,
    rank: int
):

    article_number = safe_int(
        item.get(
            "조문번호"
        )
    )

    sub_article_number = safe_int(
        item.get(
            "조문가지번호"
        )
    )

    return {

        "rank":
            str(rank),

        "law_name":
            normalize_text(
                item.get(
                    "법령명"
                )
                or
                item.get(
                    "법령명한글"
                )
            ),

        "law_type":
            normalize_text(
                item.get(
                    "법령종류명"
                )
                or
                item.get(
                    "법령구분명"
                )
            ),

        "ministry":
            normalize_text(
                item.get(
                    "소관부처명"
                )
            ),

        "law_id":
            normalize_text(
                item.get(
                    "법령ID"
                )
            ),

        "mst":
            normalize_text(
                item.get(
                    "법령일련번호"
                )
            ),

        "article_number":
            article_number,

        "sub_article_number":
            sub_article_number,

        "article_title":
            normalize_text(
                item.get(
                    "조문제목"
                )
            ),

        "article_text":
            normalize_text(
                item.get(
                    "조문내용"
                )
            ),

        "effective_date":
            normalize_text(
                item.get(
                    "시행일자"
                )
            ),

        "promulgation_date":
            normalize_text(
                item.get(
                    "공포일자"
                )
            ),

        "revision_type":
            normalize_text(
                item.get(
                    "제개정구분명"
                )
                or
                item.get(
                    "개정구분명"
                )
            ),

        "raw":
            item,
    }


# ============================================================
# 전체 결과 정규화
# ============================================================

def normalize_ai_search_results(
    data
):

    raw_items = extract_ai_search_list(
        data
    )

    results = []

    for index, item in enumerate(
        raw_items,
        start=1
    ):

        results.append(

            normalize_ai_search_item(

                item=item,

                rank=index
            )
        )

    return results