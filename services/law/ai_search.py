# ============================================================
# 법제처 지능형 법령검색 서비스
#
# 역할
#
# 검색어
#   ↓
# aiSearch API / Cache
#   ↓
# 실제 조문 탐색
#   ↓
# 표준 구조 정규화
#
# 관련도 재정렬은 reranker.py 담당
# ============================================================


# ============================================================
# 기존 외부 import 호환성을 위한 재노출
# ============================================================

from services.law.ai_search_utils import (
    normalize_text,
    safe_int,
)

from services.law.ai_search_parser import (
    is_ai_search_item,
    extract_ai_search_list,
    normalize_ai_search_item,
    normalize_ai_search_results,
)

from services.law.ai_search_fetcher import (
    request_ai_search,
)


# ============================================================
# aiSearch 실행
# ============================================================

def search_related_laws(
    query: str,
    display: int = 10
):

    query = (
        query
        or ""
    ).strip()

    if not query:

        return []

    data = request_ai_search(

        query=query,

        display=display
    )

    if data is None:

        return []

    return normalize_ai_search_results(
        data
    )


# ============================================================
# 단독 테스트
# ============================================================

if __name__ == "__main__":

    test_query = (
        "장애인 취업"
    )

    print()

    print(
        "=" * 70
    )

    print(
        "법제처 aiSearch 서비스 테스트"
    )

    print(
        "=" * 70
    )

    print(
        "검색어:",
        test_query
    )

    try:

        results = search_related_laws(

            query=test_query,

            display=10
        )

        print()

        print(
            "검색 결과:",
            len(results),
            "건"
        )

        for item in results:

            print()

            article_number = (
                item[
                    "article_number"
                ]
            )

            sub_number = (
                item[
                    "sub_article_number"
                ]
            )

            if sub_number:

                article_label = (
                    f"제{article_number}조의{sub_number}"
                )

            else:

                article_label = (
                    f"제{article_number}조"
                )

            print(
                f"[{item['rank']}] "
                f"{item['law_name']}"
            )

            print(
                "조문:",
                article_label
            )

            print(
                "제목:",
                item[
                    "article_title"
                ]
            )

            print(
                "소관부처:",
                item[
                    "ministry"
                ]
            )

            article_text = (
                item[
                    "article_text"
                ]
            )

            print(
                "내용:",
                article_text[:200]
            )

    except Exception as e:

        print()

        print(
            "오류:",
            e
        )