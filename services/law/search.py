# ============================================================
# 법령 검색 서비스
#
# 역할
#
# 검색어
#   ↓
# lawSearch API / Cache
#   ↓
# 실제 법령 목록 추출
#   ↓
# 필요 시 정확 법령 선택
#
# 조문 조회는 article.py에서 담당
# ============================================================


# ============================================================
# 기존 import 호환성을 위해 재노출
# ============================================================

from services.law.search_parser import (
    extract_law_list,
)

from services.law.search_fetcher import (
    request_law_search,
)

from services.law.search_selector import (
    select_exact_law,
)


# ============================================================
# 일반 법령 검색
# ============================================================

def search_law(
    query: str,
    display: int = 10
):

    query = (
        query
        or ""
    ).strip()

    if not query:
        return []

    data = request_law_search(

        query=query,

        display=display
    )

    if data is None:
        return []

    return extract_law_list(
        data
    )


# ============================================================
# 정확한 법령 찾기
# ============================================================

def find_exact_law(
    law_name: str
):

    law_name = (
        law_name
        or ""
    ).strip()

    if not law_name:
        return None

    laws = search_law(

        query=law_name,

        display=20
    )

    return select_exact_law(

        law_name=law_name,

        laws=laws
    )


# ============================================================
# 단독 실행 테스트
# ============================================================

if __name__ == "__main__":

    test_query = (
        "대한민국헌법"
    )

    print()

    print(
        "=" * 70
    )

    print(
        "법령 검색 서비스 테스트"
    )

    print(
        "=" * 70
    )

    print(
        "검색어:",
        test_query
    )

    try:

        result = find_exact_law(
            test_query
        )

        if result is None:

            print()

            print(
                "검색 결과 없음"
            )

        else:

            print()

            print(
                "법령명:",
                result.get(
                    "법령명한글"
                )
            )

            print(
                "법령 ID:",
                result.get(
                    "법령ID"
                )
            )

            print(
                "MST:",
                result.get(
                    "법령일련번호"
                )
            )

            print(
                "법령 종류:",
                result.get(
                    "법령구분명"
                )
            )

            print(
                "소관부처:",
                result.get(
                    "소관부처명"
                )
            )

            print(
                "시행일자:",
                result.get(
                    "시행일자"
                )
            )

            print(
                "공포일자:",
                result.get(
                    "공포일자"
                )
            )

    except Exception as e:

        print()

        print(
            "오류:",
            e
        )