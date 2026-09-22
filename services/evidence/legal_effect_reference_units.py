# ============================================================
# Legal Effect Reference Units
#
# 역할:
# - 조문 전체가 아니라 구조화된 paragraph / item / sub-item 단위에서
#   Direct Anchor 조문을 명시적으로 참조하는 unit을 찾는다.
# - 특정 법령명/조문번호를 하드코딩하지 않는다.
#
# 개선:
# - 기존에는 paragraph["text"]만 검사했다.
# - 벌칙/과태료 조문은 "항 본문 + 호" 구조가 많아서
#   실제 Direct Anchor 참조가 호(items)에 있으면 놓칠 수 있었다.
# - 이제 조문 lead + 부모 항 문맥 + 자식 호/목 텍스트를 결합하여 검사한다.
# ============================================================

from typing import (
    Any,
    Dict,
    List,
)

from services.evidence.legal_reference_parser import (
    extract_legal_references,
)


def clean_text(
    value: Any
) -> str:

    if value is None:
        return ""

    return " ".join(
        str(
            value
        ).split()
    )


def _match_direct_references(
    text: str,
    target_numbers,
    own_article_number,
    own_sub_article_number,
):

    text = clean_text(
        text
    )

    if not text:
        return []

    references = extract_legal_references(
        text=text,
        own_article_number=own_article_number,
        own_sub_article_number=own_sub_article_number,
    )

    matched = [
        reference
        for reference in references
        if int(
            reference.get(
                "article_number",
                0,
            )
            or 0
        )
        in target_numbers
    ]

    return matched


def _build_nested_units(
    items,
    parent_context: str,
):
    """
    paragraph -> 호 -> 목 구조를 재귀적으로 펼친다.

    반환값:
    [
        {
            "text": "부모 문맥 + 현재 항목",
            "leaf_text": "현재 항목",
            "unit_kind": "item",
        },
        ...
    ]
    """

    results = []

    if not isinstance(
        items,
        list
    ):
        return results

    for item in items:

        if not isinstance(
            item,
            dict
        ):
            continue

        item_text = clean_text(
            item.get(
                "text"
            )
        )

        combined_text = clean_text(
            " ".join(
                value
                for value in (
                    parent_context,
                    item_text,
                )
                if value
            )
        )

        if combined_text:

            results.append(
                {
                    "text":
                        combined_text,

                    "leaf_text":
                        item_text,

                    "unit_kind":
                        "item",
                }
            )

        child_items = item.get(
            "items"
        ) or []

        if child_items:

            child_parent = (
                combined_text
                or
                parent_context
            )

            results.extend(
                _build_nested_units(
                    items=child_items,
                    parent_context=child_parent,
                )
            )

    return results


def get_explicit_direct_reference_units(
    article: Dict[str, Any],
    direct_article_numbers,
) -> List[Dict[str, Any]]:

    if not isinstance(
        article,
        dict
    ):
        return []

    target_numbers = {
        int(
            number
        )
        for number in (
            direct_article_numbers
            or []
        )
        if str(
            number
        ).isdigit()
        and int(
            number
        ) > 0
    }

    if not target_numbers:
        return []

    paragraphs = (
        article.get(
            "paragraphs"
        )
        or []
    )

    if not isinstance(
        paragraphs,
        list
    ):
        return []

    own_article_number = (
        article.get(
            "article_number"
        )
        or 0
    )

    own_sub_article_number = (
        article.get(
            "sub_article_number"
        )
        or 0
    )

    results = []
    seen = set()

    # --------------------------------------------------------
    # 조문 전체의 공통 lead 문맥.
    #
    # 벌칙/과태료 조문은
    # article_content 쪽에
    # "다음 각 호 ... 벌금/과태료에 처한다"
    # 같은 제재 문장이 있고,
    # 실제 제5조 등 참조는 호(items)에만 있는 경우가 많다.
    #
    # 그래서 item 단위를 검사할 때
    # article_content + paragraph + item 문맥을 함께 본다.
    # --------------------------------------------------------

    article_context = clean_text(
        article.get(
            "article_content"
        )
    )

    for paragraph in paragraphs:

        if not isinstance(
            paragraph,
            dict
        ):
            continue

        paragraph_text = clean_text(
            paragraph.get(
                "text"
            )
        )

        # ----------------------------------------------------
        # 1. 항 본문 자체
        # ----------------------------------------------------

        if paragraph_text:

            matched = _match_direct_references(
                text=paragraph_text,
                target_numbers=target_numbers,
                own_article_number=own_article_number,
                own_sub_article_number=own_sub_article_number,
            )

            if matched:

                key = (
                    "paragraph",
                    paragraph_text,
                )

                if key not in seen:

                    seen.add(
                        key
                    )

                    results.append(
                        {
                            "text":
                                paragraph_text,

                            "leaf_text":
                                paragraph_text,

                            "unit_kind":
                                "paragraph",

                            "references":
                                matched,
                        }
                    )

        # ----------------------------------------------------
        # 2. 항 + 호/목 결합 단위
        #
        # 예:
        # 항: "다음 각 호의 어느 하나에 해당하는 사람은
        #      20만원 이하의 벌금..."
        # 호: "제5조를 위반한 차마의 운전자"
        #
        # 기존 paragraph-only 방식에서는 호의 제5조 참조를 놓쳤다.
        # ----------------------------------------------------

        nested_parent_context = clean_text(
            " ".join(
                value
                for value in (
                    article_context,
                    paragraph_text,
                )
                if value
            )
        )

        nested_units = _build_nested_units(
            items=(
                paragraph.get(
                    "items"
                )
                or []
            ),
            parent_context=nested_parent_context,
        )

        for unit in nested_units:

            unit_text = clean_text(
                unit.get(
                    "text"
                )
            )

            if not unit_text:
                continue

            matched = _match_direct_references(
                text=unit_text,
                target_numbers=target_numbers,
                own_article_number=own_article_number,
                own_sub_article_number=own_sub_article_number,
            )

            if not matched:
                continue

            key = (
                unit.get(
                    "unit_kind",
                    "item"
                ),
                unit_text,
            )

            if key in seen:
                continue

            seen.add(
                key
            )

            results.append(
                {
                    "text":
                        unit_text,

                    "leaf_text":
                        clean_text(
                            unit.get(
                                "leaf_text"
                            )
                        ),

                    "unit_kind":
                        unit.get(
                            "unit_kind",
                            "item"
                        ),

                    "references":
                        matched,
                }
            )

    return results
