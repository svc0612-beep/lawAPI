# ============================================================
# Legal Effect Direct Select
#
# Direct Basis 후보 생성 및 최종 Anchor 선택.
#
# 핵심 원칙
# - 정확한 제목 문자열 일치만으로 낮은 점수 후보를 강제로 우선하지 않는다.
# - score_direct_article()이 계산한 전체 연결 점수를 우선한다.
# - title_action_match + seed는 보조 우대만 하되,
#   전체 최고점과 충분히 가까운 경우에만 우선 후보가 될 수 있다.
# - 특정 법률명/조문번호는 사용하지 않는다.
# ============================================================

from typing import (
    Any,
    Dict,
    List,
)

from services.evidence.legal_effect_constants import (
    DIRECT_BASIS_LIMIT,
)

from services.evidence.legal_effect_direct_score import (
    score_direct_article,
)


# ============================================================
# 1. Direct Basis 후보 생성
# ============================================================

def find_direct_basis_articles(
    articles: List[
        Dict[str, Any]
    ],
    question: str,
    seed_map: Dict[
        str,
        Dict[str, Any]
    ]
) -> List[
    Dict[str, Any]
]:

    scored = []

    for index, article in enumerate(
        articles
    ):

        if not isinstance(
            article,
            dict
        ):

            continue

        score, details = score_direct_article(

            article=article,

            question=question,

            seed_map=seed_map,
        )

        if score <= 0:

            continue

        scored.append(
            (
                score,
                index,
                article,
                details,
            )
        )

    scored.sort(

        key=lambda item: (
            -item[0],
            item[1],
        )
    )

    results = []

    for (
        score,
        _,
        article,
        details
    ) in scored[
        :DIRECT_BASIS_LIMIT
    ]:

        roles = list(
            dict.fromkeys(

                details.get(
                    "title_roles",
                    []
                )
                +
                details.get(
                    "normative_roles",
                    []
                )
            )
        )

        results.append(
            {
                "article":
                    article,

                "score":
                    score,

                "roles":
                    roles,

                "seed":
                    details.get(
                        "seed",
                        False
                    ),

                "action_token":
                    details.get(
                        "action_token",
                        ""
                    ),

                "object_tokens":
                    details.get(
                        "object_tokens",
                        []
                    ),

                "action_match":
                    details.get(
                        "action_match",
                        False
                    ),

                "title_action_match":
                    details.get(
                        "title_action_match",
                        False
                    ),

                "body_action_match":
                    details.get(
                        "body_action_match",
                        False
                    ),

                "object_match_count":
                    details.get(
                        "object_match_count",
                        0
                    ),

                "combined_match":
                    details.get(
                        "combined_match",
                        False
                    ),

                "action_core_match":
                    details.get(
                        "action_core_match",
                        False
                    ),

                "title_action_core_match":
                    details.get(
                        "title_action_core_match",
                        False
                    ),

                "body_action_core_match":
                    details.get(
                        "body_action_core_match",
                        False
                    ),

                "cross_reference_scope":
                    details.get(
                        "cross_reference_scope",
                        False
                    ),

                "broad_subject_signal":
                    details.get(
                        "broad_subject_signal",
                        False
                    ),

                "connection_level":
                    0,
            }
        )

    return results


# ============================================================
# 2. 최종 Direct Anchor 선택
# ============================================================

def select_direct_anchors(
    direct_basis: List[
        Dict[str, Any]
    ]
) -> List[
    Dict[str, Any]
]:

    if not direct_basis:

        return []

    candidates = [

        item

        for item in direct_basis

        if float(
            item.get(
                "score",
                0
            )
            or 0
        )
        > 0
    ]

    if not candidates:

        return []

    # ========================================================
    # A. 전체 최고점을 먼저 구한다.
    #
    # 이전 로직은 title_action_match가 존재하면
    # 그 후보군만 남겨 버렸기 때문에,
    # 실제 본문상 더 직접적인 조문이 점수가 높아도
    # 제목에 질문 문자열이 들어간 보조 규정이 선택될 수 있었다.
    # ========================================================

    candidates.sort(

        key=lambda item: (
            -float(
                item.get(
                    "score",
                    0
                )
                or 0
            )
        )
    )

    global_top_score = float(
        candidates[
            0
        ].get(
            "score",
            0
        )
        or 0
    )

    if global_top_score <= 0:

        return []

    # ========================================================
    # B. title_action_match + seed는 "보조 우대"로만 사용한다.
    #
    # 전체 최고점의 95% 이상일 때만 preferred 후보가 될 수 있다.
    # 즉 exact title match라는 이유만으로
    # 훨씬 낮은 점수 후보가 최고점을 덮어쓰지 못한다.
    # ========================================================

    strong_title_seed = [

        item

        for item in candidates

        if bool(
            item.get(
                "title_action_match"
            )
        )
        and
        bool(
            item.get(
                "seed"
            )
        )
        and
        float(
            item.get(
                "score",
                0
            )
            or 0
        )
        >= (
            global_top_score
            *
            0.95
        )
    ]

    # ========================================================
    # C. seed가 없어도 exact title match가
    # 전체 최고점과 거의 같은 수준이면 우대 가능.
    # ========================================================

    strong_title = [

        item

        for item in candidates

        if bool(
            item.get(
                "title_action_match"
            )
        )
        and
        float(
            item.get(
                "score",
                0
            )
            or 0
        )
        >= (
            global_top_score
            *
            0.95
        )
    ]

    # ========================================================
    # D. 우대 후보가 없으면 전체 점수 순위를 그대로 사용한다.
    # ========================================================

    if strong_title_seed:

        preferred = strong_title_seed

    elif strong_title:

        preferred = strong_title

    else:

        preferred = candidates

    preferred.sort(

        key=lambda item: (
            -float(
                item.get(
                    "score",
                    0
                )
                or 0
            )
        )
    )

    top_score = float(
        preferred[
            0
        ].get(
            "score",
            0
        )
        or 0
    )

    if top_score <= 0:

        return []

    # ========================================================
    # E. 최종 anchor는 최고점의 95% 이상만 유지한다.
    #
    # direct basis 자체는 여러 후보를 보여줄 수 있지만,
    # 대표 anchor는 거의 동급인 경우만 복수로 유지한다.
    # ========================================================

    threshold = (
        top_score
        *
        0.95
    )

    anchors = [

        item

        for item in preferred

        if float(
            item.get(
                "score",
                0
            )
            or 0
        )
        >= threshold
    ]

    if not anchors:

        return [
            preferred[
                0
            ]
        ]

    return anchors
