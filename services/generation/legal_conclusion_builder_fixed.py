# ============================================================
# Legal Conclusion Builder
#
# OrganizedEvidence의 공식 조문을 이용해
# 사용자가 가장 먼저 읽을 짧은 결론을 만든다.
#
# 원칙
#
# - 특정 법률명 하드코딩 금지
# - 특정 조문번호 하드코딩 금지
# - 특정 숫자 하드코딩 금지
# - LLM 사용 금지
# - Evidence에 없는 법률 사실 생성 금지
# ============================================================

import re

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)


from services.generation.legal_statement_selector import (
    select_best_statement,
)

from services.evidence.legal_reference_parser import (
    extract_legal_references,
)


# ============================================================
# 1. Category
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
# 2. 텍스트 정리
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
# 3. 개정 이력 제거
# ============================================================

def remove_revision_note(
    text: str
) -> str:

    text = clean_text(
        text
    )


    text = re.sub(

        r"\s*<[^>]*(?:개정|신설|전문개정|삭제)[^>]*>\s*",

        "",

        text,
    )


    return clean_text(
        text
    )


# ============================================================
# 4. 항 번호 제거
# ============================================================

def remove_paragraph_marker(
    text: str
) -> str:

    return re.sub(

        r"^[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]\s*",

        "",

        clean_text(
            text
        ),
    ).strip()


# ============================================================
# 5. 사용자 표시용 정리
# ============================================================

def normalize_statement(
    text: str
) -> str:

    text = remove_revision_note(
        text
    )


    text = remove_paragraph_marker(
        text
    )


    return clean_text(
        text
    )


# ============================================================
# 6. 괄호 내부 세부설명 제거
#
# 짧은 결론에서 지나치게 긴 예외·정의 설명을 줄이기 위함.
#
# 원본 Evidence 자체는 변경하지 않는다.
# ============================================================

def remove_parenthetical_details(
    text: str
) -> str:

    text = clean_text(
        text
    )


    previous = None


    while (
        previous != text
    ):

        previous = text


        text = re.sub(
            r"\([^()]*\)",
            "",
            text
        )


    return clean_text(
        text
    )


# ============================================================
# 7. 문장 종결
# ============================================================

def ensure_sentence_end(
    text: str
) -> str:

    text = clean_text(
        text
    )


    if not text:

        return ""


    if text.endswith(
        (
            ".",
            "다.",
            "요.",
        )
    ):

        return text


    return (
        text
        +
        "."
    )


# ============================================================
# 8. Basis Evidence
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
# 9. Basis Category
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
# 10. 조문번호
# ============================================================

def get_article_number(
    basis: dict
) -> int:

    evidence = get_basis_evidence(
        basis
    )


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
# 11. Consequence Category 분리
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
# 12. 직접 효과 조문번호
# ============================================================

def get_direct_effect_article_numbers(
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


        number = get_article_number(
            basis
        )


        if (
            number > 0
            and
            number not in results
        ):

            results.append(
                number
            )


    return results


# ============================================================
# 13. Basis 핵심 문장
# ============================================================

def select_basis_statement(
    basis: dict,
    question: str,
    effect_category: str = "",
    related_article_numbers: Optional[
        List[int]
    ] = None
) -> str:

    evidence = get_basis_evidence(
        basis
    )


    if not evidence:

        return ""


    try:

        statement = select_best_statement(

            article=evidence,

            question=question,

            effect_category=effect_category,

            related_article_numbers=(
                related_article_numbers
                or
                []
            ),
        )

    except Exception:

        statement = ""


    return normalize_statement(
        statement
    )


# ============================================================
# 14. 숫자 조건 추출
#
# 중복되는:
#
# 상시 50명 이상
# 50명 이상
#
# 을 동시에 반환하지 않는다.
# ============================================================

def extract_numeric_conditions(
    text: str
) -> List[str]:

    text = clean_text(
        text
    )


    if not text:

        return []


    patterns = [

        r"상시\s*\d+\s*명(?:의\s*근로자를\s*고용하는\s*사업주)?\s*이상",

        r"상시\s*\d+\s*명\s*미만",

        r"\d+\s*명\s*이상",

        r"\d+\s*명\s*미만",

        r"\d+\s*일\s*이내",

        r"\d+\s*개월\s*이내",

        r"\d+\s*년\s*이내",
    ]


    matches: List[
        Tuple[
            int,
            int,
            str,
        ]
    ] = []


    for pattern in patterns:

        for match in re.finditer(
            pattern,
            text
        ):

            value = clean_text(
                match.group(
                    0
                )
            )


            matches.append(
                (
                    match.start(),
                    match.end(),
                    value,
                )
            )


    # 긴 범위 우선
    matches.sort(

        key=lambda item: (

            item[0],

            -(
                item[1]
                -
                item[0]
            ),
        )
    )


    selected = []


    selected_ranges = []


    for start, end, value in matches:

        overlap = False


        for selected_start, selected_end in selected_ranges:

            if (
                start >= selected_start
                and
                end <= selected_end
            ):

                overlap = True

                break


        if overlap:

            continue


        if value not in selected:

            selected.append(
                value
            )


            selected_ranges.append(
                (
                    start,
                    end,
                )
            )


    return selected


# ============================================================
# 15. 제외/예외 구절
# ============================================================

def extract_exclusion_clause(
    text: str
) -> str:

    text = clean_text(
        text
    )


    if not text:

        return ""


    parentheses = re.findall(
        r"\(([^()]*)\)",
        text
    )


    for value in parentheses:

        value = clean_text(
            value
        )


        if any(

            term in value

            for term in (

                "제외한다",

                "제외된다",

                "적용하지 아니한다",

                "적용하지 않는다",

                "면제",
            )
        ):

            return value


    match = re.search(

        r"([^.!?]*(?:제외한다|제외된다|적용하지 아니한다|적용하지 않는다|면제한다)[^.!?]*)",

        text,
    )


    if match:

        return clean_text(
            match.group(
                1
            )
        )


    return ""


# ============================================================
# 16. 법률 의무 문장의 핵심 앞부분
#
# "상시 50명 이상의 근로자를 고용하는 사업주"
# 같은 적용대상 부분을 보존한다.
# ============================================================

def extract_actor_clause(
    text: str
) -> str:

    text = clean_text(
        text
    )


    actor_terms = (

        "사업주는",

        "사업자는",

        "사용자는",

        "근로자는",

        "법인은",

        "기관은",

        "국가와 지방자치단체의 장은",
    )


    for term in actor_terms:

        index = text.find(
            term
        )


        if index >= 0:

            return clean_text(
                text[
                    :index
                    +
                    len(
                        term
                    )
                ]
            )


    return ""


# ============================================================
# 17. 법적 의무 부분 추출
# ============================================================

def extract_norm_clause(
    text: str
) -> str:

    text = clean_text(
        text
    )


    patterns = (

        r"([^.!?]{0,220}하여야 한다)",

        r"([^.!?]{0,220}해야 한다)",

        r"([^.!?]{0,220}아니 된다)",
    )


    for pattern in patterns:

        match = re.search(
            pattern,
            text
        )


        if match:

            return clean_text(
                match.group(
                    1
                )
            )


    return ""


# ============================================================
# 18. 직접 의무 요약
# ============================================================

def build_direct_duty_summary(
    statement: str
) -> str:

    statement = clean_text(
        statement
    )


    if not statement:

        return ""


    # ========================================================
    # 긴 괄호 설명 제거
    # ========================================================

    compact = remove_parenthetical_details(
        statement
    )


    actor_clause = extract_actor_clause(
        compact
    )


    norm_clause = extract_norm_clause(
        compact
    )


    # ========================================================
    # Actor와 Norm이 자연스럽게 이어지는 경우
    # compact 자체를 우선한다.
    # ========================================================

    if (
        compact
        and
        len(
            compact
        ) <= 320
    ):

        return ensure_sentence_end(
            compact
        )


    # ========================================================
    # 매우 긴 조문이면
    # 적용 대상 + 의무 부분 조합
    # ========================================================

    parts = []


    if actor_clause:

        parts.append(
            actor_clause
        )


    if norm_clause:

        # Actor 부분이 norm_clause 안에 이미 있으면 중복 방지
        if (
            not actor_clause
            or
            actor_clause not in norm_clause
        ):

            parts.append(
                norm_clause
            )


    if parts:

        return ensure_sentence_end(
            " ".join(
                parts
            )
        )


    # ========================================================
    # 최후 fallback
    # ========================================================

    numeric_conditions = (
        extract_numeric_conditions(
            statement
        )
    )


    if numeric_conditions:

        return (
            "적용 기준으로 "
            +
            ", ".join(
                numeric_conditions[
                    :2
                ]
            )
            +
            "이 확인됩니다."
        )


    return ensure_sentence_end(
        statement[
            :260
        ]
    )


# ============================================================
# 18-1. 직접 근거의 표시 라벨
#
# "하여야 한다 / 아니 된다"처럼 의무 규범이면 "의무",
# 권리·청구권·허용 규정이면 "직접 근거"로 표시한다.
# 특정 법률명/조문번호는 사용하지 않는다.
# ============================================================

def get_direct_basis_label(
    statement: str
) -> str:

    statement = clean_text(
        statement
    )

    if not statement:
        return "직접 근거"

    obligation_terms = (
        "하여야 한다",
        "해야 한다",
        "아니 된다",
        "하여서는 아니 된다",
        "해서는 아니 된다",
    )

    if any(
        term in statement
        for term in obligation_terms
    ):
        return "의무"

    return "직접 근거"


# ============================================================
# 19. 직접 효과 요약
# ============================================================

def build_direct_effect_summary(
    statement: str
) -> str:

    statement = clean_text(
        statement
    )


    if not statement:

        return ""


    exclusion = extract_exclusion_clause(
        statement
    )


    # ========================================================
    # 괄호 속 예외를 제거해 본문을 간단히 만든다.
    # ========================================================

    compact = remove_parenthetical_details(
        statement
    )


    main = compact


    if len(
        main
    ) > 280:

        norm = extract_norm_clause(
            main
        )


        if norm:

            main = norm


    lines = []


    if main:

        lines.append(
            ensure_sentence_end(
                main
            )
        )


    if exclusion:

        exclusion = clean_text(
            exclusion
        )


        if exclusion.endswith(
            "."
        ):

            exclusion = exclusion[
                :-1
            ]


        lines.append(
            (
                "다만 "
                +
                exclusion
                +
                "."
            )
        )


    return " ".join(
        lines
    )


# ============================================================
# 20. 조문 제목
# ============================================================

def get_basis_title(
    basis: dict
) -> str:

    evidence = get_basis_evidence(
        basis
    )


    return clean_text(
        evidence.get(
            "article_title"
        )
    )


# ============================================================
# 21. 후속 효과 요약
# ============================================================

def build_downstream_summary(
    downstream_basis: list
) -> str:

    titles = []


    for basis in downstream_basis:

        title = get_basis_title(
            basis
        )


        if (
            title
            and
            title not in titles
        ):

            titles.append(
                title
            )


    if not titles:

        return ""


    return (
        ", ".join(
            titles
        )
        +
        " 관련 규정이 확인됩니다."
    )


# ============================================================
# 22. 참조 조문번호 추출
# ============================================================

def get_reference_article_numbers(
    text: str
) -> List[int]:

    results = []


    references = extract_legal_references(
        text=text
    )


    for reference in references:

        try:

            number = int(
                reference.get(
                    "article_number"
                )
                or
                0
            )

        except (
            TypeError,
            ValueError,
        ):

            number = 0


        if (
            number > 0
            and
            number not in results
        ):

            results.append(
                number
            )


    return results


# ============================================================
# 23. 제재 조문의 호 분리
#
# 예:
#
# ... 과태료를 부과한다.
# 1. 제33조제5항 ...
# 2. 제76조제1항 ...
# ============================================================

def split_numbered_items(
    text: str
) -> Tuple[
    str,
    List[str]
]:

    text = clean_text(
        text
    )


    if not text:

        return "", []


    matches = list(
        re.finditer(
            r"(?<!\d)(\d+)\.\s*",
            text
        )
    )


    if not matches:

        return text, []


    prefix = clean_text(
        text[
            :matches[0].start()
        ]
    )


    items = []


    for index, match in enumerate(
        matches
    ):

        start = match.end()


        if (
            index
            +
            1
            <
            len(
                matches
            )
        ):

            end = matches[
                index
                +
                1
            ].start()

        else:

            end = len(
                text
            )


        body = clean_text(
            text[
                start:end
            ]
        )


        if body:

            items.append(
                body
            )


    return (
        prefix,
        items,
    )


# ============================================================
# 24. 직접 효과 조문을 참조하는 제재 호만 선택
# ============================================================

def select_relevant_sanction_item(
    statement: str,
    related_article_numbers: List[int]
) -> str:

    statement = clean_text(
        statement
    )


    if not statement:

        return ""


    prefix, items = split_numbered_items(
        statement
    )


    if not items:

        return statement


    targets = set(
        related_article_numbers
    )


    # ========================================================
    # 앞 단계 직접 효과 조문을 참조하는 호 우선
    # ========================================================

    for item in items:

        references = set(
            get_reference_article_numbers(
                item
            )
        )


        if (
            targets
            and
            references
            &
            targets
        ):

            if prefix:

                return (
                    prefix
                    +
                    " "
                    +
                    item
                )


            return item


    # ========================================================
    # 직접 연결을 못 찾으면 출력하지 않는다.
    #
    # 이유:
    # 같은 과태료/벌칙 조문 안에는 서로 다른 위반행위가
    # 다수 열거될 수 있다. 직접 효과 조문과 연결되지 않는
    # 첫 번째 호를 임의로 보여주면 질문과 무관한 제재를
    # 사실처럼 제시할 수 있다.
    # ========================================================

    return ""


# ============================================================
# 25. 조건부 제재 요약
# ============================================================

def build_sanction_summary(
    sanction_basis: list,
    question: str,
    related_article_numbers: List[int]
) -> str:

    if not sanction_basis:

        return ""


    statement = select_basis_statement(

        basis=sanction_basis[
            0
        ],

        question=question,

        effect_category=(
            CONDITIONAL_SANCTION
        ),

        related_article_numbers=(
            related_article_numbers
        ),
    )


    if not statement:

        return (
            "별도의 제재 조항도 확인되지만, "
            "별도 위반 요건을 충족하는지 확인해야 합니다."
        )


    relevant = select_relevant_sanction_item(

        statement=statement,

        related_article_numbers=(
            related_article_numbers
        ),
    )


    if not relevant:

        return ""


    relevant = ensure_sentence_end(
        relevant
    )


    return (
        "질문의 행위 자체에 자동으로 적용되는 제재는 아니며, "
        +
        relevant
    )


# ============================================================
# 26. 사용자용 핵심 결론
# ============================================================

def build_plain_conclusion(
    organized: dict,
    question: str = ""
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


    direct_numbers = (
        get_direct_effect_article_numbers(
            consequence_basis
        )
    )


    lines = []


    # ========================================================
    # A. 직접 의무
    # ========================================================

    if direct_basis:

        direct_statement = (
            select_basis_statement(

                basis=direct_basis[
                    0
                ],

                question=question,
            )
        )


        summary = (
            build_direct_duty_summary(
                direct_statement
            )
        )


        if summary:

            basis_label = (
                get_direct_basis_label(
                    direct_statement
                )
            )

            lines.append(
                "• "
                +
                basis_label
                +
                ": "
                +
                summary
            )


    # ========================================================
    # B. 직접 효과
    # ========================================================

    if direct_effects:

        direct_effect_summaries = []


        for basis in direct_effects:

            statement = select_basis_statement(

                basis=basis,

                question=question,

                effect_category=(
                    DIRECT_CONSEQUENCE
                ),
            )


            summary = (
                build_direct_effect_summary(
                    statement
                )
            )


            if (
                summary
                and
                summary not in direct_effect_summaries
            ):

                direct_effect_summaries.append(
                    summary
                )


        for summary in direct_effect_summaries:

            lines.append(
                "• 직접 효과: "
                +
                summary
            )


    # ========================================================
    # C. 후속 불이익
    # ========================================================

    downstream_summary = (
        build_downstream_summary(
            downstream
        )
    )


    if downstream_summary:

        lines.append(
            "• 후속 불이익: "
            +
            downstream_summary
        )


    # ========================================================
    # D. 조건부 제재
    # ========================================================

    sanction_summary = (
        build_sanction_summary(

            sanction_basis=sanctions,

            question=question,

            related_article_numbers=(
                direct_numbers
            ),
        )
    )


    if sanction_summary:

        lines.append(
            "• 별도 제재: "
            +
            sanction_summary
        )


    return "\n".join(
        lines
    ).strip()