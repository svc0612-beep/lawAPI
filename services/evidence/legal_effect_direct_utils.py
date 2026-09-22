# ============================================================
# Legal Effect Direct Utils
#
# Direct 근거 탐색에서 사용하는 seed map 생성.
#
# Query Expansion / Reranker가 이미 계산한 검색 품질 정보를
# Direct Basis 단계에서 잃지 않도록 함께 보존한다.
#
# 중요:
# - 특정 법률명 하드코딩 없음
# - 특정 조문번호 하드코딩 없음
# - 분야별 synonym dictionary 없음
# ============================================================

from typing import (
    Any,
    Dict,
    List,
)

from services.evidence.legal_effect_utils import (
    clean_text,
    normalize_law_name,
    safe_int,
    make_article_key,
)


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:

    try:

        return float(
            value
        )

    except (
        TypeError,
        ValueError,
    ):

        return default


def clean_string_list(
    value: Any
) -> List[str]:

    if not isinstance(
        value,
        list
    ):

        return []

    results = []

    for item in value:

        text = clean_text(
            item
        )

        if (
            text
            and
            text not in results
        ):

            results.append(
                text
            )

    return results


def build_seed_article_map(
    seed_laws: List[
        Dict[str, Any]
    ],
    primary_law_name: str
) -> Dict[
    str,
    Dict[str, Any]
]:

    primary_name = normalize_law_name(
        primary_law_name
    )

    results = {}

    if not isinstance(
        seed_laws,
        list
    ):

        return results

    for index, item in enumerate(
        seed_laws
    ):

        if not isinstance(
            item,
            dict
        ):

            continue

        item_law_name = normalize_law_name(
            item.get(
                "law_name"
            )
        )

        if (
            primary_name
            and
            item_law_name != primary_name
        ):

            continue

        key = make_article_key(

            item.get(
                "article_number"
            ),

            item.get(
                "sub_article_number",
                0
            ),
        )

        if not key:

            continue

        final_rank = (
            item.get(
                "final_rank"
            )
            or
            item.get(
                "original_rank"
            )
            or
            (
                index + 1
            )
        )

        original_rank = (
            item.get(
                "original_rank"
            )
            or
            final_rank
        )

        results[
            key
        ] = {

            # 기존 호환 필드
            "rank":
                safe_int(
                    final_rank,
                    index + 1
                ),

            "title":
                clean_text(
                    item.get(
                        "article_title"
                    )
                ),

            # 검색 단계 품질 정보
            "final_rank":
                safe_int(
                    final_rank,
                    index + 1
                ),

            "original_rank":
                safe_int(
                    original_rank,
                    index + 1
                ),

            "relevance_score":
                safe_float(
                    item.get(
                        "relevance_score"
                    ),
                    0.0,
                ),

            "query_coverage":
                safe_float(
                    item.get(
                        "query_coverage"
                    ),
                    0.0,
                ),

            "matched_tokens":
                clean_string_list(
                    item.get(
                        "matched_tokens"
                    )
                ),

            # Query Expansion에서 실제 채택된 의미 보조어.
            # 검색 보조 정보이며 법률 사실로 사용하지 않는다.
            "query_expansion_terms":
                clean_string_list(
                    item.get(
                        "query_expansion_terms"
                    )
                ),
        }

    return results
