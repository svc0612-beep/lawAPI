import re

# ============================================================
# Conclusion Direct
#
# 직접 근거 / 직접 효과 / 후속 효과의 짧은 사용자용 요약 생성.
# ============================================================

from services.generation.conclusion_text_utils import (
    clean_text,
    remove_parenthetical_details,
    ensure_sentence_end,
    extract_numeric_conditions,
    extract_exclusion_clause,
    extract_actor_clause,
    extract_norm_clause,
)

from services.generation.conclusion_helpers import (
    get_basis_title,
)

def has_negative_condition_question(
    question: str
) -> bool:

    question = clean_text(
        question
    )

    if not question:
        return False

    negative_patterns = (
        " 없이",
        "없이 ",
        "안 하면",
        "안하면",
        "않으면",
        "못 하면",
        "못하면",
    )

    return any(
        pattern in question
        for pattern in negative_patterns
    )


def is_multiple_authorization_rule(
    statement: str
) -> bool:

    statement = clean_text(
        statement
    )

    if not statement:
        return False

    has_multi_condition = (
        "다음 각 호" in statement
        and
        "어느 하나" in statement
    )

    authorization_terms = (
        "할 수 있다",
        "할 수 있으며",
        "할 수 있고",
        "가능하다",
    )

    has_authorization = any(
        term in statement
        for term in authorization_terms
    )

    numbered_items = re.findall(
        r"(?<!\d)(\d{1,2})\.\s*",
        statement
    )

    return (
        has_multi_condition
        and
        has_authorization
        and
        len(numbered_items) >= 2
    )


def build_multiple_authorization_summary(
    statement: str,
    question: str = ""
) -> str:

    if not (
        has_negative_condition_question(
            question
        )
        and
        is_multiple_authorization_rule(
            statement
        )
    ):
        return ""

    return (
        "이 조문은 질문의 행위가 허용되는 경우를 여러 가지로 정하고 있습니다. "
        "따라서 질문에서 말한 조건이 없다는 이유만으로 곧바로 위법이라고 단정할 수 없습니다. "
        "다만 다른 법정 허용 근거에도 해당하지 않으면 이 조문 위반이 될 수 있습니다."
    )


def build_direct_duty_summary(
    statement: str,
    question: str = ""
) -> str:

    statement = clean_text(
        statement
    )

    if not statement:
        return ""

    authorization_summary = (
        build_multiple_authorization_summary(
            statement=statement,
            question=question,
        )
    )

    if authorization_summary:
        return authorization_summary

    compact = remove_parenthetical_details(
        statement
    )

    actor_clause = extract_actor_clause(
        compact
    )

    norm_clause = extract_norm_clause(
        compact
    )

    if (
        compact
        and
        len(compact) <= 320
    ):
        return ensure_sentence_end(
            compact
        )

    parts = []

    if actor_clause:
        parts.append(
            actor_clause
        )

    if norm_clause:
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
                numeric_conditions[:2]
            )
            +
            "이 확인됩니다."
        )

    if compact:
        return ensure_sentence_end(
            compact
        )

    return ensure_sentence_end(
        statement
    )

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
