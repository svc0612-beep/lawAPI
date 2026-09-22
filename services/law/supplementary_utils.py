# ============================================================
# 법령 부칙 공통 유틸리티
# ============================================================

import re

from typing import (
    Any,
    List,
)


# ============================================================
# 문자열 정리
# ============================================================

def normalize_text(
    value: Any
) -> str:

    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value)
    ).strip()


# ============================================================
# 중첩 텍스트 평탄화
#
# 실제 부칙내용은
#
# [
#     [
#         "부칙 ...",
#         "제1조 ...",
#     ]
# ]
#
# 같은 중첩 구조일 수 있다.
# ============================================================

def flatten_text_items(
    value: Any
) -> List[str]:

    results: List[str] = []

    if value is None:
        return results

    # ========================================================
    # list
    # ========================================================

    if isinstance(
        value,
        list
    ):

        for item in value:

            results.extend(
                flatten_text_items(
                    item
                )
            )

        return results

    # ========================================================
    # dict
    # ========================================================

    if isinstance(
        value,
        dict
    ):

        for item in value.values():

            results.extend(
                flatten_text_items(
                    item
                )
            )

        return results

    # ========================================================
    # 문자열 / 숫자 등
    # ========================================================

    text = normalize_text(
        value
    )

    if text:

        results.append(
            text
        )

    return results