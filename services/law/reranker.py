# ============================================================
# 범용 법령 검색 결과 Reranker
#
# aiSearch 후보
#   -> 문자 기반 점수 계산
#   -> 관련성 필터
#   -> score + coverage + aiSearch 원본 순위 정렬
#
# 특정 법률 분야 하드코딩 없음
# LLM 사용 없음
# 외부 API 추가 호출 없음
# ============================================================


# 기존 외부 import 호환성을 위해 재노출
from services.law.reranker_utils import (
    normalize_text,
    compact_text,
    partial_match_score,
)

from services.law.reranker_tokens import (
    STOP_WORDS,
    tokenize_query,
)

from services.law.reranker_scoring import (
    score_token,
    score_law_result,
)

from services.law.reranker_rules import (
    is_relevant,
)


# ============================================================
# 최종 Reranking
# ============================================================

def rerank_law_results(
    query: str,
    results: list,
    top_k: int = 5,
    fallback_mode: bool = False
):

    if not results:
        return []

    scored_results = []

    for item in results:

        if not isinstance(
            item,
            dict
        ):

            continue

        scoring = score_law_result(

            query=query,

            item=item,

            fallback_mode=fallback_mode
        )

        if not is_relevant(

            scoring=scoring,

            fallback_mode=fallback_mode
        ):

            continue

        enriched = dict(
            item
        )

        enriched[
            "relevance_score"
        ] = scoring[
            "score"
        ]

        enriched[
            "query_coverage"
        ] = scoring[
            "coverage"
        ]

        enriched[
            "matched_tokens"
        ] = scoring[
            "matched_tokens"
        ]

        enriched[
            "original_rank"
        ] = scoring[
            "original_rank"
        ]

        scored_results.append(
            enriched
        )

    # ========================================================
    # 정렬
    #
    # 1. relevance score
    # 2. query coverage
    # 3. aiSearch 원본 순위
    # ========================================================

    scored_results.sort(

        key=lambda item: (

            -item.get(
                "relevance_score",
                0
            ),

            -item.get(
                "query_coverage",
                0
            ),

            item.get(
                "original_rank",
                999
            ),
        )
    )

    final_results = scored_results[
        :top_k
    ]

    for index, item in enumerate(
        final_results,
        start=1
    ):

        item[
            "final_rank"
        ] = index

    return final_results


# ============================================================
# 수동 테스트
# ============================================================

def run_test(
    query: str,
    fallback_mode: bool = False
):

    from services.law.ai_search import (
        search_related_laws,
    )

    print()
    print("=" * 80)
    print("범용 Reranker 테스트")
    print("=" * 80)
    print("검색어:", query)
    print("fallback_mode:", fallback_mode)
    print(
        "검색 토큰:",
        tokenize_query(
            query
        )
    )

    raw_results = search_related_laws(
        query=query,
        display=10
    )

    print(
        "원본 결과:",
        len(
            raw_results
        ),
        "건"
    )

    final_results = rerank_law_results(

        query=query,

        results=raw_results,

        top_k=5,

        fallback_mode=fallback_mode
    )

    print(
        "최종 결과:",
        len(
            final_results
        ),
        "건"
    )

    for item in final_results:

        print()

        article_number = item.get(
            "article_number"
        )

        sub_article_number = (
            item.get(
                "sub_article_number",
                0
            )
            or 0
        )

        if article_number is None:

            article_label = ""

        elif sub_article_number:

            article_label = (
                f"제{article_number}조의"
                f"{sub_article_number}"
            )

        else:

            article_label = (
                f"제{article_number}조"
            )

        print(
            f"[{item.get('final_rank')}] "
            f"{item.get('law_name')} "
            f"{article_label}"
        )

        print(
            "제목:",
            item.get(
                "article_title"
            )
        )

        print(
            "점수:",
            item.get(
                "relevance_score"
            )
        )

        print(
            "coverage:",
            item.get(
                "query_coverage"
            )
        )

        print(
            "원본 순위:",
            item.get(
                "original_rank"
            )
        )

        print(
            "일치 토큰:",
            item.get(
                "matched_tokens"
            )
        )


if __name__ == "__main__":

    run_test(
        "개인정보를 동의 없이 수집하면 어떻게 돼?",
        fallback_mode=False
    )
