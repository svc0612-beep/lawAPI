# ============================================================
# Legal Effect Classifier
#
# 역할
# - Legal Effect Analyzer가 찾은 효과 조문을
#   실제 법적 성격별로 분류한다.
#
# 분류:
#
# direct_consequence
#     직접적인 의무 미이행 효과
#
# downstream_consequence
#     가산금 / 연체금 / 독촉 / 체납처분 등
#
# conditional_sanction
#     별도의 특정 의무 위반에 대한
#     과태료 / 형사처벌
#
# procedure_settlement
#     환급 / 시효 / 결손처분 / 이의신청 등
#
# secondary_related
#     관련은 있지만 핵심 불이익으로 보기 어려운 규정
#
# 중요:
# - 특정 법령명/조문번호를 하드코딩하지 않는다.
# - 조문 제목, 본문, 연결 단계, 세부 참조를 함께 본다.
# ============================================================

from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from services.evidence.legal_reference_parser import (
    extract_legal_references,
)

from services.evidence.legal_effect_reference_units import (
    get_explicit_direct_reference_units,
)

from services.evidence.legal_effect_sanction_unit_rules import (
    split_explicit_sanction_units,
)


# ============================================================
# 1. 절차 / 정산 표현
# ============================================================

PROCEDURE_SETTLEMENT_TITLE_TERMS = (
    "과오납",
    "환급",
    "충당과 환급",
    "소멸시효",
    "시효의 중단",
    "시효 중단",
    "결손처분",
    "이의신청",
    "심사청구",
    "징수 우선순위",
)


PROCEDURE_SETTLEMENT_TEXT_TERMS = (
    "과오납",
    "환급",
    "소멸시효",
    "시효의 중단",
    "결손처분",
    "이의신청",
    "심사청구",
)


# ============================================================
# 2. 직접 미이행 효과 표현
# ============================================================

DIRECT_CONSEQUENCE_TITLE_TERMS = (
    "부담금 납부",
    "손해배상",
    "배상책임",
)


DIRECT_CONSEQUENCE_TEXT_TERMS = (
    "못 미치는",
    "미달하는",
    "부담금을 납부하여야",
    "부담금을 납부해야",
    "배상하여야",
    "손해배상",
)


# ============================================================
# 3. 강한 후속 불이익
# ============================================================

DOWNSTREAM_CONSEQUENCE_TITLE_TERMS = (
    "가산금",
    "연체금",
    "독촉",
    "체납처분",
    "압류",
    "공매",
    "영업정지",
    "업무정지",
    "등록취소",
    "허가취소",
)


DOWNSTREAM_CONSEQUENCE_TEXT_TERMS = (
    "가산금",
    "연체금",
    "독촉",
    "체납처분",
    "압류",
    "공매",
    "영업정지",
    "업무정지",
    "등록취소",
    "허가취소",
)


# ============================================================
# 4. 제재 표현
# ============================================================

SANCTION_TITLE_TERMS = (
    "과태료",
    "벌칙",
)


SANCTION_TEXT_TERMS = (
    "과태료",
    "징역",
    "벌금",
    "처한다",
)


# ============================================================
# 5. 문자열 정리
# ============================================================

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


# ============================================================
# 6. 조문 전체 텍스트
# ============================================================

def get_article_text(
    article: Dict[
        str,
        Any
    ]
) -> str:

    if not isinstance(
        article,
        dict
    ):

        return ""


    title = clean_text(
        article.get(
            "article_title"
        )
    )


    full_text = clean_text(
        article.get(
            "full_text"
        )
    )


    if not full_text:

        full_text = clean_text(
            article.get(
                "article_content"
            )
        )


    return (
        f"{title} {full_text}"
    ).strip()


# ============================================================
# 7. 표현 포함 여부
# ============================================================

def contains_any(
    text: str,
    terms
) -> bool:

    return any(
        term in text
        for term in terms
    )

def is_sanction_article(
    article: Dict[
        str,
        Any
    ]
) -> bool:

    title = clean_text(
        article.get(
            "article_title"
        )
    )

    text = get_article_text(
        article
    )

    return bool(
        contains_any(
            title,
            SANCTION_TITLE_TERMS
        )
        or
        contains_any(
            text,
            SANCTION_TEXT_TERMS
        )
    )


# ============================================================
# 8. 세부 조문 참조 여부
#
# 예:
#
# 제33조제5항
# 제29조제1항
#
# 처럼 항/호까지 특정하는지 확인한다.
# ============================================================

def has_specific_reference(
    references: List[
        Dict[str, Any]
    ]
) -> bool:

    for reference in references:

        sub_article_number = (
            reference.get(
                "sub_article_number",
                0
            )
            or 0
        )


        paragraph_number = (
            reference.get(
                "paragraph_number",
                0
            )
            or 0
        )


        item_number = (
            reference.get(
                "item_number",
                0
            )
            or 0
        )


        if (
            sub_article_number
            or
            paragraph_number
            or
            item_number
        ):

            return True


    return False


# ============================================================
# 9. 구조화된 조문 참조
# ============================================================

def get_article_references(
    article: Dict[
        str,
        Any
    ]
) -> List[
    Dict[str, Any]
]:

    text = clean_text(
        article.get(
            "full_text"
        )
    )


    article_number = (
        article.get(
            "article_number"
        )
        or 0
    )


    sub_article_number = (
        article.get(
            "sub_article_number"
        )
        or 0
    )


    return extract_legal_references(

        text=text,

        own_article_number=(
            article_number
        ),

        own_sub_article_number=(
            sub_article_number
        ),
    )


# ============================================================
# 10. 효과 조문 분류
# ============================================================

def classify_effect_article(
    article: Dict[
        str,
        Any
    ],
    connection_level: Optional[int] = None,
    query_connected: bool = False,
    consequence_title: bool = False
) -> Dict[
    str,
    Any
]:

    if not isinstance(
        article,
        dict
    ):

        return {

            "category":
                "unknown",

            "reason":
                "invalid_article",

            "references":
                [],
        }


    title = clean_text(
        article.get(
            "article_title"
        )
    )


    text = get_article_text(
        article
    )


    references = get_article_references(
        article
    )


    # ========================================================
    # A. 제목 자체가 명백한 절차 / 정산 규정
    #
    # 예:
    # 과오납금의 충당과 환급
    # 시효의 중단
    # 결손처분
    #
    # 제목이 명확한 경우 가장 먼저 제외한다.
    # ========================================================

    if contains_any(
        title,
        PROCEDURE_SETTLEMENT_TITLE_TERMS
    ):

        return {

            "category":
                "procedure_settlement",

            "reason":
                "procedure_or_settlement_title",

            "references":
                references,
        }


    # ========================================================
    # B. 질문 행위 자체에 직접 연결된 1차 법적 효과
    #
    # Analyzer가 같은 조문 단위에서 질문의 Action + Object를
    # 확인했고(query_connected=True), 조문 제목도 실제 법적
    # 결과를 나타내는 경우(consequence_title=True)에는
    # 형사벌/손해배상 여부와 관계없이 direct_consequence로 본다.
    #
    # 예:
    # - 침해 -> 손해배상
    # - 침해 -> 침해죄
    # - 의무 미달 -> 부담금
    #
    # 반대로 단순히 다른 조문을 참조하는 과태료/벌칙은
    # 아래 sanction 분류로 내려간다.
    # ========================================================

    if (
        connection_level == 1
        and
        query_connected
        and
        consequence_title
    ):

        return {

            "category":
                "direct_consequence",

            "reason":
                "direct_query_effect",

            "references":
                references,
        }


    # ========================================================
    # B. 과태료 / 형사벌
    #
    # 질문의 직접 미이행 효과라고 자동 판단하지 않는다.
    #
    # 특히:
    # 제33조제5항 등 특정 조항을 참조하면
    # 별도의 특정 의무 위반에 대한 제재다.
    # ========================================================

    if (
        contains_any(
            title,
            SANCTION_TITLE_TERMS
        )
        or
        contains_any(
            text,
            SANCTION_TEXT_TERMS
        )
    ):

        if has_specific_reference(
            references
        ):

            return {

                "category":
                    "conditional_sanction",

                "reason":
                    "sanction_with_specific_reference",

                "references":
                    references,
            }


        return {

            "category":
                "conditional_sanction",

            "reason":
                "sanction_provision",

            "references":
                references,
        }


    # ========================================================
    # C. 명백한 후속 불이익
    #
    # 예:
    # 가산금
    # 연체금
    # 독촉
    # 체납처분
    #
    # 제35조 / 제37조 같은 조문.
    # ========================================================

    if (
        contains_any(
            title,
            DOWNSTREAM_CONSEQUENCE_TITLE_TERMS
        )
        or
        contains_any(
            text,
            DOWNSTREAM_CONSEQUENCE_TEXT_TERMS
        )
    ):

        return {

            "category":
                "downstream_consequence",

            "reason":
                "downstream_enforcement_effect",

            "references":
                references,
        }


    # ========================================================
    # D. 직접적인 미이행 효과
    #
    # 중요:
    # connection_level == 1인 조문을 우선 판정한다.
    #
    # 본문 후반에 환급이라는 단어가 있다고 해서
    # 제33조 전체를 환급 규정으로 분류하면 안 된다.
    #
    # 예:
    #
    # 제목: 사업주의 부담금 납부 등
    #
    # 제1항:
    # 의무고용률에 못 미치는 사업주
    # → 부담금 납부
    #
    # 따라서 direct_consequence.
    # ========================================================

    if connection_level == 1:

        if (
            contains_any(
                title,
                DIRECT_CONSEQUENCE_TITLE_TERMS
            )
            or
            contains_any(
                text,
                DIRECT_CONSEQUENCE_TEXT_TERMS
            )
        ):

            return {

                "category":
                    "direct_consequence",

                "reason":
                    "direct_noncompliance_effect",

                "references":
                    references,
            }


    # ========================================================
    # E. 본문 기준 절차 / 정산
    #
    # 제목에서는 명확하지 않았지만
    # 조문 전체 성격이 환급/시효/정산 규정인 경우.
    #
    # direct_consequence 판정 뒤에 수행해야
    # 제33조 같은 조문을 잘못 제외하지 않는다.
    # ========================================================

    if contains_any(
        text,
        PROCEDURE_SETTLEMENT_TEXT_TERMS
    ):

        return {

            "category":
                "procedure_settlement",

            "reason":
                "procedure_or_settlement_text",

            "references":
                references,
        }


    # ========================================================
    # F. 2차 관련 규정
    # ========================================================

    if connection_level == 2:

        return {

            "category":
                "secondary_related",

            "reason":
                "secondary_relation_without_clear_adverse_effect",

            "references":
                references,
        }


    # ========================================================
    # G. 기타 관련 효과
    # ========================================================

    return {

        "category":
            "related_effect",

        "reason":
            "related_legal_effect",

        "references":
            references,
    }


# ============================================================
# 11. Analyzer item 하나 분류
# ============================================================

def classify_effect_item(
    item: Dict[
        str,
        Any
    ]
) -> Dict[
    str,
    Any
]:

    if not isinstance(
        item,
        dict
    ):

        return {

            "category":
                "unknown",

            "reason":
                "invalid_item",
        }


    article = item.get(
        "article",
        {}
    )


    referenced_direct_articles = (
        item.get(
            "referenced_direct_articles",
            []
        )
        or
        []
    )


    explicit_direct_reference_units = (
        get_explicit_direct_reference_units(

            article=article,

            direct_article_numbers=(
                referenced_direct_articles
            ),
        )
    )


    (
        direct_reference_sanction_units,
        conditional_reference_sanction_units,
    ) = split_explicit_sanction_units(
        explicit_direct_reference_units
    )


    classification = classify_effect_article(

        article=article,

        connection_level=(
            item.get(
                "connection_level"
            )
        ),

        query_connected=bool(
            item.get(
                "query_connected",
                False
            )
        ),

        consequence_title=bool(
            item.get(
                "consequence_title",
                False
            )
        ),
    )


    if (
        item.get(
            "connection_level"
        )
        == 1
        and
        is_sanction_article(
            article
        )
    ):

        # ----------------------------------------------------
        # Direct Anchor를 명시적으로 참조하더라도
        # "위반 사실이 별도 방식으로 입증된 경우"처럼
        # 추가 조건이 붙은 간접 책임 unit이면
        # direct_consequence로 자동 승격하지 않는다.
        #
        # 반대로 항 본문 + 호를 결합했을 때
        # Direct Anchor 참조와 실제 제재가 같은 unit에 있으면
        # direct_consequence로 승격한다.
        # ----------------------------------------------------

        if direct_reference_sanction_units:

            classification = {

                "category":
                    "direct_consequence",

                "reason":
                    "explicit_direct_sanction_unit",

                "references":
                    get_article_references(
                        article
                    ),
            }

        elif conditional_reference_sanction_units:

            classification = {

                "category":
                    "conditional_sanction",

                "reason":
                    "explicit_reference_with_indirect_condition",

                "references":
                    get_article_references(
                        article
                    ),
            }


    result = dict(
        item
    )


    result[
        "explicit_direct_reference_units"
    ] = explicit_direct_reference_units


    result[
        "direct_reference_sanction_units"
    ] = direct_reference_sanction_units


    result[
        "conditional_reference_sanction_units"
    ] = conditional_reference_sanction_units


    result[
        "effect_category"
    ] = classification.get(
        "category"
    )


    result[
        "effect_reason"
    ] = classification.get(
        "reason"
    )


    result[
        "structured_references"
    ] = classification.get(
        "references",
        []
    )


    return result


# ============================================================
# 12. 여러 효과 조문 일괄 분류
# ============================================================

def classify_effect_items(
    items: List[
        Dict[
            str,
            Any
        ]
    ]
) -> List[
    Dict[
        str,
        Any
    ]
]:

    if not isinstance(
        items,
        list
    ):

        return []


    classified = [

        classify_effect_item(
            item
        )

        for item in items

        if isinstance(
            item,
            dict
        )
    ]


    has_explicit_direct_sanction = any(

        item.get(
            "connection_level"
        )
        == 1

        and
        item.get(
            "direct_reference_sanction_units"
        )

        and
        is_sanction_article(
            item.get(
                "article",
                {}
            )
        )

        for item in classified
    )


    if has_explicit_direct_sanction:

        for item in classified:

            if item.get(
                "connection_level"
            ) != 1:

                continue

            if item.get(
                "effect_category"
            ) != "direct_consequence":

                continue

            if not is_sanction_article(
                item.get(
                    "article",
                    {}
                )
            ):

                continue

            if item.get(
                "direct_reference_sanction_units"
            ):

                continue

            item[
                "effect_category"
            ] = "conditional_sanction"

            item[
                "effect_reason"
            ] = (
                "query_connected_sanction_without_"
                "explicit_direct_reference"
            )


    return classified
