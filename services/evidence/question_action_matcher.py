# ============================================================
# Question Action Matcher
#
# 역할
#
# 사용자의 자연어 질문에서
# "질문의 핵심 행위"를 추출하고,
# 법률 조문이 그 행위를 실제로 포함하는지 확인한다.
#
# 예:
#
# 회사에서 장애인 고용 안 하면?
# → 고용
#
# 다른 사람 특허를 침해하면 어떻게 돼?
# → 침해
#
# 개인정보를 동의 없이 수집하면 어떻게 돼?
# → 수집
#
# 중요:
#
# - 특정 법률명 하드코딩 금지
# - 특정 조문번호 하드코딩 금지
# - 분야별 synonym dictionary 사용 금지
# ============================================================

import re

from typing import (
    Any,
    List,
    Set,
)


# ============================================================
# 1. 질문에서 제거할 일반 표현
# ============================================================

QUESTION_GENERIC_WORDS = {

    "하면",
    "안하면",
    "안",
    "않으면",

    "어떻게",
    "어떻게돼",
    "어떻게되",

    "되면",
    "돼",
    "되나",
    "되나요",

    "뭐야",
    "무엇",

    "알려줘",
    "알려",

    "관련",
    "대한",
    "대해",
    "대해서",

    "경우",

    "사람",
    "다른",

    "없이",
}


# ============================================================
# 2. 사용자 주체 표현
#
# 핵심 행위 후보에서 제외한다.
# ============================================================

QUESTION_ROLE_WORDS = {

    "회사",
    "직장",
    "사장",

    "직원",
    "근로자",

    "사업주",
    "사업자",

    "국가",

    "지자체",
    "지방자치단체",

    "공공기관",
}


# ============================================================
# 3. 문자열 정리
# ============================================================

def clean_text(
    value: Any
) -> str:

    if value is None:

        return ""


    return re.sub(

        r"\s+",

        " ",

        str(
            value
        ),
    ).strip()


# ============================================================
# 4. 조사 제거
#
# 개인정보를 → 개인정보
# 특허를 → 특허
# 회사에서 → 회사
#
# 형태소 분석기를 쓰지 않는 최소 규칙.
# ============================================================

def strip_korean_particle(
    token: str
) -> str:

    token = clean_text(
        token
    )


    particles = (

        "으로부터",
        "에게서",

        "에서는",
        "에게는",

        "으로",
        "에서",
        "에게",
        "한테",

        "까지",
        "부터",

        "처럼",
        "보다",

        "하고",
        "이랑",
        "랑",

        "에는",
        "에도",

        "은",
        "는",
        "이",
        "가",

        "을",
        "를",

        "의",

        "에",

        "와",
        "과",

        "도",
        "만",
    )


    for particle in particles:

        if (
            token.endswith(
                particle
            )
            and
            len(
                token
            )
            >
            len(
                particle
            )
            +
            1
        ):

            return token[
                :-
                len(
                    particle
                )
            ]


    return token


# ============================================================
# 5. 질문형 어미 제거
#
# 침해하면 → 침해
# 수집하면 → 수집
# 지급하면 → 지급
#
# 무리하게 일반 동사 어간을 변형하지 않는다.
# ============================================================

def strip_question_ending(
    token: str
) -> str:

    token = clean_text(
        token
    )


    endings = (

        "하지않으면",
        "하지않을때",

        "하였을때",
        "했을때",

        "한다면",

        "하면",

        "할때",

        "했으면",
    )


    for ending in endings:

        if (
            token.endswith(
                ending
            )
            and
            len(
                token
            )
            >
            len(
                ending
            )
        ):

            base = token[
                :-
                len(
                    ending
                )
            ]


            # ------------------------------------------------
            # 침해 + 하면처럼
            # 질문 핵심 명사형 행위를 그대로 보존
            # ------------------------------------------------

            if len(
                base
            ) >= 2:

                return base


    return token


# ============================================================
# 6. 질문 토큰 정규화
# ============================================================

def normalize_question_token(
    token: str
) -> str:

    token = clean_text(
        token
    ).lower()


    if not token:

        return ""


    token = strip_question_ending(
        token
    )


    token = strip_korean_particle(
        token
    )


    return token.strip()


# ============================================================
# 7. 질문의 의미 토큰
# ============================================================

def extract_content_tokens(
    question: str
) -> List[str]:

    question = clean_text(
        question
    ).lower()


    raw_tokens = re.findall(
        r"[가-힣A-Za-z0-9]+",
        question
    )


    results = []


    for raw in raw_tokens:

        token = normalize_question_token(
            raw
        )


        if len(
            token
        ) < 2:

            continue


        if token in QUESTION_GENERIC_WORDS:

            continue


        if token in QUESTION_ROLE_WORDS:

            continue


        if token not in results:

            results.append(
                token
            )


    return results


# ============================================================
# 8. 핵심 행위 토큰
#
# 한국어 자연어 법률 질문은 일반적으로
#
# 목적어/대상 + 행위 + 하면?
#
# 구조가 많기 때문에 마지막 의미 토큰을
# 핵심 행위 anchor로 사용한다.
#
# 예:
#
# 장애인 / 고용
# → 고용
#
# 특허 / 침해
# → 침해
#
# 개인정보 / 동의 / 수집
# → 수집
# ============================================================

def extract_action_token(
    question: str
) -> str:

    tokens = extract_content_tokens(
        question
    )


    if not tokens:

        return ""


    return tokens[
        -1
    ]


# ============================================================
# 9. 질문의 나머지 핵심 개념
# ============================================================

def extract_object_tokens(
    question: str
) -> List[str]:

    tokens = extract_content_tokens(
        question
    )


    if len(
        tokens
    ) <= 1:

        return tokens


    return tokens[
        :-1
    ]


# ============================================================
# 10. 부분 문자열 매칭
#
# 침해 → 침해한 / 침해행위 / 권리침해
# 수집 → 수집ㆍ이용
# 고용 → 고용하여야
#
# 이런 형태를 허용한다.
# ============================================================

def token_matches_text(
    token: str,
    text: str
) -> bool:

    token = clean_text(
        token
    ).lower()


    text = clean_text(
        text
    ).lower()


    if not token or not text:

        return False


    return token in text


# ============================================================
# 11. 핵심 행위 매칭
# ============================================================

def has_action_match(
    question: str,
    text: str
) -> bool:

    action_token = extract_action_token(
        question
    )


    if not action_token:

        return False


    return token_matches_text(
        action_token,
        text
    )


# ============================================================
# 12. 객체/주제 토큰 매칭 수
# ============================================================

def count_object_matches(
    question: str,
    text: str
) -> int:

    object_tokens = extract_object_tokens(
        question
    )


    return sum(

        1

        for token in object_tokens

        if token_matches_text(
            token,
            text
        )
    )


# ============================================================
# 13. Action + Object 연결도
# ============================================================

def score_question_connection(
    question: str,
    title: str,
    body: str
) -> dict:

    title = clean_text(
        title
    )


    body = clean_text(
        body
    )


    combined = (
        f"{title} {body}"
    ).strip()


    action_token = extract_action_token(
        question
    )


    object_tokens = extract_object_tokens(
        question
    )


    title_action_match = bool(
        action_token
        and
        token_matches_text(
            action_token,
            title
        )
    )


    body_action_match = bool(
        action_token
        and
        token_matches_text(
            action_token,
            body
        )
    )


    title_object_matches = sum(

        1

        for token in object_tokens

        if token_matches_text(
            token,
            title
        )
    )


    body_object_matches = sum(

        1

        for token in object_tokens

        if token_matches_text(
            token,
            body
        )
    )


    action_match = (
        title_action_match
        or
        body_action_match
    )


    object_match_count = max(

        title_object_matches,

        body_object_matches,
    )


    return {

        "action_token":
            action_token,

        "object_tokens":
            object_tokens,

        "action_match":
            action_match,

        "title_action_match":
            title_action_match,

        "body_action_match":
            body_action_match,

        "title_object_matches":
            title_object_matches,

        "body_object_matches":
            body_object_matches,

        "object_match_count":
            object_match_count,

        "combined_match":
            bool(
                action_match
                and
                (
                    object_match_count > 0
                    or
                    not object_tokens
                )
            ),
    }