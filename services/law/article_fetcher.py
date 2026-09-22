# ============================================================
# 법령 특정 조문 API 조회
#
# 역할
#
# - MST + JO 요청
# - 캐시 조회
# - 법제처 API 호출
# - API 사용량 기록
# - 캐시 저장
# ============================================================

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

from services.law.article_utils import (
    make_jo_code,
)


def get_law_article(
    mst,
    article_number: int,
    sub_article_number: int = 0
):

    """
    MST를 이용해 특정 법령 조문을 조회한다.
    """

    validate_law_api_key()

    if not mst:

        raise ValueError(
            "MST 값이 없습니다."
        )

    jo_code = make_jo_code(

        article_number=article_number,

        sub_article_number=(
            sub_article_number
        )
    )

    params = {

        "OC":
            LAW_API_KEY,

        "target":
            "law",

        "type":
            "JSON",

        "MST":
            str(mst),

        "JO":
            jo_code,
    }

    endpoint = (
        "lawService-article"
    )

    # ========================================================
    # 1. 캐시
    # ========================================================

    cached = get_cache(

        source=SOURCE_MOLEG,

        endpoint=endpoint,

        params=params
    )

    if cached is not None:

        print(
            f"[CACHE HIT] 조문조회: "
            f"MST={mst}, JO={jo_code}"
        )

        return cached

    # ========================================================
    # 2. 실제 API 호출
    # ========================================================

    print(
        f"[API CALL] 조문조회: "
        f"MST={mst}, JO={jo_code}"
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
            "법제처 조문 조회 요청 시간이 초과되었습니다."
        )

    except requests.exceptions.ConnectionError:

        raise RuntimeError(
            "법제처 API 서버에 연결할 수 없습니다."
        )

    except requests.exceptions.RequestException:

        # 요청 URL 안의 인증키가
        # 오류 메시지에 노출되지 않도록
        # 원본 requests 예외 문자열은 출력하지 않는다.
        raise RuntimeError(
            "법제처 조문 조회 요청 중 오류가 발생했습니다."
        )

    except ValueError:

        raise RuntimeError(
            "법제처 조문 응답을 JSON으로 해석할 수 없습니다."
        )

    # ========================================================
    # 3. 실제 호출 기록
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
            "law_article"
        ]
    )

    return data