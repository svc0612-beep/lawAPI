# ============================================================
# 법령 검색 응답 Parser
#
# 역할
# - lawSearch.do 응답에서 실제 법령 목록 추출
# ============================================================


def extract_law_list(
    data: dict
):

    if not isinstance(
        data,
        dict
    ):
        return []

    law_search = data.get(
        "LawSearch",
        {}
    )

    if not isinstance(
        law_search,
        dict
    ):
        return []

    result = law_search.get(
        "law",
        []
    )

    # 검색 결과 1건
    if isinstance(
        result,
        dict
    ):

        return [
            result
        ]

    # 검색 결과 여러 건
    if isinstance(
        result,
        list
    ):

        return result

    return []