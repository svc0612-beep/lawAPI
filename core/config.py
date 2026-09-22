# ============================================================
# 프로젝트 공통 설정
#
# 역할
# 1. 환경변수 로드
# 2. API Key 관리
# 3. API 주소 관리
# 4. 캐시 TTL 관리
#
# 다른 파일에서는 이 파일의 값을 import해서 사용한다.
# ============================================================

import os

from dotenv import load_dotenv


# ============================================================
# 1. .env 로드
# ============================================================

load_dotenv()


# ============================================================
# 2. API KEY
# ============================================================

LAW_API_KEY = os.getenv(
    "LAW_API_KEY"
)

NANET_API_KEY = os.getenv(
    "NANET_API_KEY"
)


# ============================================================
# 3. 법제처 API 주소
# ============================================================

LAW_SEARCH_URL = (
    "https://www.law.go.kr/DRF/lawSearch.do"
)

LAW_SERVICE_URL = (
    "https://www.law.go.kr/DRF/lawService.do"
)


# ============================================================
# 4. 국회도서관 API 주소
# ============================================================

NANET_DETAIL_BASE_URL = (
    "https://apis.data.go.kr/9720000/detailinfoservice"
)


# ============================================================
# 5. API Source 이름
# ============================================================

SOURCE_MOLEG = "법제처"

SOURCE_NANET = "국회도서관"


# ============================================================
# 6. 캐시 TTL
#
# 단위: 시간
# ============================================================

CACHE_TTL = {

    # 일반 법령 검색
    "law_search":
        12,

    # 특정 조문
    "law_article":
        24,

    # aiSearch
    "law_ai_search":
        6,

    # 공식 법령 체계도
    "law_system_map":
        24,

    # 판례 검색
    "precedent":
        12,

    # 법령해석례
    "interpretation":
        12,

    # 국회도서관 상세정보
    "nanet_detail":
        24,

    # 국회도서관 목차
    "nanet_toc":
        24,
}


# ============================================================
# 7. 환경변수 검증
# ============================================================

def validate_law_api_key():

    if not LAW_API_KEY:

        raise ValueError(
            ".env 파일에서 LAW_API_KEY를 찾을 수 없습니다."
        )


def validate_nanet_api_key():

    if not NANET_API_KEY:

        raise ValueError(
            ".env 파일에서 NANET_API_KEY를 찾을 수 없습니다."
        )


# ============================================================
# 8. 단독 실행 테스트
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 70)
    print("공통 설정 확인")
    print("=" * 70)

    print(
        "LAW_API_KEY 존재:",
        bool(
            LAW_API_KEY
        )
    )

    print(
        "NANET_API_KEY 존재:",
        bool(
            NANET_API_KEY
        )
    )

    print(
        "법제처 검색 URL:",
        LAW_SEARCH_URL
    )

    print(
        "법제처 상세 URL:",
        LAW_SERVICE_URL
    )

    print(
        "국회도서관 URL:",
        NANET_DETAIL_BASE_URL
    )
