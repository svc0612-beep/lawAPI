# ============================================================
# 법령 부칙용 상세 API Fetcher
#
# 역할:
# - LAW_API_KEY 확인
# - lawService.do 전체 상세 JSON 요청
#
# API Key가 포함된 URL / 예외 문자열을 외부에 노출하지 않는다.
# ============================================================

import os

import requests

from typing import (
    Any,
    Dict,
)

from dotenv import load_dotenv


# ============================================================
# 프로젝트 루트
# ============================================================

CURRENT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        CURRENT_DIR
    )
)


# ============================================================
# 환경변수
# ============================================================

load_dotenv(
    os.path.join(
        PROJECT_ROOT,
        ".env"
    )
)

LAW_API_KEY = os.getenv(
    "LAW_API_KEY"
)

if not LAW_API_KEY:

    raise RuntimeError(
        "LAW_API_KEY를 찾을 수 없습니다."
    )


# ============================================================
# 법제처 상세 API
# ============================================================

LAW_SERVICE_URL = (
    "https://www.law.go.kr/"
    "DRF/lawService.do"
)


# ============================================================
# 법령 상세 JSON
# ============================================================

def fetch_law_detail(
    mst: str
) -> Dict[str, Any]:

    mst = str(
        mst
        or ""
    ).strip()

    if not mst:

        raise ValueError(
            "법령일련번호(MST)가 없습니다."
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

    try:

        response = requests.get(

            LAW_SERVICE_URL,

            params=params,

            timeout=30
        )

        response.raise_for_status()

        data = response.json()

    except requests.exceptions.Timeout:

        raise RuntimeError(
            "법령 상세정보 조회 요청 시간이 초과되었습니다."
        )

    except requests.exceptions.ConnectionError:

        raise RuntimeError(
            "법제처 API 서버에 연결할 수 없습니다."
        )

    except requests.RequestException:

        # 인증키가 포함된 요청 URL이
        # 예외 문자열을 통해 노출되지 않도록 한다.
        raise RuntimeError(
            "법령 상세정보 조회 중 오류가 발생했습니다."
        )

    except ValueError:

        raise RuntimeError(
            "법령 상세정보 응답을 JSON으로 해석할 수 없습니다."
        )

    if not isinstance(
        data,
        dict
    ):

        raise RuntimeError(
            "법령 상세정보 응답 형식이 올바르지 않습니다."
        )

    return data