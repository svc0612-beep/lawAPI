# ============================================================
# Reranker 검색어 토큰 처리
#
# 목표
# - 특정 법률/법률 분야를 하드코딩하지 않는다.
# - 조사, 질문 어미, 일반적인 대화 표현을 제거한다.
# - "음주운전하면" -> "음주운전"
# - "행정처분에" -> "행정처분"
# - "개인정보를" -> "개인정보"
# 같은 범용 정규화만 수행한다.
# ============================================================

import re

from services.law.reranker_utils import (
    normalize_text,
)


# ============================================================
# 1. 의미가 약한 일반 표현
# ============================================================

STOP_WORDS = {
    "관련",
    "대해",
    "대해서",
    "대한",
    "관한",

    "알려줘",
    "알려주세요",
    "알려",
    "설명",
    "설명해줘",
    "설명해주세요",

    "뭐야",
    "뭔가요",
    "무엇",
    "어떻게",
    "어떤",

    "있어",
    "있나요",
    "있습니까",

    "법",
    "법률",
    "법령",

    # 부정/질문 보조 표현
    "안",
    "못",
    "돼",
    "되",
    "해",
    "해야",

    # 일반 지시/대명 표현
    "다른",
    "남의",
    "내",
    "내가",
    "저",
    "제가",

    # 법률 주제를 구별하는 데 거의 도움이 없는 일반 인칭어
    "사람",
}


# ============================================================
# 2. 범용 한국어 조사
#
# 긴 조사부터 먼저 제거한다.
# ============================================================

PARTICLE_SUFFIXES = (
    "에게서",
    "한테서",
    "으로부터",
    "에서부터",
    "까지는",
    "에서는",
    "에게는",
    "한테는",
    "으로는",
    "로부터",
    "에게",
    "한테",
    "에서",
    "부터",
    "까지",
    "처럼",
    "보다",
    "으로",
    "라도",
    "이라도",
    "에게도",
    "한테도",
    "에는",
    "에도",
    "과",
    "와",
    "의",
    "을",
    "를",
    "이",
    "가",
    "은",
    "는",
    "에",
    "로",
    "도",
    "만",
)


# ============================================================
# 3. 질문에서 자주 붙는 범용 어미
#
# 법률용어 사전이 아니라 질문 문법만 처리한다.
# ============================================================

QUESTION_ENDINGS = (
    "한다면",
    "된다면",
    "했다면",
    "하였다면",
    "하면",
    "되면",
    "이라면",
    "라면",
    "하려면",
    "하려고",
    "했을때",
    "했을 때",
    "할때",
    "할 때",
    "이면",
    "면",
)


def strip_particle(
    token: str
) -> str:
    """
    명사 뒤의 일반 조사를 한 번 제거한다.
    너무 짧아지는 경우에는 원문을 유지한다.
    """

    for suffix in PARTICLE_SUFFIXES:

        if not token.endswith(
            suffix
        ):
            continue

        stem = token[
            :-len(suffix)
        ]

        if len(stem) >= 2:
            return stem

    return token


def strip_question_ending(
    token: str
) -> str:
    """
    자연어 질문 끝에 붙는 일반적인 조건/질문 어미를 제거한다.

    예:
    - 음주운전하면 -> 음주운전
    - 신호위반하면 -> 신호위반
    - 불복하려면 -> 불복

    어미 제거 후 1글자만 남는 경우에는
    관련성 점수용 토큰으로 사용하기엔 정보량이 너무 적으므로
    빈 문자열로 제거한다.

    예:
    - 내면 -> 내 -> 제거
    - 가면 -> 가 -> 제거
    """

    for ending in QUESTION_ENDINGS:

        if not token.endswith(
            ending
        ):
            continue

        stem = token[
            :-len(ending)
        ]

        if len(stem) >= 2:
            return stem

        return ""

    return token


def normalize_query_token(
    token: str
) -> str:
    """
    개별 토큰을 범용적으로 정규화한다.
    """

    token = normalize_text(
        token
    ).strip()

    if not token:
        return ""

    # 먼저 질문 어미를 제거한다.
    token = strip_question_ending(
        token
    )

    if not token:
        return ""

    # 그다음 조사를 제거한다.
    token = strip_particle(
        token
    )

    token = token.strip()

    if len(token) < 2:
        return ""

    if token in STOP_WORDS:
        return ""

    return token


def tokenize_query(
    query: str
):
    """
    질의를 법률 관련성 계산용 토큰으로 변환한다.

    특정 법률명이나 특정 범죄/행위의 동의어는 넣지 않는다.
    """

    query = normalize_text(
        query
    )

    if not query:
        return []

    raw_tokens = re.findall(
        r"[가-힣A-Za-z0-9]+",
        query
    )

    tokens = []

    for raw_token in raw_tokens:

        token = normalize_query_token(
            raw_token
        )

        if not token:
            continue

        if token not in tokens:

            tokens.append(
                token
            )

    return tokens
