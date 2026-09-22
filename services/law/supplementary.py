# ============================================================
# 법제처 법령 부칙 조회 서비스
#
# 흐름:
#
# 법령명
#   ↓
# 정확한 공식 법령 선택
#   ↓
# MST
#   ↓
# 법령 상세 JSON
#   ↓
# 부칙 파싱
#   ↓
# Evidence용 표준 결과
#
# 특정 법령 하드코딩 없음
# ============================================================

from typing import (
    Any,
    Dict,
)


# ============================================================
# 기존 외부 import 호환성을 위한 재노출
# ============================================================

from services.law.supplementary_utils import (
    normalize_text,
    flatten_text_items,
)

from services.law.supplementary_selector import (
    find_exact_law,
)

from services.law.supplementary_fetcher import (
    fetch_law_detail,
)

from services.law.supplementary_parser import (
    parse_supplementary_unit,
    parse_supplementary_provisions,
)


# ============================================================
# 최종 공개 함수
# ============================================================

def get_supplementary_provisions(
    law_name: str
) -> Dict[str, Any]:

    law_name = normalize_text(
        law_name
    )

    # ========================================================
    # 1. 입력 검증
    # ========================================================

    if not law_name:

        return {

            "status":
                "error",

            "law_name":
                "",

            "count":
                0,

            "supplementary_provisions":
                [],

            "message":
                "법령명이 비어 있습니다.",
        }

    # ========================================================
    # 2. 정확한 법령 선택
    # ========================================================

    law_info = find_exact_law(
        law_name
    )

    if not law_info:

        return {

            "status":
                "not_found",

            "law_name":
                law_name,

            "count":
                0,

            "supplementary_provisions":
                [],

            "message":
                "정확히 일치하는 법령을 찾지 못했습니다.",
        }

    # ========================================================
    # 3. MST
    # ========================================================

    mst = normalize_text(
        law_info.get(
            "법령일련번호"
        )
    )

    if not mst:

        return {

            "status":
                "error",

            "law_name":
                law_name,

            "count":
                0,

            "supplementary_provisions":
                [],

            "message":
                "법령일련번호(MST)를 확인할 수 없습니다.",
        }

    # ========================================================
    # 4. 상세 JSON
    # ========================================================

    data = fetch_law_detail(
        mst=mst
    )

    # ========================================================
    # 5. 부칙 파싱
    # ========================================================

    supplementary = (
        parse_supplementary_provisions(
            data
        )
    )

    # ========================================================
    # 6. 반환
    # ========================================================

    return {

        "status":
            "success",

        "law_name":
            normalize_text(
                law_info.get(
                    "법령명한글"
                )
            ),

        "law_id":
            normalize_text(
                law_info.get(
                    "법령ID"
                )
            ),

        "mst":
            mst,

        "count":
            len(
                supplementary
            ),

        "supplementary_provisions":
            supplementary,
    }