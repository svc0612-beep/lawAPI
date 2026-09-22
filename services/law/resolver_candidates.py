# ============================================================
# Resolver 후보 생성 / 중복 제거
# ============================================================

from typing import (
    Any,
    Dict,
    List,
)

from services.law.resolver_utils import (
    normalize_text,
    calculate_match_features,
)

from services.law.resolver_scoring import (
    score_law_candidate,
)


# ============================================================
# lawSearch 후보
# ============================================================

def build_search_candidate(
    item: Dict[str, Any],
    user_expression: str,
    rank: int
) -> Dict[str, Any]:

    law_name = normalize_text(
        item.get(
            "법령명한글"
        )
    )

    abbreviation = normalize_text(
        item.get(
            "법령약칭명"
        )
    )

    features = calculate_match_features(

        user_expression=user_expression,

        law_name=law_name,

        abbreviation=abbreviation
    )

    score = score_law_candidate(

        user_expression=user_expression,

        law_name=law_name,

        abbreviation=abbreviation,

        original_rank=rank
    )

    return {

        "law_name":
            law_name,

        "abbreviation":
            abbreviation,

        "law_id":
            normalize_text(
                item.get(
                    "법령ID"
                )
            ),

        "mst":
            normalize_text(
                item.get(
                    "법령일련번호"
                )
            ),

        "law_type":
            normalize_text(
                item.get(
                    "법령구분명"
                )
            ),

        "ministry":
            normalize_text(
                item.get(
                    "소관부처명"
                )
            ),

        "effective_date":
            normalize_text(
                item.get(
                    "시행일자"
                )
            ),

        "promulgation_date":
            normalize_text(
                item.get(
                    "공포일자"
                )
            ),

        "revision_type":
            normalize_text(
                item.get(
                    "제개정구분명"
                )
            ),

        "original_rank":
            rank,

        "resolver_score":
            score,

        "source":
            "lawSearch",

        "match_features":
            features,

        "raw":
            item,
    }


# ============================================================
# aiSearch 후보
# ============================================================

def build_ai_candidate(
    item: Dict[str, Any],
    user_expression: str,
    rank: int
) -> Dict[str, Any]:

    law_name = normalize_text(
        item.get(
            "law_name"
        )
    )

    features = calculate_match_features(

        user_expression=user_expression,

        law_name=law_name,

        abbreviation=""
    )

    score = score_law_candidate(

        user_expression=user_expression,

        law_name=law_name,

        abbreviation="",

        original_rank=rank
    )

    return {

        "law_name":
            law_name,

        "abbreviation":
            "",

        "law_id":
            normalize_text(
                item.get(
                    "law_id"
                )
            ),

        "mst":
            normalize_text(
                item.get(
                    "mst"
                )
            ),

        "law_type":
            normalize_text(
                item.get(
                    "law_type"
                )
            ),

        "ministry":
            normalize_text(
                item.get(
                    "ministry"
                )
            ),

        "effective_date":
            normalize_text(
                item.get(
                    "effective_date"
                )
            ),

        "promulgation_date":
            normalize_text(
                item.get(
                    "promulgation_date"
                )
            ),

        "revision_type":
            normalize_text(
                item.get(
                    "revision_type"
                )
            ),

        "original_rank":
            rank,

        "resolver_score":
            score,

        "source":
            "aiSearch",

        "match_features":
            features,

        "raw":
            item,
    }


# ============================================================
# 후보 중복 제거
# ============================================================

def deduplicate_candidates(
    candidates: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    best_by_name = {}

    for candidate in candidates:

        law_name = normalize_text(
            candidate.get(
                "law_name"
            )
        )

        if not law_name:
            continue

        existing = best_by_name.get(
            law_name
        )

        if (
            existing is None
            or
            candidate.get(
                "resolver_score",
                0
            )
            >
            existing.get(
                "resolver_score",
                0
            )
        ):

            best_by_name[
                law_name
            ] = candidate

    final_candidates = list(
        best_by_name.values()
    )

    final_candidates.sort(

        key=lambda item: (

            -item.get(
                "resolver_score",
                0
            ),

            item.get(
                "original_rank",
                999
            )
        )
    )

    return final_candidates