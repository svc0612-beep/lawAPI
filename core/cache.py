# ============================================================
# 공통 API 캐시 통합 모듈
#
# 기존 호환성 유지:
#
# from core.cache import (
#     get_cache,
#     save_cache,
#     record_api_call,
#     ...
# )
#
# 실제 구현은 역할별 모듈로 분리되어 있다.
# ============================================================


# ============================================================
# 공통 설정
# ============================================================

from core.cache_common import (
    CURRENT_DIR,
    PROJECT_ROOT,
    DATA_DIR,
    DB_PATH,
    now_utc,
)


# ============================================================
# DB
# ============================================================

from core.cache_db import (
    get_connection,
    initialize_database,
)


# ============================================================
# 캐시 키
# ============================================================

from core.cache_key import (
    make_safe_params,
    make_cache_key,
)


# ============================================================
# 캐시 저장소
# ============================================================

from core.cache_store import (
    delete_cache_by_key,
    get_cache,
    save_cache,
    clear_expired_cache,
    get_cache_count,
)


# ============================================================
# API 사용량
# ============================================================

from core.cache_usage import (
    record_api_call,
    get_today_usage,
)


# ============================================================
# 공개 API
# ============================================================

__all__ = [

    "CURRENT_DIR",

    "PROJECT_ROOT",

    "DATA_DIR",

    "DB_PATH",

    "now_utc",

    "get_connection",

    "initialize_database",

    "make_safe_params",

    "make_cache_key",

    "delete_cache_by_key",

    "get_cache",

    "save_cache",

    "clear_expired_cache",

    "record_api_call",

    "get_today_usage",

    "get_cache_count",
]


# ============================================================
# 단독 실행 테스트
# ============================================================

if __name__ == "__main__":

    initialize_database()

    deleted_count = clear_expired_cache()

    print()

    print(
        "=" * 70
    )

    print(
        "공통 API 캐시 상태"
    )

    print(
        "=" * 70
    )

    print(
        "DB 위치:",
        DB_PATH
    )

    print(
        "현재 캐시 개수:",
        get_cache_count()
    )

    print(
        "삭제된 만료 캐시:",
        deleted_count
    )

    print()

    print(
        "-" * 70
    )

    print(
        "오늘 실제 API 호출 기록"
    )

    print(
        "-" * 70
    )

    usage = get_today_usage()

    if not usage:

        print(
            "아직 기록된 API 호출이 없습니다."
        )

    else:

        for item in usage:

            print(
                f"{item['source']} / "
                f"{item['endpoint']} : "
                f"{item['call_count']}회"
            )