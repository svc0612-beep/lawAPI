# ============================================================
# Python 기반 핵심 법률 답변 생성
#
# 중요:
# - LLM으로 법률 사실을 생성하지 않는다.
# - Evidence에 포함된 공식 조문만 사용한다.
# - 사용자의 질문과 직접 관련된 핵심 근거를 우선한다.
# - 답변 카드에는 핵심만 표시한다.
# - 전체 Evidence는 별도 탭에서 그대로 확인한다.
# ============================================================

import re

from services.generation.response_utils import (
    clean_text,
    make_article_label,
)


# ============================================================
# 1. 핵심 답변 설정
# ============================================================

CORE_LAW_LIMIT = 3

CORE_TEXT_LIMIT = 340


# ============================================================
# 2. 질문 분석용 일반 불용어
#
# 특정 법률 분야에 종속되지 않는 표현만 둔다.
# ============================================================

STOP_WORDS = {

    "관련",
    "대한",
    "대해",
    "대해서",
    "알려줘",
    "알려",
    "뭐야",
    "무엇",
    "어떻게",
    "어떻게돼",
    "어떻게되",
    "하면",
    "하는",
    "회사에서",
    "회사",
    "경우",
    "있어",
    "있나요",
    "되는",
    "되나요",
}


# ============================================================
# 3. 법적 효과를 나타내는 일반 표현
#
# 특정 법률명을 하드코딩하는 것이 아니라
# 법률 조문에서 일반적으로 중요한 효과를 찾기 위한 표현.
# ============================================================

LEGAL_EFFECT_TERMS = (

    "의무",
    "하여야 한다",
    "해야 한다",

    "금지",
    "아니 된다",

    "부담금",
    "과태료",

    "벌금",
    "징역",
    "처한다",

    "처벌",

    "손해배상",
    "배상",

    "청구할 수 있다",
    "청구",

    "취소",
    "정지",

    "제재",

    "위반",

    "추정한다",

    "고용하여야",
)


# ============================================================
# 4. 질문이 결과/위반 효과를 묻는지 확인
# ============================================================

CONSEQUENCE_QUESTION_TERMS = (

    "안 하면",
    "안하면",
    "위반",
    "처벌",
    "벌금",
    "과태료",
    "어떻게 돼",
    "어떻게돼",
    "어떻게 되",
    "문제",
    "책임",
)


# ============================================================
# 5. 검색용 텍스트 정규화
# ============================================================

def normalize_for_match(
    value
):

    text = clean_text(
        value
    ).lower()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# 6. 질문 핵심 토큰 추출
# ============================================================

def extract_question_tokens(
    question: str
):

    question = normalize_for_match(
        question
    )

    if not question:

        return []


    raw_tokens = re.findall(
        r"[가-힣A-Za-z0-9]+",
        question
    )


    results = []


    for token in raw_tokens:

        token = token.strip()


        if len(
            token
        ) < 2:

            continue


        if token in STOP_WORDS:

            continue


        if token not in results:

            results.append(
                token
            )


    return results


# ============================================================
# 7. 결과/제재 질문 여부
# ============================================================

def is_consequence_question(
    question: str
):

    question = normalize_for_match(
        question
    )


    return any(

        term in question

        for term in CONSEQUENCE_QUESTION_TERMS
    )


# ============================================================
# 8. 법적 효과 표현 개수
# ============================================================

def count_legal_effect_terms(
    text: str
):

    text = normalize_for_match(
        text
    )


    if not text:

        return 0


    return sum(

        1

        for term in LEGAL_EFFECT_TERMS

        if term in text
    )


# ============================================================
# 9. 질문 토큰 일치 개수
# ============================================================

def count_token_matches(
    tokens: list,
    text: str
):

    text = normalize_for_match(
        text
    )


    if not text:

        return 0


    return sum(

        1

        for token in tokens

        if token in text
    )


# ============================================================
# 10. 관련 법령 1건 점수 계산
#
# 원래 검색 relevance_score도 사용하지만
# 질문과 조문 제목의 직접 일치를 더 중요하게 본다.
# ============================================================

def score_law_item(
    item: dict,
    question: str
):

    if not isinstance(
        item,
        dict
    ):

        return -1.0


    tokens = extract_question_tokens(
        question
    )


    law_name = clean_text(
        item.get(
            "law_name"
        )
    )


    title = clean_text(
        item.get(
            "article_title"
        )
    )


    article_text = clean_text(
        item.get(
            "article_text"
        )
    )


    original_score = item.get(
        "relevance_score",
        0
    )


    try:

        original_score = float(
            original_score
            or 0
        )

    except (
        TypeError,
        ValueError
    ):

        original_score = 0.0


    score = 0.0


    # ========================================================
    # 기존 검색 점수
    #
    # 그대로 버리지는 않되 영향력을 낮춘다.
    # ========================================================

    score += (
        original_score
        * 0.4
    )


    # ========================================================
    # 질문 ↔ 법령명
    # ========================================================

    score += (
        count_token_matches(
            tokens,
            law_name
        )
        * 3.0
    )


    # ========================================================
    # 질문 ↔ 조문 제목
    #
    # 제목이 질문을 직접 설명하는 경우가 많기 때문에
    # 가장 높은 가중치를 준다.
    # ========================================================

    score += (
        count_token_matches(
            tokens,
            title
        )
        * 9.0
    )


    # ========================================================
    # 질문 ↔ 조문 내용
    # ========================================================

    score += (
        count_token_matches(
            tokens,
            article_text
        )
        * 2.5
    )


    # ========================================================
    # 사용자가 "안 하면?", "어떻게 돼?"처럼
    # 법적 결과를 묻는 경우
    #
    # 의무 / 부담금 / 처벌 / 벌금 / 청구 등
    # 실제 법적 효과가 있는 조문을 우선한다.
    # ========================================================

    if is_consequence_question(
        question
    ):

        title_effect_count = (
            count_legal_effect_terms(
                title
            )
        )


        text_effect_count = (
            count_legal_effect_terms(
                article_text
            )
        )


        score += (
            title_effect_count
            * 7.0
        )


        score += (
            min(
                text_effect_count,
                4
            )
            * 2.0
        )


    return score


# ============================================================
# 11. 핵심 관련 법령 선택
# ============================================================

def select_core_laws(
    laws: list,
    question: str,
    limit: int = CORE_LAW_LIMIT
):

    if not isinstance(
        laws,
        list
    ):

        return []


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
            question=question
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


# ============================================================
# 12. 법률 조문을 의미 단위로 분리
#
# 공식 조문을 요약해서 새 사실을 만드는 대신
# 실제 조문에서 가장 관련된 문장을 추출한다.
# ============================================================

def split_legal_text(
    text: str
):

    text = clean_text(
        text
    )


    if not text:

        return []


    # --------------------------------------------------------
    # 문단 기호 앞에서 구분
    # --------------------------------------------------------

    text = re.sub(
        r"(?=[②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳])",
        "\n",
        text
    )


    # --------------------------------------------------------
    # 일반 문장 종료 지점
    # --------------------------------------------------------

    parts = re.split(
        r"(?<=[.!?])\s+|\n+",
        text
    )


    results = []


    for part in parts:

        part = clean_text(
            part
        )


        if not part:

            continue


        if part not in results:

            results.append(
                part
            )


    return results


# ============================================================
# 13. 조문 내부 핵심 문장 점수
# ============================================================

def score_legal_statement(
    statement: str,
    question: str,
    title: str = ""
):

    statement = clean_text(
        statement
    )


    if not statement:

        return -1.0


    tokens = extract_question_tokens(
        question
    )


    score = 0.0


    # 질문 단어가 직접 포함된 문장
    score += (
        count_token_matches(
            tokens,
            statement
        )
        * 5.0
    )


    # 법적 효과가 명시된 문장
    score += (
        count_legal_effect_terms(
            statement
        )
        * 3.0
    )


    # 결과를 묻는 질문이라면
    # 효과 문장을 한 번 더 우선
    if is_consequence_question(
        question
    ):

        score += (
            count_legal_effect_terms(
                statement
            )
            * 3.0
        )


    # 조문 제목의 주요 표현이 본문에도 있으면 가산
    title_tokens = extract_question_tokens(
        title
    )


    score += (
        count_token_matches(
            title_tokens,
            statement
        )
        * 1.5
    )


    return score


# ============================================================
# 14. 조문에서 질문과 가장 관련된 공식 문장 추출
# ============================================================

def extract_core_statement(
    item: dict,
    question: str
):

    if not isinstance(
        item,
        dict
    ):

        return ""


    article_text = clean_text(
        item.get(
            "article_text"
        )
    )


    title = clean_text(
        item.get(
            "article_title"
        )
    )


    if not article_text:

        return ""


    statements = split_legal_text(
        article_text
    )


    if not statements:

        return article_text[
            :CORE_TEXT_LIMIT
        ]


    scored = []


    for index, statement in enumerate(
        statements
    ):

        score = score_legal_statement(

            statement=statement,

            question=question,

            title=title
        )


        scored.append(
            (
                score,
                index,
                statement,
            )
        )


    scored.sort(

        key=lambda value: (
            -value[0],
            value[1],
        )
    )


    best_statement = scored[
        0
    ][2]


    if len(
        best_statement
    ) > CORE_TEXT_LIMIT:

        best_statement = (
            best_statement[
                :CORE_TEXT_LIMIT
            ].rstrip()
            + "..."
        )


    return best_statement


# ============================================================
# 15. 특정 조문 핵심 답변
# ============================================================

def build_article_core_answer(
    article: dict
):

    if not isinstance(
        article,
        dict
    ):

        return ""


    law_name = clean_text(
        article.get(
            "law_name"
        )
    )


    article_label = clean_text(
        article.get(
            "article"
        )
    )


    specific_paragraph = clean_text(
        article.get(
            "specific_paragraph"
        )
    )


    full_article_text = clean_text(
        article.get(
            "full_article_text"
        )
    )


    lines = []


    if specific_paragraph:

        if law_name or article_label:

            lines.append(
                (
                    f"**{law_name} "
                    f"{article_label}에서 확인되는 내용입니다.**"
                ).strip()
            )


        lines.append(
            specific_paragraph
        )


        return "\n\n".join(
            lines
        )


    if full_article_text:

        if law_name or article_label:

            lines.append(
                (
                    f"**{law_name} "
                    f"{article_label}의 공식 조문입니다.**"
                ).strip()
            )


        lines.append(
            full_article_text
        )


    return "\n\n".join(
        lines
    )


# ============================================================
# 16. 관련 법령 기반 핵심 답변
#
# 이전:
# - 검색된 법령 전체 출력
#
# 현재:
# - 질문과 직접 관련된 상위 근거만 선택
# - 공식 조문에서 핵심 문장만 추출
# - 나머지 Evidence는 UI 탭에서 확인
# ============================================================

def build_laws_core_answer(
    laws: list,
    question: str = ""
):

    if not isinstance(
        laws,
        list
    ) or not laws:

        return ""


    selected_laws = select_core_laws(

        laws=laws,

        question=question,

        limit=CORE_LAW_LIMIT
    )


    if not selected_laws:

        return ""


    lines = [

        "**질문에 직접 관련된 핵심 내용은 다음과 같습니다.**",
    ]


    for item in selected_laws:

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
                "sub_article_number"
            )
        )


        title = clean_text(
            item.get(
                "article_title"
            )
        )


        statement = extract_core_statement(

            item=item,

            question=question
        )


        heading_parts = [

            law_name,

            article_label,
        ]


        heading = " ".join(

            value

            for value in heading_parts

            if value
        )


        if title:

            heading += (
                f" ({title})"
            )


        if statement:

            lines.append(
                (
                    f"- **{heading}**  \n"
                    f"  {statement}"
                )
            )


        else:

            lines.append(
                f"- **{heading}**"
            )


    lines.append(
        ""
    )


    lines.append(
        (
            "위 내용은 검색된 공식 법령 중 "
            "질문과 직접 관련성이 높은 근거를 우선해서 표시한 것입니다. "
            "전체 법령 근거는 아래 법령 탭에서 확인할 수 있습니다."
        )
    )


    return "\n".join(
        lines
    ).strip()


# ============================================================
# 17. Python 핵심 답변 생성
# ============================================================

def build_core_answer(
    evidence_result: dict
):

    if not isinstance(
        evidence_result,
        dict
    ):

        return ""


    question = clean_text(

        evidence_result.get(
            "original_question"
        )
    )


    # ========================================================
    # 특정 조문 질문
    # ========================================================

    article = evidence_result.get(
        "article"
    )


    if article:

        return build_article_core_answer(
            article
        )


    # ========================================================
    # 관련 법령 질문
    # ========================================================

    laws = evidence_result.get(
        "laws",
        []
    )


    if laws:

        return build_laws_core_answer(

            laws=laws,

            question=question
        )


    # ========================================================
    # 법령은 없지만 기타 공식 근거 존재
    # ========================================================

    interpretations = evidence_result.get(
        "interpretations",
        []
    )


    precedents = evidence_result.get(
        "precedents",
        []
    )


    library_items = evidence_result.get(
        "library_items",
        []
    )


    if interpretations or precedents:

        return (
            "관련 공식 자료가 확인되었습니다. "
            "아래 판례 또는 법령해석례에서 확인할 수 있습니다."
        )


    if library_items:

        return (
            "관련 국회도서관 참고자료가 확인되었습니다. "
            "이 자료는 법령이나 판례와 같은 직접적인 법적 근거가 아니라 "
            "연구·배경 참고자료입니다."
        )


    return ""