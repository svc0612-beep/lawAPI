# ============================================================
# 공통 API 캐시 DB 관리
#
# 역할
# - SQLite 연결
# - api_cache 테이블 초기화
# - api_usage 테이블 초기화
# ============================================================

import sqlite3

from core.cache_common import (
    DB_PATH,
)


# ============================================================
# 1. DB 연결
# ============================================================

def get_connection():

    connection = sqlite3.connect(
        DB_PATH
    )

    connection.row_factory = (
        sqlite3.Row
    )

    return connection


# ============================================================
# 2. DB 초기화
# ============================================================

def initialize_database():

    connection = get_connection()

    cursor = connection.cursor()

    # ========================================================
    # API 응답 캐시
    # ========================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS api_cache (

            cache_key TEXT PRIMARY KEY,

            source TEXT NOT NULL,

            endpoint TEXT NOT NULL,

            request_params TEXT NOT NULL,

            response_json TEXT NOT NULL,

            fetched_at TEXT NOT NULL,

            expires_at TEXT NOT NULL
        )
        """
    )

    # ========================================================
    # 실제 API 호출 횟수
    # ========================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS api_usage (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            source TEXT NOT NULL,

            endpoint TEXT NOT NULL,

            usage_date TEXT NOT NULL,

            call_count INTEGER NOT NULL DEFAULT 0,

            UNIQUE(
                source,
                endpoint,
                usage_date
            )
        )
        """
    )

    connection.commit()

    connection.close()