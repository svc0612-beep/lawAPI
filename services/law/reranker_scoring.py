# ============================================================
# Reranker 점수 계산
#
# 원칙
# - 특정 법률 분야 하드코딩 없음
# - 의미 있는 질의 토큰과 실제 조문/법령명의 일치를 우선
# - aiSearch 원본 순위는 보조 신호로만 사용
# - 문자열 일치가 전혀 없는 결과는 원본 순위만으로 올라오지 않음
# ============================================================

from services.law.reranker_utils import (
    normalize_text,
    compact_text,
    partial_match_score,
)

from services.law.reranker_tokens import (
    tokenize_query,
)


# ============================================================
# 1. 토큰 하나의 관련성 점수
# ============================================================

def score_token(
    token: str,
    law_name: str,
    article_title: str,
    article_text: str
):

    best_score = 0.0

    # --------------------------------------------------------
    # 법령명
    #
    # 자연어 질문에서 법령 주제를 구별하는 데 중요한 신호다.
    # --------------------------------------------------------

    law_match = partial_match_score(
        token,
        law_name
    )

    if law_match > 0:

        best_score = max(
            best_score,
            12.0
            * law_match
        )

    # --------------------------------------------------------
    # 조문 제목
    # --------------------------------------------------------

    title_match = partial_match_score(
        token,
        article_title
    )

    if title_match > 0:

        best_score = max(
            best_score,
            10.0
            * title_match
        )

    # --------------------------------------------------------
    # 조문 본문
    # --------------------------------------------------------

    body_match = partial_match_score(
        token,
        article_text
    )

    if body_match > 0:

        best_score = max(
            best_score,
            4.0
            * body_match
        )

    return round(
        best_score,
        2
    )


# ============================================================
# 2. 결과 하나의 관련성 점수
# ============================================================

def score_law_result(
    query: str,
    item: dict,
    fallback_mode: bool = False
):

    tokens = tokenize_query(
        query
    )

    law_name = normalize_text(
        item.get(
            "law_name"
        )
    )

    article_title = normalize_text(
        item.get(
            "article_title"
        )
    )

    article_text = normalize_text(
        item.get(
            "article_text"
        )
    )

    score = 0.0

    matched_tokens = []

    # ========================================================
    # 전체 질의 직접 일치
    #
    # 매우 강한 보조 신호이지만 이것만으로 coverage를 만들지는 않는다.
    # ========================================================

    compact_query = compact_text(
        query
    )

    if compact_query:

        if compact_query in compact_text(
            law_name
        ):

            score += 18

        if compact_query in compact_text(
            article_title
        ):

            score += 16

        if compact_query in compact_text(
            article_text
        ):

            score += 6

    # ========================================================
    # 의미 있는 토큰 일치
    # ========================================================

    for token in tokens:

        token_score = score_token(

            token=token,

            law_name=law_name,

            article_title=article_title,

            article_text=article_text
        )

        if token_score <= 0:
            continue

        matched_tokens.append(
            token
        )

        score += token_score

    # ========================================================
    # coverage
    # ========================================================

    if tokens:

        coverage = (
            len(
                matched_tokens
            )
            /
            len(
                tokens
            )
        )

    else:

        coverage = 0.0

    # ========================================================
    # coverage 보너스
    # ========================================================

    if coverage == 1.0:

        score += 12

    elif coverage >= 0.5:

        score += 6

    elif coverage >= 0.34:

        score += 2

    # ========================================================
    # aiSearch 원본 순위
    #
    # 원본 순위는 실제 질의 토큰이 하나라도 일치했을 때만
    # 보너스로 사용한다.
    #
    # 따라서 coverage=0 결과가 검색 순위 하나만으로
    # 상위에 남는 문제를 막는다.
    # ========================================================

    try:

        original_rank = int(
            item.get(
                "rank",
                999
            )
        )

    except (
        TypeError,
        ValueError
    ):

        original_rank = 999

    if (
        coverage > 0
        and
        original_rank <= 10
    ):

        if fallback_mode:

            rank_bonus = max(
                0,
                6
                -
                (
                    original_rank
                    * 0.5
                )
            )

        else:

            rank_bonus = max(
                0,
                4
                -
                (
                    original_rank
                    * 0.35
                )
            )

        score += rank_bonus

    return {

        "score":
            round(
                score,
                2
            ),

        "coverage":
            round(
                coverage,
                2
            ),

        "matched_tokens":
            matched_tokens,

        "original_rank":
            original_rank,
    }
