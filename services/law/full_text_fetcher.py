# ============================================================
# 법령 전체 원문 API 호출
# ============================================================

from typing import (
    Any,
    Dict,
)

import requests

from core.config import (
    LAW_API_KEY,
    LAW_SERVICE_URL,
)
from core.cache import get_cache, save_cache, record_api_call

from services.law.full_text_utils import (
    normalize_text,
)


REQUEST_TIMEOUT = 30


def request_full_law_json(
    mst: str,
    effective_date: str = ""
) -> Dict[str, Any]:

    mst = normalize_text(
        mst
    )

    if not mst:

        raise ValueError(
            "법령일련번호(MST)가 없습니다."
        )

    if not LAW_API_KEY:

        raise RuntimeError(
            "법제처 API 인증키가 설정되어 있지 않습니다."
        )

    params = {

        "OC":
            LAW_API_KEY,

        "target":
            "law",

        "MST":
            mst,

        "type":
            "JSON",
    }

    effective_date = normalize_text(effective_date)
    if effective_date:
        if len(effective_date) != 8 or not effective_date.isdigit():
            raise ValueError("시행일자 형식이 올바르지 않습니다.")
        params["efYd"] = effective_date
        # The ordinary `law` target may return a scheduled promulgated
        # version even when efYd is supplied. The official effective-date
        # contract is the separate `eflaw` target.
        params["target"] = "eflaw"

    endpoint = "lawService-full-law-v4"
    cached = get_cache(source="법제처", endpoint=endpoint, params=params)
    if cached is not None:
        return cached

    try:

        response = requests.get(
            LAW_SERVICE_URL,
            params=params,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

    except requests.RequestException:

        # 인증키가 포함된 요청 URL이나
        # requests 예외 문자열을 노출하지 않는다.
        raise RuntimeError(
            "법령 전체 원문 API 호출에 실패했습니다."
        )

    try:

        data = response.json()

    except ValueError:

        raise RuntimeError(
            "법령 전체 원문 응답을 JSON으로 해석할 수 없습니다."
        )

    if not isinstance(
        data,
        dict
    ):

        raise RuntimeError(
            "법령 전체 원문 응답 형식이 올바르지 않습니다."
        )

    root = data.get("법령")
    if not isinstance(root, dict) or not isinstance(root.get("조문"), dict):
        raise RuntimeError("법령 전체 원문에 조문 데이터가 없습니다.")
    record_api_call(source="법제처", endpoint=endpoint)
    save_cache(source="법제처", endpoint=endpoint, params=params,
               response_data=data, ttl_hours=24)
    return data
