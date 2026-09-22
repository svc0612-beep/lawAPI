# ============================================================
# 공식 법령 재검증
# ============================================================

from typing import (
    Any,
    Dict,
    Optional,
)

from services.law.search import (
    search_law,
)

from services.law.resolver_utils import (
    normalize_text,
    compact_text,
)


def verify_official_law(
    law_name: str
) -> Optional[Dict[str, Any]]:

    law_name = normalize_text(
        law_name
    )

    if not law_name:
        return None

    results = search_law(
        query=law_name,
        display=20
    )

    target = compact_text(
        law_name
    )

    for item in results:

        candidate_name = compact_text(
            item.get(
                "법령명한글"
            )
        )

        if candidate_name == target:

            return item

    return None