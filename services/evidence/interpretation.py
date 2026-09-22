# ============================================================
# 법제처 법령해석례 서비스
#
# 역할
# 1. 법제처 법령해석례 검색 target=expc
# 2. 검색 결과 구조 정규화
# 3. 상위 해석례 상세조회
# 4. 검색 결과 + 상세내용 병합
# 5. 공통 SQLite 캐시 사용
# ============================================================

import os
import sys


# ============================================================
# 1. 프로젝트 루트 경로 등록
# ============================================================

CURRENT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        CURRENT_DIR
    )
)

if PROJECT_ROOT not in sys.path:

    sys.path.append(
        PROJECT_ROOT
    )


# ============================================================
# 2. 공통 유틸
# ============================================================

from services.evidence.interpretation_utils import (
    normalize_text,
)


# ============================================================
# 3. Parser
# ============================================================

from services.evidence.interpretation_parser import (
    is_interpretation_item,
    extract_interpretation_list,
    normalize_interpretation_item,
    normalize_interpretation_list,
    extract_interpretation_detail,
    normalize_interpretation_detail,
)


# ============================================================
# 4. Fetcher
# ============================================================

from services.evidence.interpretation_fetcher import (
    fetch_interpretation_search_data,
    fetch_interpretation_detail_data,
)


# ============================================================
# 5. 법령해석례 검색 + 상세내용 병합
# ============================================================

def search_interpretations(
    query: str,
    display: int = 5,
    detail_limit: int = 3
):

    query = (
        query
        or ""
    ).strip()

    if not query:

        return []

    # ========================================================
    # A. 검색
    # ========================================================

    data = (
        fetch_interpretation_search_data(
            query=query,
            display=display
        )
    )

    if data is None:

        return []

    results = (
        normalize_interpretation_list(
            data
        )
    )

    if not results:

        return []

    # ========================================================
    # B. 상세조회 개수 제한
    # ========================================================

    try:

        detail_limit = int(
            detail_limit
        )

    except (
        TypeError,
        ValueError,
    ):

        detail_limit = 3

    detail_limit = max(
        0,
        min(
            detail_limit,
            len(
                results
            )
        )
    )

    # ========================================================
    # C. 상위 결과 상세 병합
    # ========================================================

    for index, item in enumerate(
        results
    ):

        item.setdefault(
            "inquiry_summary",
            ""
        )

        item.setdefault(
            "answer_summary",
            ""
        )

        item.setdefault(
            "reasoning",
            ""
        )

        item.setdefault(
            "full_text",
            ""
        )

        item.setdefault(
            "raw_detail",
            {}
        )

        if index >= detail_limit:

            continue

        interpretation_id = normalize_text(
            item.get(
                "interpretation_id"
            )
        )

        if not interpretation_id:

            continue

        try:

            detail_data = (
                fetch_interpretation_detail_data(
                    interpretation_id
                )
            )

            detail = (
                normalize_interpretation_detail(
                    detail_data
                )
            )

        except Exception:

            # 상세조회 1건 실패가
            # 전체 검색 결과 실패로 이어지지 않게 한다.
            continue

        if not isinstance(
            detail,
            dict
        ):

            continue

        # 상세정보가 검색 목록보다 더 정확하면 갱신한다.
        for key in (
            "title",
            "case_number",
            "reply_date",
            "agency",
            "inquiry_summary",
            "answer_summary",
            "reasoning",
            "full_text",
            "raw_detail",
        ):

            value = detail.get(
                key
            )

            if value not in (
                None,
                "",
                {},
                [],
            ):

                item[
                    key
                ] = value

    return results


# ============================================================
# 6. 기존 공개 API 반환
# ============================================================

__all__ = [

    "normalize_text",

    "is_interpretation_item",

    "extract_interpretation_list",

    "normalize_interpretation_item",

    "normalize_interpretation_list",

    "extract_interpretation_detail",

    "normalize_interpretation_detail",

    "fetch_interpretation_search_data",

    "fetch_interpretation_detail_data",

    "search_interpretations",
]


# ============================================================
# 7. 단독 실행 테스트
# ============================================================

if __name__ == "__main__":

    test_query = (
        "음주운전"
    )

    print()

    print(
        "=" * 70
    )

    print(
        "법령해석례 검색 + 상세조회 테스트"
    )

    print(
        "=" * 70
    )

    print(
        "검색어:",
        test_query
    )

    try:

        results = search_interpretations(
            query=test_query,
            display=5,
            detail_limit=3
        )

        print()

        print(
            "검색 결과:",
            len(
                results
            ),
            "건"
        )

        for item in results:

            print()

            print(
                f"[{item['rank']}] "
                f"{item['title']}"
            )

            print(
                "안건번호:",
                item[
                    "case_number"
                ]
            )

            print(
                "회신/해석일자:",
                item[
                    "reply_date"
                ]
            )

            print(
                "기관:",
                item[
                    "agency"
                ]
            )

            print(
                "해석례 ID:",
                item[
                    "interpretation_id"
                ]
            )

            print(
                "질의요지 길이:",
                len(
                    item.get(
                        "inquiry_summary",
                        ""
                    )
                )
            )

            print(
                "회답 길이:",
                len(
                    item.get(
                        "answer_summary",
                        ""
                    )
                )
            )

            print(
                "이유 길이:",
                len(
                    item.get(
                        "reasoning",
                        ""
                    )
                )
            )

    except Exception as e:

        print()

        print(
            "오류:",
            e
        )
