# ============================================================
# 공식 법령 관계 조회 서비스
#
# 현재 범위
# - 법제처 lsStmd 법령 체계도
# - 상위법령
# - 하위법령
# - 시행령
# - 시행규칙
# - 별도 관련법령
#
# 행정규칙은 응답에 포함되더라도 이번 단계에서는 제외한다.
# ============================================================

from typing import (
    Any,
    Dict,
)

from services.law.related_laws_fetcher import (
    request_law_system_map,
)

from services.law.related_laws_parser import (
    normalize_text,
    parse_law_system_map,
)


def get_official_related_laws(
    law_name: str,
    mst: str,
    law_id: str = "",
) -> Dict[str, Any]:

    law_name = normalize_text(
        law_name
    )

    mst = normalize_text(
        mst
    )

    law_id = normalize_text(
        law_id
    )

    if not law_name:

        return {
            "status": "error",
            "law_name": "",
            "mst": mst,
            "count": 0,
            "related_laws": [],
            "message": "법령명이 비어 있습니다.",
        }

    if not mst:

        return {
            "status": "error",
            "law_name": law_name,
            "mst": "",
            "count": 0,
            "related_laws": [],
            "message": "법령일련번호(MST)가 없습니다.",
        }

    raw_data = request_law_system_map(
        mst=mst
    )

    related_laws = parse_law_system_map(
        raw_data=raw_data,
        source_law_name=law_name,
        source_mst=mst,
        source_law_id=law_id,
        include_administrative=False,
    )

    return {
        "status": "success",
        "law_name": law_name,
        "mst": mst,
        "count": len(related_laws),
        "related_laws": related_laws,
        "message": "",
    }
