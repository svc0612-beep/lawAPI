# ============================================================
# 외부 API 사용량 기록
#
# 역할
# - 실제 API 호출 횟수 기록
# - 오늘 API 사용량 조회
#
# 캐시 HIT는 여기에서 기록하지 않는다.
# ============================================================

from core.cache_common import (
    now_utc,
)

from core.cache_db import (
    get_connection,
    initialize_database,
)


# ============================================================
# 1. 실제 API 호출 기록
# ============================================================

def record_api_call(
    source: str,
    endpoint: str
):

    initialize_database()

    today = (
        now_utc()
        .date()
        .isoformat()
    )

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO api_usage (

            source,

            endpoint,

            usage_date,

            call_count

        )

        VALUES (?, ?, ?, 1)

        ON CONFLICT(
            source,
            endpoint,
            usage_date
        )

        DO UPDATE SET

            call_count =
                call_count + 1
        """,
        (
            source,
            endpoint,
            today,
        )
    )

    connection.commit()

    connection.close()


# ============================================================
# 2. 오늘 API 사용량 조회
# ============================================================

def get_today_usage():

    initialize_database()

    today = (
        now_utc()
        .date()
        .isoformat()
    )

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT

            source,

            endpoint,

            call_count

        FROM api_usage

        WHERE usage_date = ?

        ORDER BY
            source,
            endpoint
        """,
        (
            today,
        )
    )

    rows = cursor.fetchall()

    connection.close()

    results = []

    for row in rows:

        results.append(
            {
                "source":
                    row[
                        "source"
                    ],

                "endpoint":
                    row[
                        "endpoint"
                    ],

                "call_count":
                    row[
                        "call_count"
                    ],
            }
        )

    return results