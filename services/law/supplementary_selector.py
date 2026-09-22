# ============================================================
# 부칙 조회용 정확 법령 선택
#
# 중요:
# - 검색 첫 번째 결과를 fallback으로 사용하지 않는다.
# - 공백 제거 후 정확히 같은 법령만 선택한다.
# - 특정 법령 하드코딩 없음
# ============================================================

import re

from typing import (
    Any,
    Dict,
    Optional,
)

from services.law.search import (
    search_law,
)


def find_exact_law(
    law_name: str
) -> Optional[
    Dict[str, Any]
]:

    law_name = (
        law_name
        or ""
    ).strip()

    if not law_name:
        return None

    results = search_law(

        query=law_name,

        display=20
    )

    target = re.sub(
        r"\s+",
        "",
        law_name
    )

    for item in results:

        candidate = re.sub(

            r"\s+",

            "",

            str(
                item.get(
                    "법령명한글",
                    ""
                )
            )
        )

        if candidate == target:

            return item

    return None