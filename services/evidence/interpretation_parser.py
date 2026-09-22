# ============================================================
# 법제처 법령해석례 응답 Parser
#
# 역할
# - 법령해석례 검색 결과 판별
# - 검색 응답에서 해석례 목록 추출
# - 검색 결과 정규화
# - 법령해석례 상세조회 응답 정규화
# ============================================================

from services.evidence.interpretation_utils import (
    normalize_text,
)


# ============================================================
# 1. 실제 법령해석례 검색 결과인지 판별
# ============================================================

def is_interpretation_item(
    item
):

    if not isinstance(
        item,
        dict
    ):

        return False

    has_title = (
        "안건명" in item
        or
        "해석례명" in item
        or
        "제목" in item
    )

    has_identifier = (
        "안건번호" in item
        or
        "법령해석례일련번호" in item
        or
        "해석례일련번호" in item
    )

    return (
        has_title
        and
        has_identifier
    )


# ============================================================
# 2. 검색 응답 전체에서 실제 해석례 찾기
# ============================================================

def extract_interpretation_list(
    data
):
    """
    응답 구조가 달라져도
    실제 법령해석례 객체를 재귀적으로 찾는다.
    """

    results = []

    def walk(
        value
    ):

        if isinstance(
            value,
            dict
        ):

            if is_interpretation_item(
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
# 3. 법령해석례 검색 결과 1건 정규화
# ============================================================

def normalize_interpretation_item(
    item: dict,
    rank: int
):

    title = (

        item.get(
            "안건명"
        )

        or

        item.get(
            "해석례명"
        )

        or

        item.get(
            "제목"
        )
    )

    case_number = (

        item.get(
            "안건번호"
        )

        or

        item.get(
            "해석례번호"
        )
    )

    reply_date = (

        item.get(
            "회신일자"
        )

        or

        item.get(
            "해석일자"
        )
    )

    agency = (

        item.get(
            "기관명"
        )

        or

        item.get(
            "질의기관명"
        )

        or

        item.get(
            "회신기관명"
        )
    )

    interpretation_id = (

        item.get(
            "법령해석례일련번호"
        )

        or

        item.get(
            "해석례일련번호"
        )
    )

    return {

        "rank":
            rank,

        "title":
            normalize_text(
                title
            ),

        "case_number":
            normalize_text(
                case_number
            ),

        "reply_date":
            normalize_text(
                reply_date
            ),

        "agency":
            normalize_text(
                agency
            ),

        "interpretation_id":
            normalize_text(
                interpretation_id
            ),

        "raw":
            item,
    }


# ============================================================
# 4. 법령해석례 검색 목록 전체 정규화
# ============================================================

def normalize_interpretation_list(
    data
):

    raw_items = extract_interpretation_list(
        data
    )

    return [

        normalize_interpretation_item(
            item=item,
            rank=index
        )

        for index, item in enumerate(
            raw_items,
            start=1
        )
    ]


# ============================================================
# 5. 법령해석례 상세 객체 추출
# ============================================================

def extract_interpretation_detail(
    data
):

    if not isinstance(
        data,
        dict
    ):

        return {}

    detail = data.get(
        "ExpcService"
    )

    if isinstance(
        detail,
        dict
    ):

        return detail

    return {}


# ============================================================
# 6. 법령해석례 상세조회 결과 정규화
#
# 실제 상세 API 주요 필드
# - 질의요지
# - 회답
# - 이유
# - 안건명
# - 안건번호
# - 해석일자
# ============================================================

def normalize_interpretation_detail(
    data
):

    detail = extract_interpretation_detail(
        data
    )

    if not detail:

        return {

            "title":
                "",

            "case_number":
                "",

            "reply_date":
                "",

            "agency":
                "",

            "inquiry_summary":
                "",

            "answer_summary":
                "",

            "reasoning":
                "",

            "full_text":
                "",

            "raw_detail":
                {},
        }

    title = normalize_text(
        detail.get(
            "안건명"
        )
    )

    case_number = normalize_text(
        detail.get(
            "안건번호"
        )
    )

    reply_date = normalize_text(

        detail.get(
            "해석일자"
        )

        or

        detail.get(
            "회신일자"
        )
    )

    agency = normalize_text(

        detail.get(
            "해석기관명"
        )

        or

        detail.get(
            "기관명"
        )

        or

        detail.get(
            "질의기관명"
        )
    )

    inquiry_summary = normalize_text(
        detail.get(
            "질의요지"
        )
    )

    answer_summary = normalize_text(
        detail.get(
            "회답"
        )
    )

    reasoning = normalize_text(
        detail.get(
            "이유"
        )
    )

    full_text_parts = [

        value

        for value in (
            inquiry_summary,
            answer_summary,
            reasoning,
        )

        if value
    ]

    full_text = "\n\n".join(
        full_text_parts
    )

    return {

        "title":
            title,

        "case_number":
            case_number,

        "reply_date":
            reply_date,

        "agency":
            agency,

        "inquiry_summary":
            inquiry_summary,

        "answer_summary":
            answer_summary,

        "reasoning":
            reasoning,

        "full_text":
            full_text,

        "raw_detail":
            detail,
    }
