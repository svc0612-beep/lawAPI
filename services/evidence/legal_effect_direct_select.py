# ============================================================
# Legal Effect Direct Select
#
# Direct Basis 후보 생성 및 최종 Anchor 선택.
# 점수 계산은 score 모듈에 맡기고, 최종 Anchor 품질 게이트만 담당한다.
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

                "local_seed_bridge":
                    details.get(
                        "local_seed_bridge",
                        False
                    ),

                "bridge_seed_article_number":
                    details.get(
                        "bridge_seed_article_number",
                        0
                    ),

                "bridge_distance":
                    details.get(
                        "bridge_distance",
                        999
                    ),

                "bridge_prefix_length":
                    details.get(
                        "bridge_prefix_length",
                        0
                    ),

                "connection_level":
                    0,
            }
        )

    return results


def select_direct_anchors(
    direct_basis: List[
        Dict[str, Any]
    ]
) -> List[
    Dict[str, Any]
]:

    if not direct_basis:

        return []

    # ========================================================
    # 1. 질문의 Action + Object가 실제 조문에서 함께 확인되고,
    #    제목에서도 핵심 Action이 직접 확인되는 후보를 최우선한다.
    #
    # 이유:
    # Local Seed Bridge는 "검색된 조문 근처"를 탐색하기 위한
    # 보조 장치다. 그런데 기존 구현은 Bridge 후보가 하나라도
    # 있으면 실제 의미 일치 후보를 전부 제쳐버렸다.
    #
    # 그 결과:
    # - 무면허 운전 → 결격사유/시험 조문
    # - 해고 → 예고 조문
    # - 특허 침해 → 소송 절차 조문
    #
    # 같은 현상이 발생할 수 있었다.
    #
    # 특정 법률명/조문번호 하드코딩 없음.
    # ========================================================

    preferred = [

        item

        for item in direct_basis

        if bool(
            item.get(
                "combined_match"
            )
        )
        and
        bool(
            item.get(
                "title_action_match"
            )
        )
    ]

    # ========================================================
    # 2. 제목까지는 아니더라도,
    #    Action + Object가 같은 조문에서 실제로 연결되는 후보.
    #
    # 질문 의미와 조문 본문이 직접 연결되므로
    # 단순 검색 근접성(Local Bridge)보다 우선한다.
    # ========================================================

    if not preferred:

        preferred = [

            item

            for item in direct_basis

            if bool(
                item.get(
                    "combined_match"
                )
            )
            and
            bool(
                item.get(
                    "action_match"
                )
            )
        ]

    # ========================================================
    # 3. Object가 없는 질문에서는 제목의 Action 직접 일치를 사용.
    #
    # 예:
    # "폭행하면?", "침해하면?"처럼
    # 질문에 별도 객체 토큰이 없을 수 있다.
    # ========================================================

    if not preferred:

        preferred = [

            item

            for item in direct_basis

            if bool(
                item.get(
                    "title_action_match"
                )
            )
        ]

    # ========================================================
    # 4. 실제 의미 일치 후보가 없을 때만 Local Seed Bridge 사용.
    #
    # Bridge는 다음과 같은 경우의 fallback이다.
    #
    # - 절도: 자연어 "훔치다" ↔ 법률어 "절취"
    # - 빌린 돈: 자연어 "갚다" ↔ 법률어 "반환"
    # - 신호위반: 검색 seed 주변의 실제 신호 준수 의무 조문
    #
    # 즉 Bridge는 semantic match를 대체하지 않고,
    # semantic match가 없을 때만 보완한다.
    # ========================================================

    if not preferred:

        preferred = [

            item

            for item in direct_basis

            if bool(
                item.get(
                    "local_seed_bridge"
                )
            )
        ]

    # ========================================================
    # 5. 마지막 fallback.
    # ========================================================

    if not preferred:

        preferred = list(
            direct_basis
        )

    preferred.sort(

        key=lambda item: (
            -float(
                item.get(
                    "score",
                    0
                )
                or 0
            ),
            int(
                item.get(
                    "bridge_distance",
                    999
                )
                or 999
            ),
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
    # 품질 후보끼리는 최고점의 90% 이상만 anchor로 유지.
    # ========================================================

    threshold = (
        top_score
        *
        0.90
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
