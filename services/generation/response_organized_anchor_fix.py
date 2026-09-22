# ============================================================
# Python 기반 핵심 법률 답변 생성
#
# 핵심 원칙
#
# 1. LLM으로 법률 사실을 생성하지 않는다.
# 2. 공식 Evidence만 사용한다.
# 3. 특정 조문 질문은 공식 조문을 그대로 표시한다.
# 4. 자연어 질문은 OrganizedEvidence를 우선 사용한다.
# 5. 조문 내부 핵심 항 선택은 legal_statement_selector가 담당한다.
# 6. 사용자용 핵심 결론은 legal_conclusion_builder가 담당한다.
#
# 자연어 질문 답변 흐름
#
# 사용자용 핵심 결론
#   ↓
# 직접 근거
#   ↓
# 직접 미이행 효과
#   ↓
# 후속 불이익
#   ↓
# 조건부 별도 제재
#
# Organizer가 충분한 구조를 만들지 못한 경우에만
# aiSearch 결과를 fallback으로 사용한다.
# ============================================================

import re

from typing import (
    Any,
    Dict,
    List,
)


from services.generation.response_utils import (
    clean_text,
    make_article_label,
)

from services.evidence.organizer import (
    organize_evidence,
)

from services.generation.legal_statement_selector import (
    select_best_statement,
)

from services.generation.legal_conclusion_builder import (
    build_plain_conclusion,
)


# ============================================================
# 1. 설정
# ============================================================

CORE_LAW_LIMIT = 3

CORE_TEXT_LIMIT = 430


# ============================================================
# 2. Effect Category
# ============================================================

DIRECT_CONSEQUENCE = (
    "direct_consequence"
)

DOWNSTREAM_CONSEQUENCE = (
    "downstream_consequence"
)

CONDITIONAL_SANCTION = (
    "conditional_sanction"
)


# ============================================================
# 3. 질문 불용어
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
# 4. 일반적인 법적 효과 표현
# ============================================================

LEGAL_EFFECT_TERMS = (

    "의무",

    "하여야 한다",
    "해야 한다",

    "금지",
    "아니 된다",

    "부담금",

    "가산금",
    "연체금",

    "독촉",
    "체납처분",

    "과태료",

    "벌금",
    "징역",
    "처한다",

    "손해배상",
    "배상",

    "취소",
    "정지",

    "위반",
)


# ============================================================
# 5. 결과 질문 표현
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

    "책임",

    "문제",
)


# ============================================================
# 6. 텍스트 정규화
# ============================================================

def normalize_for_match(
    value: Any
) -> str:

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
# 7. 질문 토큰
# ============================================================

def extract_question_tokens(
    question: str
) -> List[str]:

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
# 8. 결과 질문 여부
# ============================================================

def is_consequence_question(
    question: str
) -> bool:

    question = normalize_for_match(
        question
    )


    return any(

        term in question

        for term in CONSEQUENCE_QUESTION_TERMS
    )


# ============================================================
# 9. 토큰 일치
# ============================================================

def count_token_matches(
    tokens: List[str],
    text: str
) -> int:

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
# 10. 법적 효과 표현 수
# ============================================================

def count_legal_effect_terms(
    text: str
) -> int:

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
# 11. Fallback용 조문 분리
# ============================================================

def split_legal_text(
    text: str
) -> List[str]:

    text = clean_text(
        text
    )


    if not text:

        return []


    text = re.sub(

        r"(?=[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳])",

        "\n",

        text,
    )


    parts = re.split(

        r"(?<=[.!?])\s+|\n+",

        text,
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
# 12. Fallback 문장 점수
# ============================================================

def score_statement(
    statement: str,
    question: str,
    title: str = ""
) -> float:

    statement = clean_text(
        statement
    )


    if not statement:

        return -1.0


    question_tokens = (
        extract_question_tokens(
            question
        )
    )


    title_tokens = (
        extract_question_tokens(
            title
        )
    )


    score = 0.0


    score += (

        count_token_matches(
            question_tokens,
            statement
        )

        *
        5.0
    )


    score += (

        count_token_matches(
            title_tokens,
            statement
        )

        *
        2.0
    )


    score += (

        count_legal_effect_terms(
            statement
        )

        *
        3.0
    )


    if is_consequence_question(
        question
    ):

        score += (

            count_legal_effect_terms(
                statement
            )

            *
            2.0
        )


    return score


# ============================================================
# 13. Fallback 핵심 문장
# ============================================================

def extract_core_statement(
    evidence: Dict[str, Any],
    question: str
) -> str:

    if not isinstance(
        evidence,
        dict
    ):

        return ""


    article_text = clean_text(

        evidence.get(
            "article_text"
        )

        or

        evidence.get(
            "full_text"
        )
    )


    title = clean_text(
        evidence.get(
            "article_title"
        )
    )


    if not article_text:

        return ""


    statements = split_legal_text(
        article_text
    )


    if not statements:

        result = article_text[
            :CORE_TEXT_LIMIT
        ]


        if len(
            article_text
        ) > CORE_TEXT_LIMIT:

            result = (
                result.rstrip()
                +
                "..."
            )


        return result


    scored = []


    for index, statement in enumerate(
        statements
    ):

        score = score_statement(

            statement=statement,

            question=question,

            title=title,
        )


        scored.append(
            (
                score,
                index,
                statement,
            )
        )


    scored.sort(

        key=lambda item: (

            -item[0],

            item[1],
        )
    )


    best = scored[
        0
    ][2]


    if len(
        best
    ) > CORE_TEXT_LIMIT:

        best = (

            best[
                :CORE_TEXT_LIMIT
            ].rstrip()

            +
            "..."
        )


    return best


# ============================================================
# 14. 특정 조문 질문
# ============================================================

def build_article_core_answer(
    article: dict
) -> str:

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
# 15. Organizer
# ============================================================

def get_organized_result(
    evidence_result: dict
) -> Dict[str, Any]:

    if not isinstance(
        evidence_result,
        dict
    ):

        return {}


    try:

        organized = organize_evidence(
            evidence_result
        )


        if organized is None:

            return {}


        if not hasattr(
            organized,
            "to_dict"
        ):

            return {}


        result = organized.to_dict()


        if isinstance(
            result,
            dict
        ):

            return result


    except Exception:

        return {}


    return {}


# ============================================================
# 16. Primary Law Name
# ============================================================

def get_primary_law_name(
    organized: dict
) -> str:

    primary_laws = organized.get(
        "primary_laws",
        []
    )


    if not isinstance(
        primary_laws,
        list
    ):

        return ""


    if not primary_laws:

        return ""


    first = primary_laws[
        0
    ]


    if not isinstance(
        first,
        dict
    ):

        return ""


    return clean_text(
        first.get(
            "law_name"
        )
    )


# ============================================================
# 17. Basis Evidence
# ============================================================

def get_basis_evidence(
    basis: dict
) -> Dict[str, Any]:

    if not isinstance(
        basis,
        dict
    ):

        return {}


    evidence = basis.get(
        "evidence"
    )


    if isinstance(
        evidence,
        dict
    ):

        return evidence


    return {}


# ============================================================
# 18. Basis Category
# ============================================================

def get_basis_category(
    basis: dict
) -> str:

    if not isinstance(
        basis,
        dict
    ):

        return ""


    return clean_text(

        basis.get(
            "effect_type"
        )

        or

        basis.get(
            "role"
        )
    )


# ============================================================
# 19. Basis Article Number
# ============================================================

def get_basis_article_number(
    basis: dict
) -> int:

    evidence = get_basis_evidence(
        basis
    )


    if not evidence:

        return 0


    try:

        return int(
            evidence.get(
                "article_number"
            )
            or
            0
        )

    except (
        TypeError,
        ValueError,
    ):

        return 0


# ============================================================
# 20. 직접 근거 조문번호
# ============================================================

def get_direct_basis_article_numbers(
    direct_basis: list
) -> List[int]:

    results = []


    if not isinstance(
        direct_basis,
        list
    ):

        return results


    for basis in direct_basis:

        if not isinstance(
            basis,
            dict
        ):

            continue


        article_number = (
            get_basis_article_number(
                basis
            )
        )


        if (
            article_number > 0
            and
            article_number not in results
        ):

            results.append(
                article_number
            )


    return results


# ============================================================
# 20. Heading
# ============================================================

def build_evidence_heading(
    evidence: dict
) -> str:

    if not isinstance(
        evidence,
        dict
    ):

        return ""


    law_name = clean_text(
        evidence.get(
            "law_name"
        )
    )


    article_label = make_article_label(

        evidence.get(
            "article_number"
        ),

        evidence.get(
            "sub_article_number",
            0
        ),
    )


    article_title = clean_text(
        evidence.get(
            "article_title"
        )
    )


    heading = " ".join(

        item

        for item in (
            law_name,
            article_label,
        )

        if item
    )


    if article_title:

        if heading:

            heading += (
                f" ({article_title})"
            )

        else:

            heading = article_title


    return heading


# ============================================================
# 21. Consequence Category 분리
# ============================================================

def split_consequence_basis(
    consequence_basis: list
) -> Dict[
    str,
    List[dict]
]:

    results = {

        DIRECT_CONSEQUENCE:
            [],

        DOWNSTREAM_CONSEQUENCE:
            [],

        CONDITIONAL_SANCTION:
            [],
    }


    if not isinstance(
        consequence_basis,
        list
    ):

        return results


    for basis in consequence_basis:

        if not isinstance(
            basis,
            dict
        ):

            continue


        category = get_basis_category(
            basis
        )


        if category in results:

            results[
                category
            ].append(
                basis
            )


    return results


# ============================================================
# 22. 직접 Effect 조문번호
# ============================================================

def get_direct_consequence_article_numbers(
    consequence_basis: list
) -> List[int]:

    results = []


    if not isinstance(
        consequence_basis,
        list
    ):

        return results


    for basis in consequence_basis:

        if get_basis_category(
            basis
        ) != DIRECT_CONSEQUENCE:

            continue


        article_number = (
            get_basis_article_number(
                basis
            )
        )


        if (
            article_number > 0
            and
            article_number not in results
        ):

            results.append(
                article_number
            )


    return results


# ============================================================
# 23. Basis 핵심 항 선택
# ============================================================

def select_basis_statement(
    evidence: dict,
    question: str,
    effect_category: str = "",
    related_article_numbers: List[int] = None
) -> str:

    if not isinstance(
        evidence,
        dict
    ):

        return ""


    if effect_category in {

        DIRECT_CONSEQUENCE,

        DOWNSTREAM_CONSEQUENCE,

        CONDITIONAL_SANCTION,

    }:

        try:

            selected = select_best_statement(

                article=evidence,

                question=question,

                effect_category=effect_category,

                related_article_numbers=(
                    related_article_numbers
                    or
                    []
                ),
            )


            if selected:

                return selected


        except Exception:

            pass


    return extract_core_statement(

        evidence=evidence,

        question=question,
    )


# ============================================================
# 24. Basis 출력
# ============================================================

def build_basis_lines(
    basis_items: list,
    question: str,
    effect_category: str = "",
    related_article_numbers: List[int] = None
) -> List[str]:

    lines = []


    if not isinstance(
        basis_items,
        list
    ):

        return lines


    for basis in basis_items:

        if not isinstance(
            basis,
            dict
        ):

            continue


        evidence = get_basis_evidence(
            basis
        )


        if not evidence:

            continue


        heading = build_evidence_heading(
            evidence
        )


        statement = select_basis_statement(

            evidence=evidence,

            question=question,

            effect_category=effect_category,

            related_article_numbers=(
                related_article_numbers
                or
                []
            ),
        )


        if heading:

            lines.append(
                f"- **{heading}**"
            )


        if statement:

            lines.append(
                f"  - {statement}"
            )


    return lines


# ============================================================
# 25. OrganizedEvidence 기반 답변
# ============================================================

def build_organized_core_answer(
    organized: dict,
    question: str
) -> str:

    if not isinstance(
        organized,
        dict
    ):

        return ""


    if not organized.get(
        "primary_law_confirmed"
    ):

        return ""


    direct_basis = organized.get(
        "direct_basis",
        []
    ) or []


    consequence_basis = organized.get(
        "consequence_basis",
        []
    ) or []


    if (
        not direct_basis
        and
        not consequence_basis
    ):

        return ""


    categorized = split_consequence_basis(
        consequence_basis
    )


    direct_effects = categorized.get(
        DIRECT_CONSEQUENCE,
        []
    )


    downstream = categorized.get(
        DOWNSTREAM_CONSEQUENCE,
        []
    )


    sanctions = categorized.get(
        CONDITIONAL_SANCTION,
        []
    )


    direct_effect_article_numbers = (
        get_direct_consequence_article_numbers(
            consequence_basis
        )
    )


    direct_basis_article_numbers = (
        get_direct_basis_article_numbers(
            direct_basis
        )
    )


    primary_law_name = (
        get_primary_law_name(
            organized
        )
    )


    # ========================================================
    # 새 사용자용 결론 Builder
    # ========================================================

    plain_conclusion = ""


    try:

        plain_conclusion = build_plain_conclusion(

            organized=organized,

            question=question,
        )

    except Exception:

        plain_conclusion = ""


    lines = []


    # ========================================================
    # 결론
    # ========================================================

    lines.append(
        "### 결론"
    )


    if plain_conclusion:

        lines.append(
            plain_conclusion
        )


    if primary_law_name:

        lines.append(
            ""
        )


        lines.append(
            (
                "현재 공식 근거에서 확인된 주 법령은 "
                f"**{primary_law_name}**입니다."
            )
        )


    # ========================================================
    # 직접 근거
    # ========================================================

    if direct_basis:

        lines.append(
            ""
        )


        lines.append(
            "### 1. 질문에 직접 적용되는 근거"
        )


        lines.extend(
            build_basis_lines(

                basis_items=direct_basis,

                question=question,
            )
        )


    # ========================================================
    # 직접 효과
    # ========================================================

    if direct_effects:

        lines.append(
            ""
        )


        lines.append(
            "### 2. 의무를 충족하지 않았을 때의 직접 효과"
        )


        lines.extend(
            build_basis_lines(

                basis_items=direct_effects,

                question=question,

                effect_category=(
                    DIRECT_CONSEQUENCE
                ),

                related_article_numbers=(
                    direct_basis_article_numbers
                ),
            )
        )


    # ========================================================
    # 후속 불이익
    # ========================================================

    if downstream:

        lines.append(
            ""
        )


        lines.append(
            "### 3. 이후 이어질 수 있는 후속 불이익"
        )


        lines.extend(
            build_basis_lines(

                basis_items=downstream,

                question=question,

                effect_category=(
                    DOWNSTREAM_CONSEQUENCE
                ),

                related_article_numbers=(
                    direct_effect_article_numbers
                ),
            )
        )


    # ========================================================
    # 조건부 별도 제재
    # ========================================================

    if sanctions:

        lines.append(
            ""
        )


        lines.append(
            "### 4. 별도 위반이 있을 때 적용될 수 있는 제재"
        )


        lines.append(
            (
                "아래 제재 조항은 질문에 나온 행위 자체와 "
                "자동으로 동일시하지 않습니다. "
                "해당 조문이 정한 별도의 위반 요건을 "
                "충족하는지 따로 확인해야 합니다."
            )
        )


        lines.extend(
            build_basis_lines(

                basis_items=sanctions,

                question=question,

                effect_category=(
                    CONDITIONAL_SANCTION
                ),

                related_article_numbers=(
                    direct_effect_article_numbers
                ),
            )
        )


    # ========================================================
    # 적용조건 안내
    # ========================================================

    lines.append(
        ""
    )


    lines.append(
        "### 적용할 때 확인할 점"
    )


    lines.append(
        (
            "실제 적용 여부와 범위는 각 조문에 적힌 "
            "적용 대상, 인원 기준, 예외, 신고·납부 등 "
            "세부 요건에 따라 달라질 수 있습니다."
        )
    )


    return "\n".join(
        lines
    ).strip()


# ============================================================
# 26. Fallback Law 점수
# ============================================================

def score_law_item(
    item: dict,
    question: str
) -> float:

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


    score = 0.0


    score += (

        count_token_matches(
            tokens,
            law_name
        )

        *
        3.0
    )


    score += (

        count_token_matches(
            tokens,
            title
        )

        *
        9.0
    )


    score += (

        count_token_matches(
            tokens,
            article_text
        )

        *
        2.5
    )


    if is_consequence_question(
        question
    ):

        score += (

            count_legal_effect_terms(
                title
            )

            *
            5.0
        )


    return score


# ============================================================
# 27. Fallback Laws 선택
# ============================================================

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

        key=lambda item: (

            -item[0],

            item[1],
        )
    )


    return [

        item

        for _, _, item in candidates[
            :limit
        ]
    ]


# ============================================================
# 28. Fallback 답변
# ============================================================

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


# ============================================================
# 29. Public Entry Point
# ============================================================

def build_core_answer(
    evidence_result: dict
) -> str:

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
    # A. 특정 조문 질문
    # ========================================================

    article = evidence_result.get(
        "article"
    )


    if article:

        answer = build_article_core_answer(
            article
        )


        if answer:

            return answer


    # ========================================================
    # B. 자연어 질문
    # ========================================================

    organized = get_organized_result(
        evidence_result
    )


    if organized:

        answer = build_organized_core_answer(

            organized=organized,

            question=question,
        )


        if answer:

            return answer


    # ========================================================
    # C. aiSearch Fallback
    # ========================================================

    laws = evidence_result.get(
        "laws",
        []
    )


    if laws:

        return build_laws_core_answer(

            laws=laws,

            question=question,
        )


    # ========================================================
    # D. 기타 공식 자료
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
            "관련 판례 또는 법령해석례가 확인되었습니다. "
            "현재 법령 Evidence만으로 직접적인 결론을 "
            "구성하기 어려워 해당 공식 자료를 함께 "
            "확인해야 합니다."
        )


    if library_items:

        return (
            "관련 국회도서관 참고자료가 확인되었습니다. "
            "이 자료는 직접적인 법적 근거가 아니라 "
            "연구·입법 배경 참고자료입니다."
        )


    return ""