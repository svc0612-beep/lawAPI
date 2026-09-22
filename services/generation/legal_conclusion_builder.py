# ============================================================
# Legal Conclusion Builder
#
# 최종 사용자용 짧은 결론 조립만 담당한다.
#
# 리팩터링 원칙:
# - 특정 법률명/조문번호/숫자 하드코딩 금지
# - LLM 사용 금지
# - Evidence에 없는 법률 사실 생성 금지
# - 기존 import 호환성을 위해 기존 public helper를 re-export
# ============================================================

from services.generation.conclusion_text_utils import (
    clean_text,
    remove_revision_note,
    remove_paragraph_marker,
    normalize_statement,
    remove_parenthetical_details,
    ensure_sentence_end,
    extract_numeric_conditions,
    extract_exclusion_clause,
    extract_actor_clause,
    extract_norm_clause,
)

from services.generation.conclusion_helpers import (
    DIRECT_CONSEQUENCE,
    DOWNSTREAM_CONSEQUENCE,
    CONDITIONAL_SANCTION,
    get_basis_evidence,
    get_basis_category,
    get_article_number,
    split_consequence_basis,
    get_direct_effect_article_numbers,
    select_basis_statement,
    select_representative_direct_basis,
    get_basis_title,
    get_reference_article_numbers,
    split_numbered_items,
)

from services.generation.conclusion_direct import (
    build_direct_duty_summary,
    get_direct_basis_label,
    build_direct_effect_summary,
    build_downstream_summary,
)

from services.generation.conclusion_sanction import (
    select_relevant_sanction_item,
    build_sanction_summary,
)

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

        representative_basis = (
            select_representative_direct_basis(

                direct_basis=direct_basis,

                consequence_basis=consequence_basis,

                question=question,
            )
        )


        direct_statement = (
            select_basis_statement(

                basis=representative_basis,

                question=question,
            )
        )


        summary = (
            build_direct_duty_summary(
                direct_statement,
                question=question,
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
