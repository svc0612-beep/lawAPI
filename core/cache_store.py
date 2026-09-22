# ============================================================
# 공통 API 응답 캐시 저장소
#
# 역할
# - 캐시 조회
# - 캐시 저장
# - 특정 캐시 삭제
# - 만료 캐시 삭제
# - 현재 캐시 개수 조회
# ============================================================

import json

from datetime import (
    datetime,
    timedelta,
)

from core.cache_common import (
    now_utc,
)

from core.cache_db import (
    get_connection,
    initialize_database,
)

from core.cache_key import (
    make_safe_params,
    make_cache_key,
)


# ============================================================
# 1. 캐시 삭제
# ============================================================

def delete_cache_by_key(
    cache_key: str
):

    initialize_database()

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM api_cache
        WHERE cache_key = ?
        """,
        (
            cache_key,
        )
    )

    connection.commit()

    connection.close()


# ============================================================
# 2. 캐시 조회
# ============================================================

def get_cache(
    source: str,
    endpoint: str,
    params: dict
):

    initialize_database()

    cache_key = make_cache_key(
        source=source,
        endpoint=endpoint,
        params=params
    )

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT

            response_json,

            expires_at

        FROM api_cache

        WHERE cache_key = ?
        """,
        (
            cache_key,
        )
    )

    row = cursor.fetchone()

    connection.close()

    # ========================================================
    # 캐시 없음
    # ========================================================

    if row is None:

        return None

    # ========================================================
    # 만료시간 복원
    # ========================================================

    try:

        expires_at = datetime.fromisoformat(
            row[
                "expires_at"
            ]
        )

    except (
        ValueError,
        TypeError
    ):

        delete_cache_by_key(
            cache_key
        )

        return None

    # ========================================================
    # 캐시 만료
    # ========================================================

    if now_utc() >= expires_at:

        delete_cache_by_key(
            cache_key
        )

        return None

    # ========================================================
    # JSON 복원
    # ========================================================

    try:

        return json.loads(
            row[
                "response_json"
            ]
        )

    except json.JSONDecodeError:

        delete_cache_by_key(
            cache_key
        )

        return None


# ============================================================
# 3. 캐시 저장
# ============================================================

def save_cache(
    source: str,
    endpoint: str,
    params: dict,
    response_data,
    ttl_hours: int
):

    initialize_database()

    cache_key = make_cache_key(
        source=source,
        endpoint=endpoint,
        params=params
    )

    safe_params = make_safe_params(
        params
    )

    fetched_at = now_utc()

    expires_at = (
        fetched_at
        + timedelta(
            hours=ttl_hours
        )
    )

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO api_cache (

            cache_key,

            source,

            endpoint,

            request_params,

            response_json,

            fetched_at,

            expires_at

        )

        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            cache_key,

            source,

            endpoint,

            json.dumps(
                safe_params,
                ensure_ascii=False,
                sort_keys=True,
                default=str
            ),

            json.dumps(
                response_data,
                ensure_ascii=False,
                default=str
            ),

            fetched_at.isoformat(),

            expires_at.isoformat(),
        )
    )

    connection.commit()

    connection.close()


# ============================================================
# 4. 만료된 캐시 삭제
# ============================================================

def clear_expired_cache():

    initialize_database()

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM api_cache
        WHERE expires_at <= ?
        """,
        (
            now_utc().isoformat(),
        )
    )

    deleted_count = (
        cursor.rowcount
    )

    connection.commit()

    connection.close()

    return deleted_count


# ============================================================
# 5. 현재 캐시 개수
# ============================================================

def get_cache_count():

    initialize_database()

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT COUNT(*) AS count
        FROM api_cache
        """
    )

    row = cursor.fetchone()

    connection.close()

    return row[
        "count"
    ]