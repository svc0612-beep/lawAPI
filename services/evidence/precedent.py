# ============================================================
# 법제처 판례 서비스
#
# 역할
# 1. 법제처 판례 검색 target=prec
# 2. 검색 결과 구조 정규화
# 3. 상위 판례 상세조회
# 4. 검색 결과 + 상세내용 병합
# 5. 공통 SQLite 캐시 사용
# ============================================================

import os
import sys


# ============================================================
# 1. 프로젝트 루트 경로 등록
# ============================================================

CURRENT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        CURRENT_DIR
    )
)

if PROJECT_ROOT not in sys.path:

    sys.path.append(
        PROJECT_ROOT
    )


# ============================================================
# 2. 공통 유틸
# ============================================================

from services.evidence.precedent_utils import (
    normalize_text,
    ensure_list,
)


# ============================================================
# 3. Parser
# ============================================================

from services.evidence.precedent_parser import (
    is_precedent_item,
    extract_precedent_list,
    normalize_precedent_item,
    normalize_precedent_list,
    extract_precedent_detail,
    normalize_precedent_detail,
)


# ============================================================
# 4. Fetcher
# ============================================================

from services.evidence.precedent_fetcher import (
    fetch_precedent_search_data,
    fetch_precedent_detail_data,
)


# ============================================================
# 5. 판례 검색 + 상세내용 병합
# ============================================================

def search_precedents(
    query: str,
    display: int = 5,
    detail_limit: int = 3
):

    query = (
        query
        or ""
    ).strip()

    if not query:

        return []

    # ========================================================
    # A. 검색
    # ========================================================

    data = fetch_precedent_search_data(
        query=query,
        display=display
    )

    if data is None:

        return []

    results = normalize_precedent_list(
        data
    )

    if not results:

        return []

    # ========================================================
    # B. 상세조회 개수 제한
    #
    # 검색 목록 전체를 매번 상세조회하면 API 호출량이 커지므로
    # 상위 결과만 상세조회한다.
    # ========================================================

    try:

        detail_limit = int(
            detail_limit
        )

    except (
        TypeError,
        ValueError,
    ):

        detail_limit = 3

    detail_limit = max(
        0,
        min(
            detail_limit,
            len(
                results
            )
        )
    )

    # ========================================================
    # C. 상위 결과 상세 병합
    # ========================================================

    for index, item in enumerate(
        results
    ):

        item["detail_verified"] = False
        item["detail_status"] = "not_requested"
        pid = str(item.get("precedent_id", ""))
        item["official_link"] = "https://www.law.go.kr/LSW/precInfoP.do?precSeq=" + pid if pid.isdigit() else ""

        # 상세조회 대상이 아닌 검색 결과도
        # 동일한 key 구조를 유지한다.
        item.setdefault(
            "holding",
            ""
        )

        item.setdefault(
            "summary",
            ""
        )

        item.setdefault(
            "reasoning",
            ""
        )

        item.setdefault(
            "reference_articles",
            ""
        )

        item.setdefault(
            "reference_precedents",
            ""
        )

        item.setdefault(
            "full_text",
            ""
        )

        item.setdefault(
            "raw_detail",
            {}
        )

        if index >= detail_limit:

            continue

        item["detail_status"] = "error"

        precedent_id = normalize_text(
            item.get(
                "precedent_id"
            )
        )

        if not precedent_id:

            continue

        try:

            detail_data = (
                fetch_precedent_detail_data(
                    precedent_id
                )
            )

            detail = (
                normalize_precedent_detail(
                    detail_data
                )
            )

        except Exception:

            # 판례 상세조회 1건이 실패해도
            # 검색 결과 전체를 버리지 않는다.
            continue

        if not isinstance(
            detail,
            dict
        ):

            continue

        raw_detail = detail.get("raw_detail", {})
        detail_id = str(raw_detail.get("판례정보일련번호") or raw_detail.get("판례일련번호") or "")
        identity_ok = (detail_id == precedent_id and
                       normalize_text(raw_detail.get("사건번호")) == item.get("case_number") and
                       normalize_text(raw_detail.get("법원명")) == item.get("court_name") and
                       ''.join(c for c in str(raw_detail.get("선고일자", "")) if c.isdigit()) ==
                       ''.join(c for c in str(item.get("decision_date", "")) if c.isdigit()) and
                       bool(item.get("decision_date")))
        if not identity_ok or not detail.get("full_text"):
            item["detail_status"] = "unverified"
            continue
        item["detail_verified"] = True
        item["detail_status"] = "success"

        for key in (
            "holding",
            "summary",
            "reasoning",
            "reference_articles",
            "reference_precedents",
            "full_text",
            "raw_detail",
        ):

            value = detail.get(
                key
            )

            if value not in (
                None,
                "",
                {},
                [],
            ):

                item[
                    key
                ] = value

    return results


# ============================================================
# 6. 기존 공개 API 반환
# ============================================================

__all__ = [

    "normalize_text",

    "ensure_list",

    "is_precedent_item",

    "extract_precedent_list",

    "normalize_precedent_item",

    "normalize_precedent_list",

    "extract_precedent_detail",

    "normalize_precedent_detail",

    "fetch_precedent_search_data",

    "fetch_precedent_detail_data",

    "search_precedents",
]


# ============================================================
# 7. 단독 실행 테스트
# ============================================================

if __name__ == "__main__":

    test_query = (
        "음주운전"
    )

    print()

    print(
        "=" * 70
    )

    print(
        "판례 검색 + 상세조회 테스트"
    )

    print(
        "=" * 70
    )

    print(
        "검색어:",
        test_query
    )

    try:

        results = search_precedents(
            query=test_query,
            display=5,
            detail_limit=3
        )

        print()

        print(
            "검색 결과:",
            len(
                results
            ),
            "건"
        )

        for item in results:

            print()

            print(
                f"[{item['rank']}] "
                f"{item['case_name']}"
            )

            print(
                "사건번호:",
                item[
                    "case_number"
                ]
            )

            print(
                "법원:",
                item[
                    "court_name"
                ]
            )

            print(
                "선고일자:",
                item[
                    "decision_date"
                ]
            )

            print(
                "판례 ID:",
                item[
                    "precedent_id"
                ]
            )

            print(
                "판시사항 길이:",
                len(
                    item.get(
                        "holding",
                        ""
                    )
                )
            )

            print(
                "판결요지 길이:",
                len(
                    item.get(
                        "summary",
                        ""
                    )
                )
            )

            print(
                "판례내용 길이:",
                len(
                    item.get(
                        "full_text",
                        ""
                    )
                )
            )

    except Exception as e:

        print()

        print(
            "오류:",
            e
        )
