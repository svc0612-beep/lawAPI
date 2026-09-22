# ============================================================
# 법제처 판례 응답 Parser
#
# 역할
# - 판례 검색 결과 판별
# - 검색 응답에서 판례 목록 추출
# - 판례 검색 결과 정규화
# - 판례 상세조회 응답 정규화
# ============================================================

from services.evidence.precedent_utils import (
    normalize_text,
)


# ============================================================
# 1. 실제 판례 검색 결과인지 확인
# ============================================================

def is_precedent_item(
    item
):

    if not isinstance(
        item,
        dict
    ):

        return False

    has_case_name = (
        "사건명" in item
    )

    has_case_number = (
        "사건번호" in item
    )

    return (
        has_case_name
        and
        has_case_number
    )


# ============================================================
# 2. 검색 응답 전체에서 판례 결과 찾기
# ============================================================

def extract_precedent_list(
    data
):
    """
    응답 구조가 달라져도
    실제 판례 객체를 재귀적으로 찾는다.
    """

    results = []

    def walk(
        value
    ):

        if isinstance(
            value,
            dict
        ):

            if is_precedent_item(
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
# 3. 판례 검색 결과 1건 정규화
# ============================================================

def normalize_precedent_item(
    item: dict,
    rank: int
):

    return {

        "rank":
            rank,

        "case_name":
            normalize_text(
                item.get(
                    "사건명"
                )
            ),

        "case_number":
            normalize_text(
                item.get(
                    "사건번호"
                )
            ),

        "decision_date":
            normalize_text(
                item.get(
                    "선고일자"
                )
            ),

        "court_name":
            normalize_text(
                item.get(
                    "법원명"
                )
            ),

        "court_type":
            normalize_text(
                item.get(
                    "법원종류명"
                )
            ),

        "case_type":
            normalize_text(
                item.get(
                    "사건종류명"
                )
            ),

        "decision_type":
            normalize_text(
                item.get(
                    "판결유형"
                )
            ),

        "precedent_id":
            normalize_text(

                item.get(
                    "판례일련번호"
                )

                or

                item.get(
                    "판례정보일련번호"
                )
            ),

        "raw":
            item,
    }


# ============================================================
# 4. 판례 검색 목록 전체 정규화
# ============================================================

def normalize_precedent_list(
    data
):

    raw_items = extract_precedent_list(
        data
    )

    return [

        normalize_precedent_item(
            item=item,
            rank=index
        )

        for index, item in enumerate(
            raw_items,
            start=1
        )
    ]


# ============================================================
# 5. 판례 상세 객체 추출
# ============================================================

def extract_precedent_detail(
    data
):

    if not isinstance(
        data,
        dict
    ):

        return {}

    detail = data.get(
        "PrecService"
    )

    if isinstance(
        detail,
        dict
    ):

        return detail

    return {}


# ============================================================
# 6. 판례 상세조회 결과 정규화
#
# 실제 상세 API 주요 필드
# - 판시사항
# - 판결요지
# - 참조조문
# - 참조판례
# - 판례내용
# ============================================================

def normalize_precedent_detail(
    data
):

    detail = extract_precedent_detail(
        data
    )

    if not detail:

        return {

            "holding":
                "",

            "summary":
                "",

            "reasoning":
                "",

            "reference_articles":
                "",

            "reference_precedents":
                "",

            "full_text":
                "",

            "raw_detail":
                {},
        }

    holding = normalize_text(
        detail.get(
            "판시사항"
        )
    )

    summary = normalize_text(
        detail.get(
            "판결요지"
        )
    )

    reference_articles = normalize_text(
        detail.get(
            "참조조문"
        )
    )

    reference_precedents = normalize_text(
        detail.get(
            "참조판례"
        )
    )

    full_text = normalize_text(

        detail.get(
            "판례내용"
        )

        or

        detail.get(
            "판결내용"
        )

        or

        detail.get(
            "본문"
        )
    )

    # 판례 상세 API는 별도의 '이유' 필드를
    # 항상 제공하지 않으므로 판례내용을 reasoning으로도 활용한다.
    reasoning = full_text

    return {

        "holding":
            holding,

        "summary":
            summary,

        "reasoning":
            reasoning,

        "reference_articles":
            reference_articles,

        "reference_precedents":
            reference_precedents,

        "full_text":
            full_text,

        "raw_detail":
            detail,
    }
