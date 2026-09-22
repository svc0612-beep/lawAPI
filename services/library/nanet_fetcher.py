# ============================================================
# 국회도서관 API Fetcher
#
# 역할
# - /detail
# - /toc
# - 캐시
# - API 사용량 기록
#
# 중요:
# - serviceKey를 오류 메시지에 노출하지 않는다.
# ============================================================

import requests

from core.config import (
    NANET_API_KEY,
    NANET_DETAIL_BASE_URL,
    SOURCE_NANET,
    validate_nanet_api_key,
)

from core.cache import (
    get_cache,
    save_cache,
    record_api_call,
)

from services.library.nanet_utils import (
    normalize_text,
)

from services.library.nanet_xml import (
    parse_xml_response,
    validate_response_status,
)


# ============================================================
# 공통 API 호출
# ============================================================

def request_nanet(
    path: str,
    control_no: str,
    endpoint: str,
    ttl_hours: int
):

    validate_nanet_api_key()

    control_no = normalize_text(
        control_no
    )

    if not control_no:

        raise ValueError(
            "controlno가 비어 있습니다."
        )

    url = (
        f"{NANET_DETAIL_BASE_URL}/{path}"
    )

    params = {

        "serviceKey":
            NANET_API_KEY,

        "controlno":
            control_no,
    }

    # ========================================================
    # 1. 캐시 확인
    # ========================================================

    cached = get_cache(
        source=SOURCE_NANET,
        endpoint=endpoint,
        params=params
    )

    if cached is not None:

        print(
            f"[CACHE HIT] 국회도서관 "
            f"{path}: {control_no}"
        )

        validate_response_status(
            cached
        )

        return cached

    # ========================================================
    # 2. 실제 API 호출
    # ========================================================

    print(
        f"[API CALL] 국회도서관 "
        f"{path}: {control_no}"
    )

    try:

        response = requests.get(
            url,
            params=params,
            timeout=20
        )

        response.raise_for_status()

    except requests.exceptions.Timeout:

        raise RuntimeError(
            "국회도서관 API 요청 시간이 초과되었습니다."
        )

    except requests.exceptions.ConnectionError:

        raise RuntimeError(
            "국회도서관 API 서버에 연결할 수 없습니다."
        )

    except requests.exceptions.RequestException:

        raise RuntimeError(
            "국회도서관 API 요청 중 오류가 발생했습니다."
        )

    # ========================================================
    # 3. XML 파싱
    # ========================================================

    data = parse_xml_response(
        response.text
    )

    validate_response_status(
        data
    )

    # ========================================================
    # 4. API 사용량 기록
    # ========================================================

    record_api_call(
        source=SOURCE_NANET,
        endpoint=endpoint
    )

    # ========================================================
    # 5. 캐시 저장
    # ========================================================

    save_cache(
        source=SOURCE_NANET,
        endpoint=endpoint,
        params=params,
        response_data=data,
        ttl_hours=ttl_hours
    )

    return data