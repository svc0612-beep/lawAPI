# ============================================================
# Organized Evidence Response
#
# 역할:
# - OrganizedEvidence를 사용자용 상세 답변으로 변환
# - 공식 Evidence만 사용
# - 조문 내부 핵심 항 선택은 legal_statement_selector에 위임
# ============================================================

from typing import (
    Any,
    Dict,
    List,
)

from services.generation.response_utils import (
    clean_text,
    make_article_label,
)

from services.generation.response_scoring import (
    extract_core_statement,
)

from services.generation.legal_statement_selector import (
    select_best_statement,
)

from services.generation.legal_conclusion_builder import (
    build_plain_conclusion,
    select_relevant_sanction_item,
)


DIRECT_CONSEQUENCE = (
    "direct_consequence"
)

DOWNSTREAM_CONSEQUENCE = (
    "downstream_consequence"
)

CONDITIONAL_SANCTION = (
    "conditional_sanction"
)


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


def build_sanction_basis_lines(
    basis_items: list,
    question: str,
    related_article_numbers: List[int] = None
) -> List[str]:

    lines = []

    if not isinstance(
        basis_items,
        list
    ):
        return lines

    related_article_numbers = (
        related_article_numbers
        or
        []
    )

    if not related_article_numbers:
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

        statement = select_basis_statement(
            evidence=evidence,
            question=question,
            effect_category=(
                CONDITIONAL_SANCTION
            ),
            related_article_numbers=(
                related_article_numbers
            ),
        )

        if not statement:
            continue

        relevant = select_relevant_sanction_item(
            statement=statement,
            related_article_numbers=(
                related_article_numbers
            ),
        )

        if not relevant:
            continue

        heading = build_evidence_heading(
            evidence
        )

        if heading:

            lines.append(
                f"- **{heading}**"
            )

        lines.append(
            f"  - {relevant}"
        )

    return lines


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

    primary_law_name = (
        get_primary_law_name(
            organized
        )
    )

    plain_conclusion = ""

    try:

        plain_conclusion = build_plain_conclusion(
            organized=organized,
            question=question,
        )

    except Exception:
        plain_conclusion = ""

    lines = []

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

    if direct_effects:

        lines.append(
            ""
        )

        lines.append(
            "### 2. 질문 행위에 따른 직접적인 법적 효과"
        )

        lines.extend(
            build_basis_lines(
                basis_items=direct_effects,
                question=question,
                effect_category=(
                    DIRECT_CONSEQUENCE
                ),
            )
        )

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

    if sanctions:

        sanction_lines = (
            build_sanction_basis_lines(
                basis_items=sanctions,
                question=question,
                related_article_numbers=(
                    direct_effect_article_numbers
                ),
            )
        )

        if sanction_lines:

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
                sanction_lines
            )

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
