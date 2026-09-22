# ============================================================
# 법제처 법령해석례 Fetcher
#
# 역할
# - target=expc 검색 API 호출
# - target=expc 상세 API 호출
# - SQLite 캐시 확인 / 저장
# - API 사용량 기록
#
# 중요:
# - API Key를 오류 메시지에 노출하지 않는다.
# ============================================================

import requests

from core.config import (
    LAW_API_KEY,
    LAW_SEARCH_URL,
    LAW_SERVICE_URL,
    SOURCE_MOLEG,
    CACHE_TTL,
    validate_law_api_key,
)

from core.cache import (
    get_cache,
    save_cache,
    record_api_call,
)


# ============================================================
# 법령해석례 검색 원본 데이터 조회
# ============================================================

def fetch_interpretation_search_data(
    query: str,
    display: int = 5
):

    validate_law_api_key()

    query = (
        query
        or ""
    ).strip()

    if not query:

        return None

    params = {

        "OC":
            LAW_API_KEY,

        "target":
            "expc",

        "type":
            "JSON",

        "query":
            query,

        "display":
            display,
    }

    endpoint = (
        "lawSearch-expc"
    )

    # ========================================================
    # 1. 캐시 확인
    # ========================================================

    cached = get_cache(
        source=SOURCE_MOLEG,
        endpoint=endpoint,
        params=params
    )

    if cached is not None:

        print(
            f"[CACHE HIT] expc: {query}"
        )

        return cached

    # ========================================================
    # 2. 실제 API 호출
    # ========================================================

    print(
        f"[API CALL] expc: {query}"
    )

    try:

        response = requests.get(
            LAW_SEARCH_URL,
            params=params,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

    except requests.exceptions.Timeout:

        raise RuntimeError(
            "법제처 법령해석례 검색 요청 시간이 초과되었습니다."
        )

    except requests.exceptions.ConnectionError:

        raise RuntimeError(
            "법제처 API 서버에 연결할 수 없습니다."
        )

    except requests.exceptions.RequestException:

        raise RuntimeError(
            "법제처 법령해석례 검색 요청 중 오류가 발생했습니다."
        )

    except ValueError:

        raise RuntimeError(
            "법제처 법령해석례 검색 응답을 JSON으로 해석할 수 없습니다."
        )

    # ========================================================
    # 3. API 호출 기록
    # ========================================================

    record_api_call(
        source=SOURCE_MOLEG,
        endpoint=endpoint
    )

    # ========================================================
    # 4. 캐시 저장
    # ========================================================

    save_cache(
        source=SOURCE_MOLEG,
        endpoint=endpoint,
        params=params,
        response_data=data,
        ttl_hours=CACHE_TTL[
            "interpretation"
        ]
    )

    return data


# ============================================================
# 법령해석례 상세 원본 데이터 조회
#
# interpretation_id:
# - 법령해석례 검색 결과의 법령해석례일련번호
# - 예: 314839
# ============================================================

def fetch_interpretation_detail_data(
    interpretation_id: str
):

    validate_law_api_key()

    interpretation_id = str(
        interpretation_id
        or ""
    ).strip()

    if not interpretation_id:

        return None

    params = {

        "OC":
            LAW_API_KEY,

        "target":
            "expc",

        "type":
            "JSON",

        "ID":
            interpretation_id,
    }

    endpoint = (
        "lawService-expc"
    )

    # ========================================================
    # 1. 캐시 확인
    # ========================================================

    cached = get_cache(
        source=SOURCE_MOLEG,
        endpoint=endpoint,
        params=params
    )

    if cached is not None:

        print(
            f"[CACHE HIT] expc detail: {interpretation_id}"
        )

        return cached

    # ========================================================
    # 2. 실제 API 호출
    # ========================================================

    print(
        f"[API CALL] expc detail: {interpretation_id}"
    )

    try:

        response = requests.get(
            LAW_SERVICE_URL,
            params=params,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

    except requests.exceptions.Timeout:

        raise RuntimeError(
            "법제처 법령해석례 상세조회 요청 시간이 초과되었습니다."
        )

    except requests.exceptions.ConnectionError:

        raise RuntimeError(
            "법제처 API 서버에 연결할 수 없습니다."
        )

    except requests.exceptions.RequestException:

        raise RuntimeError(
            "법제처 법령해석례 상세조회 요청 중 오류가 발생했습니다."
        )

    except ValueError:

        raise RuntimeError(
            "법제처 법령해석례 상세조회 응답을 JSON으로 해석할 수 없습니다."
        )

    # ========================================================
    # 3. API 호출 기록
    # ========================================================

    record_api_call(
        source=SOURCE_MOLEG,
        endpoint=endpoint
    )

    # ========================================================
    # 4. 캐시 저장
    # ========================================================

    save_cache(
        source=SOURCE_MOLEG,
        endpoint=endpoint,
        params=params,
        response_data=data,
        ttl_hours=CACHE_TTL[
            "interpretation"
        ]
    )

    return data
