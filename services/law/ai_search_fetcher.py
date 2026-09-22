# ============================================================
# aiSearch API Fetcher
#
# 역할
#
# - 캐시 조회
# - 법제처 aiSearch 호출
# - API 호출 기록
# - 캐시 저장
# ============================================================

import requests

from core.config import (
    LAW_API_KEY,
    LAW_SEARCH_URL,
    SOURCE_MOLEG,
    CACHE_TTL,
    validate_law_api_key,
)

from core.cache import (
    get_cache,
    save_cache,
    record_api_call,
)


def request_ai_search(
    query: str,
    display: int = 10
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
            "aiSearch",

        "type":
            "JSON",

        "query":
            query,

        "display":
            display,
    }

    endpoint = (
        "lawSearch-aiSearch"
    )

    # ========================================================
    # 1. 캐시 조회
    # ========================================================

    cached = get_cache(

        source=SOURCE_MOLEG,

        endpoint=endpoint,

        params=params
    )

    if cached is not None:

        print(
            f"[CACHE HIT] aiSearch: {query}"
        )

        return cached

    # ========================================================
    # 2. 실제 API 호출
    # ========================================================

    print(
        f"[API CALL] aiSearch: {query}"
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
            "법제처 aiSearch 요청 시간이 초과되었습니다."
        )

    except requests.exceptions.ConnectionError:

        raise RuntimeError(
            "법제처 API 서버에 연결할 수 없습니다."
        )

    except requests.exceptions.RequestException:

        # 요청 URL에 인증키가 포함될 수 있으므로
        # requests 원본 예외 문자열은 노출하지 않는다.
        raise RuntimeError(
            "법제처 aiSearch 요청 중 오류가 발생했습니다."
        )

    except ValueError:

        raise RuntimeError(
            "법제처 aiSearch 응답을 JSON으로 해석할 수 없습니다."
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
            "law_ai_search"
        ]
    )

    return data