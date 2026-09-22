# ============================================================
# 공통 API 캐시 키 생성
#
# 역할
# - 인증정보 제거
# - 요청 파라미터 정규화
# - SHA-256 캐시 키 생성
#
# 중요:
# API Key는 캐시 DB와 캐시 키 payload에 저장하지 않는다.
# ============================================================

import json
import hashlib


# ============================================================
# 1. API Key 제거
# ============================================================

def make_safe_params(
    params: dict
):

    safe_params = {}

    for key, value in params.items():

        if key.lower() in {
            "oc",
            "servicekey",
            "apikey",
            "api_key",
        }:

            continue

        safe_params[
            key
        ] = value

    return safe_params


# ============================================================
# 2. 캐시 키 생성
# ============================================================

def make_cache_key(
    source: str,
    endpoint: str,
    params: dict
):

    safe_params = make_safe_params(
        params
    )

    payload = {

        "source":
            source,

        "endpoint":
            endpoint,

        "params":
            safe_params,
    }

    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        default=str
    )

    return hashlib.sha256(
        serialized.encode(
            "utf-8"
        )
    ).hexdigest()