# ============================================================
# Fallback Response
#
# 역할:
# - OrganizedEvidence가 충분하지 않을 때 aiSearch laws를 사용
# - Query Expansion + Reranker가 만든 최종 검색 순위를 보존
# - 검색 순위 정보가 없는 예외 입력만 response scoring 사용
#
# 핵심 원칙:
# - 이미 검색/Reranker 단계에서 정렬된 Evidence를
#   답변 단계에서 다시 뒤집지 않는다.
# - 특정 법률명/조문번호 하드코딩 없음.
# ============================================================

from typing import (
    List,
)

from services.generation.response_utils import (
    clean_text,
    make_article_label,
)

from services.generation.response_scoring import (
    extract_core_statement,
    score_law_item,
)


CORE_LAW_LIMIT = 3


def _safe_rank(
    value
):
    try:
        rank = int(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return None

    if rank <= 0:
        return None

    return rank


def _has_retrieval_order(
    item: dict
) -> bool:

    if not isinstance(
        item,
        dict
    ):
        return False

    return (
        _safe_rank(
            item.get(
                "final_rank"
            )
        )
        is not None
        or
        item.get(
            "relevance_score"
        )
        is not None
    )


def _select_by_retrieval_order(
    laws: list,
    limit: int
) -> List[dict]:
    """
    Query Expansion / Reranker가 이미 만든 순서를 그대로 보존한다.

    final_rank가 있으면 해당 값을 우선 사용하고,
    final_rank가 없지만 relevance_score가 있는 경우에는
    현재 리스트 순서를 보존한다.
    """

    candidates = []

    for index, item in enumerate(
        laws
    ):

        if not isinstance(
            item,
            dict
        ):
            continue

        final_rank = _safe_rank(
            item.get(
                "final_rank"
            )
        )

        if final_rank is None:
            final_rank = (
                index
                +
                1
            )

        candidates.append(
            (
                final_rank,
                index,
                item,
            )
        )

    candidates.sort(
        key=lambda value: (
            value[0],
            value[1],
        )
    )

    return [
        item
        for _, _, item in candidates[
            :limit
        ]
    ]


def _select_by_response_score(
    laws: list,
    question: str,
    limit: int
) -> List[dict]:
    """
    검색 순위 메타데이터가 전혀 없는 예외 입력용 fallback.
    기존 response scoring 동작을 유지한다.
    """

    candidates = []

    for index, item in enumerate(
        laws
    ):

        if not isinstance(
            item,
            dict
        ):
            continue

        score = score_law_item(
            item=item,
            question=question,
        )

        candidates.append(
            (
                score,
                index,
                item,
            )
        )

    candidates.sort(
        key=lambda value: (
            -value[0],
            value[1],
        )
    )

    return [
        item
        for _, _, item in candidates[
            :limit
        ]
    ]


def select_core_laws(
    laws: list,
    question: str,
    limit: int = CORE_LAW_LIMIT
) -> List[dict]:

    if not isinstance(
        laws,
        list
    ):
        return []

    valid_laws = [
        item
        for item in laws
        if isinstance(
            item,
            dict
        )
    ]

    if not valid_laws:
        return []

    # ========================================================
    # A. 정상 경로
    #
    # Query Expansion + Reranker가 이미 관련도를 계산한 경우
    # 검색 단계의 최종 순위를 그대로 사용한다.
    #
    # 이전 구현은 여기에서 response_score로 다시 정렬하여
    # 검색 1위 조문을 뒤로 보내는 회귀가 발생할 수 있었다.
    # ========================================================

    if any(
        _has_retrieval_order(
            item
        )
        for item in valid_laws
    ):

        return _select_by_retrieval_order(
            laws=valid_laws,
            limit=limit,
        )

    # ========================================================
    # B. 예외 경로
    #
    # 검색 순위 메타데이터가 없는 입력만 기존 점수로 정렬.
    # ========================================================

    return _select_by_response_score(
        laws=valid_laws,
        question=question,
        limit=limit,
    )


def build_laws_core_answer(
    laws: list,
    question: str = ""
) -> str:

    selected = select_core_laws(
        laws=laws,
        question=question,
        limit=CORE_LAW_LIMIT,
    )

    if not selected:
        return ""

    lines = [
        (
            "**관련 공식 조문은 확인되었지만, "
            "현재 근거만으로 하나의 직접적인 법적 결론으로 "
            "확정하지 않았습니다.**"
        ),
    ]

    for item in selected:

        law_name = clean_text(
            item.get(
                "law_name"
            )
        )

        article_label = make_article_label(
            item.get(
                "article_number"
            ),
            item.get(
                "sub_article_number",
                0
            ),
        )

        title = clean_text(
            item.get(
                "article_title"
            )
        )

        heading = " ".join(
            value
            for value in (
                law_name,
                article_label,
            )
            if value
        )

        if title:

            heading += (
                f" ({title})"
            )

        statement = extract_core_statement(
            evidence=item,
            question=question,
        )

        lines.append(
            f"- **{heading}**"
        )

        if statement:

            lines.append(
                f"  - {statement}"
            )

    return "\n".join(
        lines
    ).strip()
