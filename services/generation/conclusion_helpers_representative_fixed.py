# ============================================================
# Conclusion Helpers
#
# Evidence/Basis 접근, category 분리, 조문 참조/항목 분리를 담당.
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

from services.evidence.question_action_matcher import (
    score_question_connection,
)

from services.generation.conclusion_text_utils import (
    clean_text,
    normalize_statement,
)


DIRECT_CONSEQUENCE = "direct_consequence"
DOWNSTREAM_CONSEQUENCE = "downstream_consequence"
CONDITIONAL_SANCTION = "conditional_sanction"

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



def get_basis_raw_text(
    basis: dict
) -> str:

    evidence = get_basis_evidence(
        basis
    )

    if not evidence:

        return ""


    return clean_text(

        evidence.get(
            "full_text"
        )

        or

        evidence.get(
            "article_content"
        )

        or

        evidence.get(
            "article_text"
        )
    )


def select_representative_direct_basis(
    direct_basis: list,
    consequence_basis: list,
    question: str = ""
) -> dict:

    """
    여러 direct basis 중 최종 결론에 사용할 대표 근거를 고른다.

    우선순위
    1. 실제 법적 효과/후속 조문이 명시적으로 참조하는 direct basis
    2. 질문의 action/object가 선택된 항과 직접 연결되는 정도
    3. 기존 direct_basis 순서

    특정 법률명/조문번호는 사용하지 않는다.
    """

    if not isinstance(
        direct_basis,
        list
    ):

        return {}


    candidates = [
        basis

        for basis in direct_basis

        if isinstance(
            basis,
            dict
        )
        and
        get_basis_evidence(
            basis
        )
    ]


    if not candidates:

        return {}


    # ========================================================
    # A. consequence 조문이 어떤 direct article을
    #    실제로 참조하는지 수집
    # ========================================================

    referenced_numbers = []


    if isinstance(
        consequence_basis,
        list
    ):

        for basis in consequence_basis:

            if not isinstance(
                basis,
                dict
            ):

                continue


            raw_text = get_basis_raw_text(
                basis
            )


            if not raw_text:

                continue


            for number in get_reference_article_numbers(
                raw_text
            ):

                if number not in referenced_numbers:

                    referenced_numbers.append(
                        number
                    )


    scored = []


    for index, basis in enumerate(
        candidates
    ):

        article_number = get_article_number(
            basis
        )


        statement = select_basis_statement(

            basis=basis,

            question=question,
        )


        score = 0.0


        # ====================================================
        # B. 실제 consequence가 이 direct article을
        #    명시적으로 참조하면 가장 강하게 우선
        # ====================================================

        if (
            article_number > 0
            and
            article_number in referenced_numbers
        ):

            score += 100.0


        # ====================================================
        # C. 질문 action/object 연결도
        # ====================================================

        if statement and question:

            try:

                connection = score_question_connection(

                    question=question,

                    title="",

                    body=statement,
                )

            except Exception:

                connection = {}


            if bool(
                connection.get(
                    "body_action_match"
                )
                or
                connection.get(
                    "action_match"
                )
            ):

                score += 20.0


            if bool(
                connection.get(
                    "combined_match"
                )
            ):

                score += 10.0


            try:

                object_match_count = int(

                    connection.get(
                        "object_match_count"
                    )

                    or 0
                )

            except (
                TypeError,
                ValueError,
            ):

                object_match_count = 0


            score += (
                min(
                    object_match_count,
                    3
                )
                *
                2.0
            )


        # 기존 순서는 마지막 tie-break로만 유지한다.
        scored.append(
            (
                score,
                -index,
                basis,
            )
        )


    scored.sort(
        key=lambda item: (
            -item[
                0
            ],
            -item[
                1
            ],
        )
    )


    return scored[
        0
    ][
        2
    ]

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
