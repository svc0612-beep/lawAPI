# ============================================================
# 공식 법령 체계도 API Fetcher
#
# 역할
# - 캐시 조회
# - 법제처 lsStmd 호출
# - API 사용량 기록
# - 캐시 저장
# ============================================================

from typing import (
    Any,
    Dict,
)

import requests

from core.config import (
    LAW_API_KEY,
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


REQUEST_TIMEOUT = 30


def request_law_system_map(
    mst: str,
) -> Dict[str, Any]:

    validate_law_api_key()

    mst = (
        str(mst)
        if mst is not None
        else ""
    ).strip()

    if not mst:
        raise ValueError(
            "법령일련번호(MST)가 없습니다."
        )

    params = {
        "OC": LAW_API_KEY,
        "target": "lsStmd",
        "type": "JSON",
        "MST": mst,
    }

    endpoint = "lawService-lsStmd"

    cached = get_cache(
        source=SOURCE_MOLEG,
        endpoint=endpoint,
        params=params,
    )

    if cached is not None:

        print(
            f"[CACHE HIT] 법령체계도: MST={mst}"
        )

        return cached

    print(
        f"[API CALL] 법령체계도: MST={mst}"
    )

    try:

        response = requests.get(
            LAW_SERVICE_URL,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

    except requests.exceptions.Timeout:

        raise RuntimeError(
            "법제처 법령 체계도 요청 시간이 초과되었습니다."
        ) from None

    except requests.exceptions.ConnectionError:

        raise RuntimeError(
            "법제처 API 서버에 연결할 수 없습니다."
        ) from None

    except requests.exceptions.RequestException:

        # 요청 URL에는 인증값이 포함될 수 있으므로
        # 원본 requests 예외 문자열을 노출하지 않는다.
        raise RuntimeError(
            "법제처 법령 체계도 요청 중 오류가 발생했습니다."
        ) from None

    except ValueError:

        raise RuntimeError(
            "법제처 법령 체계도 응답을 JSON으로 해석할 수 없습니다."
        ) from None

    if not isinstance(data, dict):
        raise RuntimeError(
            "법제처 법령 체계도 응답 형식이 올바르지 않습니다."
        )

    record_api_call(
        source=SOURCE_MOLEG,
        endpoint=endpoint,
    )

    save_cache(
        source=SOURCE_MOLEG,
        endpoint=endpoint,
        params=params,
        response_data=data,
        ttl_hours=CACHE_TTL[
            "law_system_map"
        ],
    )

    return data
