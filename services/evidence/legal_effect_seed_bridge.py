# ============================================================
# Legal Effect Seed Bridge
#
# 같은 법령 안에서 "가까운 검색 seed 조문"과
# full law 조문 제목의 핵심어 연결을 계산한다.
#
# 특정 법률명/조문번호/주제 하드코딩 없음.
# ============================================================

import re

from typing import (
    Any,
    Dict,
)


LOCAL_SEED_MAX_DISTANCE = 3
LOCAL_SEED_MAX_RANK = 4


BRIDGE_GENERIC_TOKENS = {
    "관련",
    "관계",
    "정의",
    "통칙",
    "기준",
    "방법",
    "절차",
    "업무",
    "관리",
    "설치",
    "운영",
    "규정",
    "사항",
    "등",
    "등의",
    "대한",
    "따른",
    "따를",
    "및",
    "또는",
    "그",
    "의무",
    "금지",
    "책임",
    "벌칙",
    "처벌",
    "과태료",
    "손해배상",
}


BRIDGE_EXCEPTION_TERMS = (
    "불능",
    "예외",
    "제외",
    "면제",
    "특례",
)


def clean_text(
    value: Any
) -> str:

    return " ".join(
        str(
            value
            or ""
        ).split()
    )


def split_bridge_tokens(
    title: str
):

    raw_tokens = re.findall(
        r"[가-힣A-Za-z0-9]+",
        clean_text(
            title
        ).lower(),
    )

    results = []

    for token in raw_tokens:

        token = re.sub(
            r"[^가-힣A-Za-z0-9]",
            "",
            token,
        )

        if len(
            token
        ) < 2:
            continue

        if token in BRIDGE_GENERIC_TOKENS:
            continue

        if token not in results:

            results.append(
                token
            )

    return results


def common_prefix_length(
    left: str,
    right: str
) -> int:

    length = 0

    for left_char, right_char in zip(
        left,
        right
    ):

        if left_char != right_char:
            break

        length += 1

    return length


def seed_article_number(
    key: str
) -> int:

    try:

        value = str(
            key
            or ""
        ).split(
            ":",
            1
        )[0]

        return int(
            value
        )

    except (
        TypeError,
        ValueError,
    ):

        return 0


def find_local_seed_bridge(
    article: Dict[str, Any],
    title: str,
    seed_map: Dict[
        str,
        Dict[str, Any]
    ],
) -> Dict[str, Any]:

    try:

        article_number = int(
            article.get(
                "article_number"
            )
            or 0
        )

    except (
        TypeError,
        ValueError,
    ):

        article_number = 0

    if article_number <= 0:
        return {}

    article_tokens = split_bridge_tokens(
        title
    )

    if not article_tokens:
        return {}

    best = {}

    # --------------------------------------------------------
    # 검색 Seed 전체를 서로 연결하면
    # 서로 다른 세부 상황의 조문까지 의미가 번진다.
    #
    # 따라서 현재 검색에서 가장 높은 순위의 Seed만
    # 의미 기준점(anchor)으로 사용한다.
    # --------------------------------------------------------

    valid_ranks = []

    for seed in seed_map.values():

        if not isinstance(
            seed,
            dict
        ):
            continue

        try:

            seed_rank = int(
                seed.get(
                    "rank"
                )
                or 999
            )

        except (
            TypeError,
            ValueError,
        ):

            seed_rank = 999

        if seed_rank > 0:

            valid_ranks.append(
                seed_rank
            )

    if not valid_ranks:
        return {}

    best_seed_rank = min(
        valid_ranks
    )

    for seed_key, seed in (
        seed_map.items()
    ):

        if not isinstance(
            seed,
            dict
        ):
            continue

        seed_number = seed_article_number(
            seed_key
        )

        if seed_number <= 0:
            continue

        distance = abs(
            article_number
            -
            seed_number
        )

        if distance > LOCAL_SEED_MAX_DISTANCE:
            continue

        try:

            seed_rank = int(
                seed.get(
                    "rank"
                )
                or 999
            )

        except (
            TypeError,
            ValueError,
        ):

            seed_rank = 999

        if seed_rank != best_seed_rank:
            continue

        seed_title = clean_text(
            seed.get(
                "title"
            )
        )

        seed_tokens = split_bridge_tokens(
            seed_title
        )

        if not seed_tokens:
            continue

        best_prefix = 0

        for article_token in article_tokens:

            for seed_token in seed_tokens:

                best_prefix = max(
                    best_prefix,
                    common_prefix_length(
                        article_token,
                        seed_token,
                    ),
                )

        if best_prefix < 2:
            continue

        candidate = {
            "seed_number":
                seed_number,

            "seed_rank":
                seed_rank,

            "distance":
                distance,

            "prefix_length":
                best_prefix,

            "seed_title":
                seed_title,
        }

        if not best:

            best = candidate
            continue

        candidate_key = (
            -candidate[
                "prefix_length"
            ],
            candidate[
                "distance"
            ],
            candidate[
                "seed_rank"
            ],
        )

        best_key = (
            -best[
                "prefix_length"
            ],
            best[
                "distance"
            ],
            best[
                "seed_rank"
            ],
        )

        if candidate_key < best_key:

            best = candidate

    return best


def has_bridge_exception(
    title: str
) -> bool:

    normalized = clean_text(
        title
    ).lower()

    return any(
        term in normalized
        for term in BRIDGE_EXCEPTION_TERMS
    )
