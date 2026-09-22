# ============================================================
# 법령 부칙 Parser
#
# 실제 확인 구조:
#
# 법령
# └─ 부칙
#    └─ 부칙단위
#       ├─ 부칙키
#       ├─ 부칙공포일자
#       ├─ 부칙공포번호
#       └─ 부칙내용
# ============================================================

from typing import (
    Any,
    Dict,
    List,
)

from services.law.supplementary_utils import (
    normalize_text,
    flatten_text_items,
)


# ============================================================
# 부칙 한 건
# ============================================================

def parse_supplementary_unit(
    law_name: str,
    unit: Dict[str, Any]
) -> Dict[str, Any]:

    content_items = flatten_text_items(
        unit.get(
            "부칙내용"
        )
    )

    title = ""

    if content_items:

        title = content_items[0]

    full_text = "\n".join(
        content_items
    )

    return {

        "source":
            "법제처",

        "law_name":
            law_name,

        "supplementary_key":
            normalize_text(
                unit.get(
                    "부칙키"
                )
            ),

        "promulgation_date":
            normalize_text(
                unit.get(
                    "부칙공포일자"
                )
            ),

        "promulgation_number":
            normalize_text(
                unit.get(
                    "부칙공포번호"
                )
            ),

        "title":
            title,

        "content_items":
            content_items,

        "text":
            full_text,
    }


# ============================================================
# 부칙 전체
# ============================================================

def parse_supplementary_provisions(
    data: Dict[str, Any]
) -> List[
    Dict[str, Any]
]:

    if not isinstance(
        data,
        dict
    ):

        return []

    law_root = data.get(
        "법령",
        {}
    )

    if not isinstance(
        law_root,
        dict
    ):

        return []

    # ========================================================
    # 법령명
    # ========================================================

    basic_info = law_root.get(
        "기본정보",
        {}
    )

    if not isinstance(
        basic_info,
        dict
    ):

        basic_info = {}

    law_name = normalize_text(

        basic_info.get(
            "법령명_한글"
        )

        or

        basic_info.get(
            "법령명한글"
        )
    )

    # ========================================================
    # 부칙
    # ========================================================

    supplementary_root = law_root.get(
        "부칙",
        {}
    )

    if not isinstance(
        supplementary_root,
        dict
    ):

        return []

    units = supplementary_root.get(
        "부칙단위",
        []
    )

    # 1건일 경우 dict 가능
    if isinstance(
        units,
        dict
    ):

        units = [
            units
        ]

    if not isinstance(
        units,
        list
    ):

        return []

    results = []

    for unit in units:

        if not isinstance(
            unit,
            dict
        ):

            continue

        parsed = parse_supplementary_unit(

            law_name=law_name,

            unit=unit
        )

        if parsed.get(
            "text"
        ):

            results.append(
                parsed
            )

    return results