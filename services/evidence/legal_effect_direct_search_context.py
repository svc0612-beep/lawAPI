# ============================================================
# Legal Effect Direct - Search Context
#
# Query Expansion / Reranker가 이미 확보한 검색 의미와 품질을
# Direct Basis 단계에서 보존해 사용하는 보조 모듈.
#
# 중요:
# - 특정 법률명 하드코딩 없음
# - 특정 조문번호 하드코딩 없음
# - 분야별 synonym dictionary 없음
# - 검색 관련성에만 사용하고 법률 사실을 생성하지 않음
# ============================================================

import re

from typing import (
    Any,
    Dict,
    List,
)

from services.evidence.legal_effect_utils import (
    clean_text,
    safe_int,
)


NEGATIVE_CONTEXT_MARKERS = (
    "없이",
    "안",
    "않",
    "못",
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


def clean_list(
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


def compact(
    value: Any
) -> str:

    return re.sub(
        r"\s+",
        "",
        clean_text(
            value
        ).lower(),
    )


def question_negative_markers(
    question: str
) -> List[str]:

    question_text = clean_text(
        question
    ).lower()

    raw_tokens = re.findall(
        r"[가-힣A-Za-z0-9]+",
        question_text,
    )

    results = []

    for marker in NEGATIVE_CONTEXT_MARKERS:

        if marker == "안":

            if marker in raw_tokens:

                results.append(
                    marker
                )

            continue

        if marker in question_text:

            results.append(
                marker
            )

    return results


def novel_expansion_terms(
    question: str,
    terms: Any,
) -> List[str]:

    question_compact = compact(
        question
    )

    results = []

    for term in clean_list(
        terms
    ):

        term_compact = compact(
            term
        )

        if len(
            term_compact
        ) < 2:

            continue

        # 원 질문에 이미 포함된 단순 분해어는
        # 새로운 의미 확장으로 보지 않는다.
        #
        # 예:
        # 음주운전 → 음주 / 운전
        if (
            term_compact in question_compact
            or
            question_compact in term_compact
        ):

            continue

        if term not in results:

            results.append(
                term
            )

    return results


def count_term_matches(
    terms: List[str],
    text: str,
) -> int:

    normalized = clean_text(
        text
    ).lower()

    return sum(
        1
        for term in terms
        if clean_text(
            term
        ).lower()
        in normalized
    )


def build_seed_search_context(
    seed: Any,
    question: str,
    title: str,
    lead_text: str,
    title_roles: List[str],
    normative_roles: List[str],
) -> Dict[str, Any]:

    context = {

        "query_coverage":
            0.0,

        "original_rank":
            999,

        "final_rank":
            999,

        "matched_tokens":
            [],

        "expansion_terms":
            [],

        "novel_expansion_terms":
            [],

        "novel_title_matches":
            0,

        "novel_body_matches":
            0,

        "negative_context_match":
            False,

        "semantic_seed_search_support":
            False,

        "semantic_seed_bypass":
            False,
    }

    if not isinstance(
        seed,
        dict
    ):

        return context

    context[
        "query_coverage"
    ] = max(
        0.0,
        min(
            1.0,
            safe_float(
                seed.get(
                    "query_coverage"
                ),
                0.0,
            ),
        ),
    )

    context[
        "original_rank"
    ] = safe_int(
        seed.get(
            "original_rank"
        ),
        999,
    )

    context[
        "final_rank"
    ] = safe_int(
        seed.get(
            "final_rank"
        )
        or
        seed.get(
            "rank"
        ),
        999,
    )

    context[
        "matched_tokens"
    ] = clean_list(
        seed.get(
            "matched_tokens"
        )
    )

    context[
        "expansion_terms"
    ] = clean_list(
        seed.get(
            "query_expansion_terms"
        )
    )

    context[
        "novel_expansion_terms"
    ] = novel_expansion_terms(
        question,
        context[
            "expansion_terms"
        ],
    )

    context[
        "novel_title_matches"
    ] = count_term_matches(
        context[
            "novel_expansion_terms"
        ],
        title,
    )

    context[
        "novel_body_matches"
    ] = count_term_matches(
        context[
            "novel_expansion_terms"
        ],
        lead_text,
    )

    negative_markers = question_negative_markers(
        question
    )

    matched_token_text = " ".join(
        context[
            "matched_tokens"
        ]
    ).lower()

    context[
        "negative_context_match"
    ] = bool(
        negative_markers
        and
        any(
            marker in matched_token_text
            for marker in negative_markers
        )
    )

    context[
        "semantic_seed_search_support"
    ] = bool(
        (
            context[
                "query_coverage"
            ] >= 0.75
            and
            len(
                context[
                    "matched_tokens"
                ]
            ) >= 2
        )
        or
        context[
            "novel_title_matches"
        ] > 0
        or
        context[
            "novel_body_matches"
        ] > 0
    )

    context[
        "semantic_seed_bypass"
    ] = bool(
        context[
            "semantic_seed_search_support"
        ]
        and
        (
            title_roles
            or
            normative_roles
        )
    )

    return context


def score_seed_search_context(
    context: Dict[str, Any]
) -> float:

    score = 0.0

    query_coverage = safe_float(
        context.get(
            "query_coverage"
        ),
        0.0,
    )

    original_rank = safe_int(
        context.get(
            "original_rank"
        ),
        999,
    )

    final_rank = safe_int(
        context.get(
            "final_rank"
        ),
        999,
    )

    score += (
        query_coverage
        *
        20.0
    )

    if original_rank < 999:

        score += max(
            0.0,
            32.0
            -
            (
                max(
                    original_rank,
                    1,
                )
                -
                1
            )
            *
            3.0
        )

    if (
        original_rank < 999
        and
        final_rank < 999
    ):

        rank_jump = max(
            0,
            original_rank
            -
            final_rank
            -
            2,
        )

        score -= min(
            30.0,
            rank_jump
            *
            2.0,
        )

    score += min(
        safe_int(
            context.get(
                "novel_title_matches"
            ),
            0,
        ),
        2,
    ) * 20.0

    score += min(
        safe_int(
            context.get(
                "novel_body_matches"
            ),
            0,
        ),
        2,
    ) * 4.0

    if context.get(
        "negative_context_match"
    ):

        score += 20.0

    if context.get(
        "semantic_seed_bypass"
    ):

        score += 10.0

    return score
