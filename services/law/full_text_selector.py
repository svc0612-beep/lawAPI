# ============================================================
# 전체 법령 조회용 법령 선택기
#
# 역할
# - 법령명으로 법제처 lawSearch를 호출해서 후보 목록을 받고
# - 정확 일치하는 법령 하나를 골라서 반환
#
# 변경 이력
# - 2026-09-21: 짧은 법령명(상법·상표법 등) 정확 매칭 실패 해결
#   법제처 API는 부분매칭으로 결과를 뿌리기 때문에,
#   '상법' 같은 짧은 이름은 상위 20건 안에 정작 본인이 안 들어올 수 있다.
#   → 1차 display=20 검색으로 정확 매칭 실패 시,
#      2차 display=100 검색으로 재시도해서 매칭 확률을 높인다.
#      (정상 케이스는 1차에서 히트 → 성능 손실 없음)
# ============================================================

from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from services.law.search import (
    search_law,
)

from services.law.full_text_utils import (
    normalize_text,
    compact_text,
)


# ============================================================
# 후보 목록에서 정확 일치하는 법령 하나 선택
#
# 매칭 순서
# 1) 공백/특수문자 제거 후 정확 일치 (가장 넓게)
# 2) 일반 문자열 정확 일치
# 없으면 None
# ============================================================

def select_best_law(
    law_name: str,
    results: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:

    # 후보 없으면 즉시 종료
    if not results:
        return None

    # 공백/특수문자 제거한 타깃 문자열
    target = compact_text(
        law_name
    )

    if not target:
        return None

    # ---- 1차: 공백/특수문자 제거 후 정확 일치 ----
    for item in results:

        candidate_name = item.get(
            "법령명한글",
            ""
        )

        if compact_text(
            candidate_name
        ) == target:

            return item

    # ---- 2차: 일반 문자열 정확 일치 ----
    normalized_target = normalize_text(
        law_name
    )

    for item in results:

        candidate_name = normalize_text(
            item.get(
                "법령명한글",
                ""
            )
        )

        if candidate_name == normalized_target:

            return item

    # 정확 일치 없음
    return None


# ============================================================
# 법령명 → 전체조회용 법령 dict 하나
#
# 흐름
# 1) 1차 검색 (display=20) — 대부분의 경우 여기서 해결
# 2) 여기서 정확 매칭 실패한 경우에만 2차 검색 (display=100)
#    → 짧은 이름(상법, 상표법 등)이 부분매칭 결과 뒤에 밀린 케이스 구제
# 3) 그래도 매칭 못 하면 None
# ============================================================

def find_law_for_full_text(
    law_name: str
) -> Optional[Dict[str, Any]]:

    # 앞뒤 공백 정리
    law_name = normalize_text(
        law_name
    )

    if not law_name:
        return None

    # ---- 1차: 기본 검색량 ----
    results = search_law(
        query=law_name,
        display=20
    )

    selected = select_best_law(
        law_name=law_name,
        results=results
    )

    # 1차에서 성공하면 즉시 반환 (캐시 재사용, 성능 영향 X)
    if selected is not None:
        return selected

    # ---- 2차: 넓은 검색 (짧은 법령명 구제) ----
    # 부분매칭으로 결과가 많이 뿌려지는 짧은 이름을 위해
    # display를 크게 늘려서 정확 일치 후보를 놓치지 않게 한다.
    wide_results = search_law(
        query=law_name,
        display=100
    )

    # 1차 결과와 결합 (혹시 캐시된 20건이 별개로 존재할 경우 대비)
    combined = list(wide_results)

    # 이미 본 candidate 는 넘어가도록 dedup key로 법령일련번호 사용
    seen_mst = set()
    deduped = []
    for item in combined:
        mst = item.get("법령일련번호")
        if mst and mst in seen_mst:
            continue
        if mst:
            seen_mst.add(mst)
        deduped.append(item)

    # 2차 매칭 시도
    return select_best_law(
        law_name=law_name,
        results=deduped
    )
