# ============================================================
# 범용 법령명 Resolver
#
# 역할:
#
# 사용자 법령 표현
#      ↓
# lawSearch
#      ↓
# 후보 점수 계산
#      ↓
# 안전한 자동 확정 판단
#      ↓
# 필요 시 aiSearch 보조
#      ↓
# 공식 법령 재검증
#      ↓
# resolved / ambiguous / not_found
#
# 특정 법령명 하드코딩 없음
# ============================================================

from typing import (
    Any,
    Dict,
    Optional,
)

from services.law.search import (
    search_law,
)

from services.law.ai_search import (
    search_related_laws,
)


# ============================================================
# 기존 외부 import 호환성을 위해 재노출
# ============================================================

from services.law.resolver_utils import (
    normalize_text,
    compact_text,
    normalize_law_name_for_matching,
    make_bigrams,
    bigram_similarity,
    calculate_single_match_features,
    calculate_match_features,
)

from services.law.resolver_scoring import (
    score_single_name,
    score_law_candidate,
)

from services.law.resolver_candidates import (
    build_search_candidate,
    build_ai_candidate,
    deduplicate_candidates,
)

from services.law.resolver_verifier import (
    verify_official_law,
)

from services.law.resolver_decision import (
    can_auto_resolve,
)


# ============================================================
# 공통 not_found 결과
# ============================================================

def build_not_found_result() -> Dict[str, Any]:

    return {

        "status":
            "not_found",

        "resolved_law_name":
            "",

        "confidence":
            0,

        "law_info":
            None,

        "candidates":
            [],
    }


# ============================================================
# resolved 결과
# ============================================================

def build_resolved_result(
    candidate: Dict[str, Any],
    candidates,
    max_candidates: int
) -> Dict[str, Any]:

    law_name = candidate.get(
        "law_name",
        ""
    )

    law_info = verify_official_law(
        law_name
    )

    return {

        "status":
            "resolved",

        "resolved_law_name":
            law_name,

        "confidence":
            candidate.get(
                "resolver_score",
                0
            ),

        "law_info":
            law_info,

        "candidates":
            candidates[
                :max_candidates
            ],
    }


# ============================================================
# top / second
# ============================================================

def get_top_candidates(
    candidates
):

    top = candidates[0]

    second = (
        candidates[1]
        if len(candidates) > 1
        else None
    )

    return (
        top,
        second
    )


# ============================================================
# aiSearch 후보 공식정보 보강
# ============================================================

def enrich_candidates_with_official_info(
    candidates,
    user_expression: str
):

    enriched_candidates = []

    for candidate in candidates:

        law_name = candidate.get(
            "law_name",
            ""
        )

        official = verify_official_law(
            law_name
        )

        if official:

            enriched_candidate = (
                build_search_candidate(

                    item=official,

                    user_expression=(
                        user_expression
                    ),

                    rank=candidate.get(
                        "original_rank",
                        999
                    )
                )
            )

            enriched_candidates.append(
                enriched_candidate
            )

        else:

            enriched_candidates.append(
                candidate
            )

    return deduplicate_candidates(
        enriched_candidates
    )


# ============================================================
# 최종 Resolver
# ============================================================

def resolve_law_name(
    user_expression: str,
    search_query: Optional[str] = None,
    max_candidates: int = 5
) -> Dict[str, Any]:

    user_expression = normalize_text(
        user_expression
    )

    search_query = normalize_text(
        search_query
        or
        user_expression
    )

    if not user_expression:

        return build_not_found_result()

    candidates = []

    # ========================================================
    # 1차
    # 일반 법령검색
    #
    # 공식 법령명 + 공식 약칭 사용
    # ========================================================

    search_results = search_law(

        query=user_expression,

        display=20
    )

    for rank, item in enumerate(
        search_results,
        start=1
    ):

        candidates.append(

            build_search_candidate(

                item=item,

                user_expression=(
                    user_expression
                ),

                rank=rank
            )
        )

    candidates = deduplicate_candidates(
        candidates
    )

    # ========================================================
    # lawSearch 결과만으로 안전하게 확정 가능한가?
    # ========================================================

    if candidates:

        top, second = get_top_candidates(
            candidates
        )

        if can_auto_resolve(
            top,
            second
        ):

            return build_resolved_result(

                candidate=top,

                candidates=candidates,

                max_candidates=(
                    max_candidates
                )
            )

    # ========================================================
    # 2차
    # aiSearch 보조
    # ========================================================

    ai_results = search_related_laws(

        query=search_query,

        display=10
    )

    for rank, item in enumerate(
        ai_results,
        start=1
    ):

        candidate = build_ai_candidate(

            item=item,

            user_expression=(
                user_expression
            ),

            rank=rank
        )

        if candidate.get(
            "law_name"
        ):

            candidates.append(
                candidate
            )

    candidates = deduplicate_candidates(
        candidates
    )

    if not candidates:

        return build_not_found_result()

    # ========================================================
    # aiSearch 후보를 공식 lawSearch로 재확인
    #
    # 목적:
    # - 공식 법령명 확인
    # - 공식 약칭 정보 보강
    # ========================================================

    candidates = (
        enrich_candidates_with_official_info(

            candidates=candidates,

            user_expression=(
                user_expression
            )
        )
    )

    if not candidates:

        return build_not_found_result()

    # ========================================================
    # 최종 자동 확정 판단
    # ========================================================

    top, second = get_top_candidates(
        candidates
    )

    if can_auto_resolve(
        top,
        second
    ):

        return build_resolved_result(

            candidate=top,

            candidates=candidates,

            max_candidates=max_candidates
        )

    # ========================================================
    # 하나의 공식 법령으로 안전하게 확정할 수 없음
    # ========================================================

    return {

        "status":
            "ambiguous",

        "resolved_law_name":
            "",

        "confidence":
            top.get(
                "resolver_score",
                0
            ),

        "law_info":
            None,

        "candidates":
            candidates[
                :max_candidates
            ],
    }