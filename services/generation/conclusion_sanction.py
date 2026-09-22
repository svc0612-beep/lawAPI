# ============================================================
# Conclusion Sanction
#
# 조건부 제재 조문에서 실제 관련 호를 선택하고 요약한다.
# ============================================================

from typing import (
    List,
)

from services.generation.conclusion_text_utils import (
    clean_text,
    remove_revision_note,
    ensure_sentence_end,
)

from services.generation.conclusion_helpers import (
    CONDITIONAL_SANCTION,
    select_basis_statement,
    get_reference_article_numbers,
    split_numbered_items,
)

def select_relevant_sanction_item(
    statement: str,
    related_article_numbers: List[int]
) -> str:

    # 개정 이력의 날짜(예: 2017.11.28)가
    # "1. / 2." 형태의 호 번호로 잘못 인식되지 않도록
    # 번호 분리 전에 개정 이력을 먼저 제거한다.
    statement = remove_revision_note(
        clean_text(
            statement
        )
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
