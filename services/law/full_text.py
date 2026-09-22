# ============================================================
# 법령 전체 원문 조회 서비스
#
# 이 파일의 역할:
#
# 1. 법령 선택
# 2. MST 확보
# 3. 전체 원문 API 호출
# 4. 파서 실행
# 5. 결과 반환
#
# 세부 선택/HTTP/파싱 로직은 별도 모듈에 분리한다.
# ============================================================

from typing import (
    Any,
    Dict,
)

from services.law.full_text_utils import (
    normalize_text,
    compact_text,
    safe_int,
    ensure_list,
)

from services.law.full_text_selector import (
    select_best_law,
    find_law_for_full_text,
)

from services.law.full_text_fetcher import (
    request_full_law_json,
)

from services.law.full_article_parser import (
    parse_mok_items,
    parse_ho_items,
    parse_paragraphs,
    build_mok_text,
    build_ho_text,
    build_paragraph_text,
    parse_article_node,
)

from services.law.full_text_parser import (
    get_law_root,
    get_basic_info,
    parse_articles,
    deduplicate_articles,
    extract_metadata,
    parse_full_law,
)


# ============================================================
# 최종 범용 법령 전체조회
# ============================================================

def get_full_law(
    law_name: str
) -> Dict[str, Any]:

    law_name = normalize_text(
        law_name
    )

    # ========================================================
    # 법령명 검증
    # ========================================================

    if not law_name:

        return {

            "status":
                "error",

            "message":
                "조회할 법령명이 없습니다.",

            "law_name":
                "",

            "articles":
                [],
        }

    # ========================================================
    # 1. 정확 법령 검색
    # ========================================================

    selected_law = find_law_for_full_text(
        law_name
    )

    if not selected_law:

        return {

            "status":
                "not_found",

            "message":
                "정확히 일치하는 법령을 찾지 못했습니다.",

            "requested_law_name":
                law_name,

            "law_name":
                "",

            "articles":
                [],
        }

    # ========================================================
    # 2. MST
    # ========================================================

    mst = normalize_text(
        selected_law.get(
            "법령일련번호"
        )
    )

    if not mst:

        return {

            "status":
                "error",

            "message":
                "법령일련번호(MST)를 확인할 수 없습니다.",

            "requested_law_name":
                law_name,

            "articles":
                [],
        }

    # ========================================================
    # 3. 전체 법령 API
    # ========================================================

    raw_data = request_full_law_json(
        mst=mst,
        effective_date=normalize_text(selected_law.get("시행일자"))
    )

    # ========================================================
    # 4. 전체 법령 파싱
    # ========================================================

    parsed = parse_full_law(
        raw_data
    )

    # ========================================================
    # 5. 상세 API에서 비어 있는 메타데이터는
    #    법령 검색 결과로 보완
    # ========================================================

    fallback_metadata = {

        "law_name":
            "법령명한글",

        "law_type":
            "법령구분명",

        "ministry":
            "소관부처명",

        "law_id":
            "법령ID",

        "mst":
            "법령일련번호",

        "effective_date":
            "시행일자",

        "promulgation_date":
            "공포일자",

        "revision_type":
            "제개정구분명",
    }

    for (
        output_key,
        search_key
    ) in fallback_metadata.items():

        if not parsed.get(
            output_key
        ):

            parsed[
                output_key
            ] = normalize_text(
                selected_law.get(
                    search_key
                )
            )

    parsed[
        "status"
    ] = "success"

    parsed[
        "requested_law_name"
    ] = law_name

    return parsed


# ============================================================
# 간단 테스트
# ============================================================

def print_test_result(
    law_name: str
):

    result = get_full_law(
        law_name
    )

    print(
        "=" * 80
    )

    print(
        "법령 전체조회 테스트"
    )

    print(
        "=" * 80
    )

    print(
        "요청 법령:",
        law_name
    )

    print(
        "상태:",
        result.get(
            "status"
        )
    )

    print(
        "법령명:",
        result.get(
            "law_name"
        )
    )

    print(
        "MST:",
        result.get(
            "mst"
        )
    )

    print(
        "시행일자:",
        result.get(
            "effective_date"
        )
    )

    print(
        "실제 조문수:",
        result.get(
            "article_count",
            0
        )
    )

    print(
        "구조정보 수:",
        len(
            result.get(
                "structure",
                []
            )
        )
    )

    articles = result.get(
        "articles",
        []
    )

    for article in articles[:5]:

        article_number = article.get(
            "article_number"
        )

        sub_number = (
            article.get(
                "sub_article_number",
                0
            )
            or 0
        )

        if sub_number:

            label = (
                f"제{article_number}조의"
                f"{sub_number}"
            )

        else:

            label = (
                f"제{article_number}조"
            )

        print()

        print(
            "-" * 80
        )

        print(
            label,
            article.get(
                "article_title",
                ""
            )
        )

        headers = article.get(
            "section_headers",
            []
        )

        if headers:

            print(
                "구조:",
                " > ".join(
                    headers
                )
            )

        print(
            article.get(
                "full_text",
                ""
            )[:1200]
        )


if __name__ == "__main__":

    print_test_result(
        "장애인복지법"
    )
