# ============================================================
# 국회도서관 자료검색 API 403 원인 확인용
#
# 중요:
# - API 키를 화면에 출력하지 않는다.
# - 요청 URL도 출력하지 않는다.
# - 서버 응답 본문만 확인한다.
# ============================================================

import os
import sys
import requests


# ============================================================
# 프로젝트 루트 등록
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
# 설정
# ============================================================

from core.config import (
    NANET_API_KEY,
    validate_nanet_api_key,
)


SEARCH_URL = (
    "https://apis.data.go.kr/9720000/searchservice/basic"
)


# ============================================================
# 실행
# ============================================================

if __name__ == "__main__":

    validate_nanet_api_key()


    params = {

        "ServiceKey":
            NANET_API_KEY,

        "pageno":
            1,

        "displaylines":
            10,

        "search":
            "자료명,특허",
    }


    print()
    print("=" * 70)
    print("국회도서관 자료검색 API 상태 확인")
    print("=" * 70)


    try:

        response = requests.get(
            SEARCH_URL,
            params=params,
            timeout=20
        )


        # ----------------------------------------------------
        # URL / API KEY는 출력하지 않는다.
        # ----------------------------------------------------

        print(
            "HTTP 상태 코드:",
            response.status_code
        )


        print(
            "Content-Type:",
            response.headers.get(
                "Content-Type",
                ""
            )
        )


        print()

        print(
            "서버 응답:"
        )

        print(
            response.text[:2000]
        )


    except requests.exceptions.Timeout:

        print(
            "요청 시간 초과"
        )


    except requests.exceptions.ConnectionError:

        print(
            "서버 연결 실패"
        )


    except requests.exceptions.RequestException as e:

        # requests 예외 문자열에는
        # API 키가 포함된 URL이 들어갈 수 있으므로
        # e 자체를 출력하지 않는다.

        print(
            "HTTP 요청 자체에서 오류가 발생했습니다."
        )