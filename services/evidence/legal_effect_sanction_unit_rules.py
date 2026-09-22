# ============================================================
# Legal Effect Sanction Unit Rules
#
# 역할:
# - Direct Anchor를 명시적으로 참조하는 제재 unit이
#   "질문 행위 자체의 직접 제재"인지
#   "추가 조건/간접 책임/집행절차가 붙은 제재"인지 구분한다.
#
# 특정 법률명/조문번호 하드코딩 없음.
# ============================================================

from typing import (
    Any,
    Dict,
    List,
)


DIRECT_SANCTION_TERMS = (
    "과태료",
    "벌금",
    "징역",
    "구류",
    "과료",
    "처한다",
)


# ------------------------------------------------------------
# 직접 위반자에게 바로 제재를 주는 문장이라기보다
# "위반 사실이 별도 방식으로 입증된 경우"
# "직접 위반자와 다른 책임 주체에게 제재"
# 같은 구조에서 자주 나타나는 일반 표현.
#
# 특정 법률/주제 용어는 넣지 않는다.
# ------------------------------------------------------------

INDIRECT_CONDITION_GROUPS = (
    (
        "위반한 사실",
        "입증",
    ),
    (
        "위반 사실",
        "입증",
    ),
    (
        "위반한 사실",
        "영상기록",
    ),
    (
        "위반한 사실",
        "사진",
    ),

    # --------------------------------------------------------
    # 과태료/제재의 존재 자체가 아니라
    # "누가 부과ㆍ징수하는가"를 정하는 집행/권한 규정.
    #
    # 이런 unit은 Direct Anchor를 참조하더라도
    # 질문 행위 자체의 직접 제재 문장으로 보지 않는다.
    # --------------------------------------------------------

    (
        "과태료",
        "부과",
        "징수",
    ),
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


def unit_has_sanction_effect(
    unit: Dict[str, Any]
) -> bool:

    if not isinstance(
        unit,
        dict
    ):
        return False

    text = clean_text(
        unit.get(
            "text"
        )
    )

    if not text:
        return False

    return any(
        term in text
        for term in DIRECT_SANCTION_TERMS
    )


def unit_has_indirect_condition(
    unit: Dict[str, Any]
) -> bool:

    if not isinstance(
        unit,
        dict
    ):
        return False

    text = clean_text(
        unit.get(
            "text"
        )
    )

    if not text:
        return False

    for terms in INDIRECT_CONDITION_GROUPS:

        if all(
            term in text
            for term in terms
        ):
            return True

    return False


def split_explicit_sanction_units(
    units: List[Dict[str, Any]]
):

    direct_units = []
    conditional_units = []

    if not isinstance(
        units,
        list
    ):
        return (
            direct_units,
            conditional_units,
        )

    for unit in units:

        if not isinstance(
            unit,
            dict
        ):
            continue

        if not unit_has_sanction_effect(
            unit
        ):
            continue

        if unit_has_indirect_condition(
            unit
        ):

            conditional_units.append(
                unit
            )

        else:

            direct_units.append(
                unit
            )

    return (
        direct_units,
        conditional_units,
    )
