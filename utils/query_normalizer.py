# ============================================================
# 법률 검색어 정규화
#
# 역할
# 사용자의 자연어 질문을
# 법률 API 검색에 적합한 핵심 검색어로 변환한다.
#
# 예:
#
# 특허 침해하면 어떻게 돼?
# → 특허 침해
#
# 장애인 취업 관련 법 알려줘
# → 장애인 취업
#
# 회사에서 장애인 고용 안 하면?
# → 장애인 고용 의무
#
# 장애인 고용에 대해서 설명해줘
# → 장애인 고용
#
# 중요:
# - LLM 사용 없음
# - 외부 API 호출 없음
# - 검색 전처리만 담당
# ============================================================

import re


# ============================================================
# 1. 질문/요청 표현
# ============================================================

QUESTION_PHRASES = [

    # 긴 표현 먼저
    "어떻게 되는 거야",
    "어떻게 되는거야",
    "어떻게 처리되나요",
    "어떻게 처리돼",
    "어떻게 되나요",
    "어떻게 되지",
    "어떻게 돼",

    "설명해주세요",
    "설명해 주세요",
    "설명해줘",
    "설명해 줘",

    "알려주세요",
    "알려 주세요",
    "알려줘",
    "알려 줘",

    "찾아주세요",
    "찾아 주세요",
    "찾아줘",
    "찾아 줘",

    "보여주세요",
    "보여 주세요",
    "보여줘",
    "보여 줘",

    "관련 법률",
    "관련법률",
    "관련 법",
    "관련법",

    "법률 알려줘",
    "법 알려줘",

    "무엇이야",
    "뭐야",
    "뭔데",
]


# ============================================================
# 2. 검색 목적에 맞춘 의미 변환
#
# 단순 삭제하면 중요한 의미가 사라지는 표현은
# 검색에 적합한 법률 키워드로 변환한다.
# ============================================================

SEMANTIC_REPLACEMENTS = [

    # 장애인 고용 미이행 질문
    (
        r"장애인\s+고용\s+안\s*하면",
        "장애인 고용 의무"
    ),

    (
        r"장애인\s+고용하지\s+않으면",
        "장애인 고용 의무"
    ),

    (
        r"장애인을\s+고용하지\s+않으면",
        "장애인 고용 의무"
    ),

    (
        r"장애인을\s+고용\s+안\s*하면",
        "장애인 고용 의무"
    ),
]


# ============================================================
# 3. 조건형 어미
# ============================================================

CONDITION_PATTERNS = [

    r"\s+안\s+하면$",
    r"\s+안하면$",

    r"하면은$",
    r"하면$",

    r"되면은$",
    r"되면$",

    r"한다면$",
    r"된다면$",

    r"했을\s*때$",
    r"할\s*때$",

    r"인\s*경우$",
    r"경우$",
]


# ============================================================
# 4. 특수문자 제거
# ============================================================

def clean_symbols(text: str) -> str:

    text = re.sub(
        r"[?!？！]+",
        " ",
        text
    )

    text = re.sub(
        r"[,;:]+",
        " ",
        text
    )

    return text


# ============================================================
# 5. 의미 변환
# ============================================================

def apply_semantic_replacements(
    text: str
) -> str:

    for pattern, replacement in SEMANTIC_REPLACEMENTS:

        text = re.sub(
            pattern,
            replacement,
            text
        )

    return text


# ============================================================
# 6. 질문 표현 제거
# ============================================================

def remove_question_phrases(
    text: str
) -> str:

    phrases = sorted(
        QUESTION_PHRASES,
        key=len,
        reverse=True
    )

    for phrase in phrases:

        text = text.replace(
            phrase,
            " "
        )

    return text


# ============================================================
# 7. 조건형 어미 제거
# ============================================================

def remove_condition_endings(
    text: str
) -> str:

    text = text.strip()

    changed = True

    while changed:

        changed = False

        for pattern in CONDITION_PATTERNS:

            new_text = re.sub(
                pattern,
                "",
                text
            ).strip()

            if new_text != text:

                text = new_text
                changed = True

    return text


# ============================================================
# 8. 불필요한 표현 제거
# ============================================================

def remove_weak_words(
    text: str
) -> str:

    weak_words = {

        "관련",
        "대해서",
        "대해",
        "관해서",
        "관해",
    }

    tokens = text.split()

    cleaned_tokens = []

    for token in tokens:

        if token in weak_words:
            continue

        cleaned_tokens.append(
            token
        )

    return " ".join(
        cleaned_tokens
    )


# ============================================================
# 9. 조사 정리
#
# 검색어 마지막에 붙은
# 에 / 에서 / 은 / 는 / 을 / 를 등을 정리한다.
#
# 너무 공격적으로 모든 조사를 없애면
# 고유명사나 법률용어가 손상될 수 있으므로
# 마지막 토큰 위주로 제한한다.
# ============================================================

def clean_last_particle(
    text: str
) -> str:

    tokens = text.split()

    if not tokens:

        return ""


    last = tokens[-1]


    # 긴 조사부터 처리
    particles = [

        "에서는",
        "에게서",
        "으로는",

        "에서",
        "에게",
        "으로",

        "에는",
        "은",
        "는",
        "이",
        "가",
        "을",
        "를",
        "에",
    ]


    for particle in particles:

        if (
            last.endswith(particle)
            and len(last) > len(particle)
        ):

            last = last[
                :-len(particle)
            ]

            break


    tokens[-1] = last


    return " ".join(
        token
        for token in tokens
        if token
    )


# ============================================================
# 10. 문장 앞쪽의 의미 약한 상황 표현 정리
# ============================================================

def clean_context_prefix(
    text: str
) -> str:

    # 법률 검색에서는 "회사에서" 자체보다
    # 핵심 법률 개념이 더 중요하다.
    text = re.sub(
        r"^회사에서\s+",
        "",
        text
    )

    return text


# ============================================================
# 11. 공백 정리
# ============================================================

def normalize_spaces(
    text: str
) -> str:

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


# ============================================================
# 12. 최종 검색어 정규화
# ============================================================

def normalize_search_query(
    text: str
) -> str:

    if not text:

        return ""


    query = text.strip()


    # 1. 문장부호 제거
    query = clean_symbols(
        query
    )


    # 2. 의미 있는 표현 먼저 변환
    query = apply_semantic_replacements(
        query
    )


    # 3. 질문/요청 표현 제거
    query = remove_question_phrases(
        query
    )


    # 4. 공백 정리
    query = normalize_spaces(
        query
    )


    # 5. 조건형 종결어미 제거
    query = remove_condition_endings(
        query
    )


    # 6. 의미 약한 단어 제거
    query = remove_weak_words(
        query
    )


    # 7. 마지막 조사 정리
    query = clean_last_particle(
        query
    )


    # 8. 앞쪽 상황 표현 정리
    query = clean_context_prefix(
        query
    )


    # 9. 최종 공백 정리
    query = normalize_spaces(
        query
    )


    return query


# ============================================================
# 13. 테스트
# ============================================================

if __name__ == "__main__":

    test_questions = [

        "특허 침해하면 어떻게 돼?",

        "장애인 취업 관련 법 알려줘",

        "회사에서 장애인 고용 안 하면?",

        "특허 침해 관련 법률 알려주세요",

        "장애인 고용에 대해서 설명해줘",
    ]


    print()
    print("=" * 70)
    print("법률 검색어 정규화 테스트")
    print("=" * 70)


    for question in test_questions:

        normalized = normalize_search_query(
            question
        )

        print()
        print(
            "원문:",
            question
        )

        print(
            "검색어:",
            normalized
        )